"""The language model only proposes. It sees no data, and a wrong suggestion cannot become a match."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from app.core.config import Settings
from app.intelligence.kpi.ir import Compare, DatePart, Difference, Filter, Measure, Op, Ratio
from app.reverse.engine import ReverseEngine
from app.reverse.models import NOT_REPRODUCIBLE, REPRODUCED, ParsedReport
from app.reverse.proposer import SYSTEM_PROMPT, AnthropicProposer, build_prompt, column_roles, default_proposer, parse_candidates

from tests.reverse.conftest import target

COLUMNS = ["Region", "Sales", "Cost", "Order Date"]


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Region": ["North", "North", "South"],
            "Sales": [100.5, 200.25, 4242.5],
            "Cost": [10.0, 20.0, 30.0],
            "Order Date": pd.to_datetime(["2024-01-05", "2024-02-09", "2025-03-01"]),
        }
    )


# --- what the model is told ---------------------------------------------------------------


def test_the_prompt_has_column_names_and_labels_but_never_a_data_value(frame) -> None:
    cell = target(4242.5, ["West"], ["2024"], unit="currency", ctx=["Sales by Region"], axis=["Region"])
    prompt = build_prompt("Orders", frame, cell)
    payload = json.loads(prompt)
    assert payload["columns"] == [
        {"name": "Region", "type": "text"},
        {"name": "Sales", "type": "number"},
        {"name": "Cost", "type": "number"},
        {"name": "Order Date", "type": "date"},
    ]
    assert payload["row_labels"] == ["West"] and payload["column_labels"] == ["2024"] and payload["unit"] == "currency"
    for secret in ("North", "South", "4242.5", "4242", "100.5", "200.25", "2025-03-01"):
        assert secret not in prompt and secret not in SYSTEM_PROMPT
    assert "NOT given the data" in SYSTEM_PROMPT


def test_even_the_number_being_explained_is_not_sent(frame) -> None:
    cell = target(31337.77, ["West"], ["2024"], shown="31,337.77")
    assert "31337" not in build_prompt("Orders", frame, cell) and "31,337" not in build_prompt("Orders", frame, cell)


def test_column_roles_are_coarse(frame) -> None:
    assert [r["type"] for r in column_roles(frame.assign(Flag=[True, False, True]))] == ["text", "number", "number", "date", "flag"]


# --- what comes back ----------------------------------------------------------------------


def test_a_well_formed_reply_becomes_ir() -> None:
    reply = json.dumps(
        [
            {"op": "sum", "column": "Sales", "filters": [{"column": "Region", "compare": "==", "value": "West"}]},
            {"op": "count", "column": None},
            {"op": "sum", "column": "Sales", "filters": [{"column": "Order Date", "compare": "==", "value": 2024, "part": "year"}]},
            {"ratio": {"numerator": {"op": "sum", "column": "Sales"}, "denominator": {"op": "sum", "column": "Cost"}, "scale": 100}},
            {"difference": {"minuend": {"op": "sum", "column": "Sales"}, "subtrahend": {"op": "sum", "column": "Cost"}}},
        ]
    )
    parsed = parse_candidates(f"Here you go:\n{reply}", COLUMNS)
    assert parsed[0] == Measure(Op.SUM, "Sales", (Filter("Region", Compare.EQ, "West"),))
    assert parsed[1] == Measure(Op.COUNT)
    assert parsed[2].filters == (Filter("Order Date", Compare.EQ, 2024, DatePart.YEAR),)
    assert parsed[3] == Ratio(Measure(Op.SUM, "Sales"), Measure(Op.SUM, "Cost"), 100.0)
    assert isinstance(parsed[4], Difference)


@pytest.mark.parametrize(
    "reply",
    [
        "no json here",
        "[not json]",
        '{"op": "sum", "column": "Sales"}',  # an object, not a list
        '[{"op": "sum", "column": "Profit"}]',  # invented column
        '[{"op": "median", "column": "Sales"}]',  # unknown op
        '[{"op": "ratio", "column": "Sales"}]',  # ratio is not a measure op
        '[{"op": "sum", "column": "Sales", "filters": [{"column": "Nope", "compare": "==", "value": 1}]}]',
        '[{"op": "sum", "column": "Sales", "filters": [{"column": "Region", "compare": "~~", "value": 1}]}]',
        '[{"op": "sum", "column": "Sales", "filters": [{"column": "Order Date", "compare": "==", "value": "2024", "part": "year"}]}]',
        '[{"op": "sum", "column": "Sales", "filters": [{"column": "Region", "compare": "in", "value": "West"}]}]',
        '[{"ratio": {"numerator": {"op": "sum", "column": "Sales"}, "denominator": {"op": "sum", "column": "Ghost"}}}]',
        '[{"ratio": {"numerator": {"op": "sum", "column": "Sales"}, "denominator": {"op": "sum", "column": "Cost"}, "scale": 7}}]',
        '[{"op": "sum"}]',  # sum needs a column
        '["sum of sales"]',
        "[1, 2, 3]",
    ],
)
def test_anything_unknown_or_malformed_is_dropped(reply) -> None:
    assert parse_candidates(reply, COLUMNS) == []


def test_good_and_bad_candidates_are_sorted_out_individually_and_capped() -> None:
    good = {"op": "sum", "column": "Sales"}
    reply = json.dumps([{"op": "sum", "column": "Ghost"}, good] + [good] * 20)
    parsed = parse_candidates(reply, COLUMNS)
    assert 1 <= len(parsed) <= 10 and all(p.column == "Sales" for p in parsed)


# --- the client ---------------------------------------------------------------------------


class FakeClient:
    def __init__(self, reply: str) -> None:
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self.create)
        self.reply = reply

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="thinking", text="ignored"), SimpleNamespace(type="text", text=self.reply)])


def test_the_proposer_sends_only_the_prompt_and_parses_the_text_block(frame) -> None:
    client = FakeClient('[{"op": "sum", "column": "Sales"}]')
    proposals = AnthropicProposer(Settings(anthropic_api_key="k"), client).propose("Orders", frame, target(1.0, ["X"]))
    assert proposals == [Measure(Op.SUM, "Sales")]
    (call,) = client.calls
    assert call["messages"][0]["content"] == build_prompt("Orders", frame, target(1.0, ["X"]))
    assert "4242" not in json.dumps(call, default=str)


def test_no_key_means_no_proposer() -> None:
    assert default_proposer(Settings(anthropic_api_key="")) is None
    assert isinstance(default_proposer(Settings(anthropic_api_key="k")), AnthropicProposer)


# --- the model proposes; computation decides ----------------------------------------------


class ScriptedProposer:
    def __init__(self, *proposals) -> None:
        self.proposals = list(proposals)
        self.asked: list[str] = []

    def propose(self, table, df, cell):
        self.asked.append(cell.id)
        if isinstance(self.proposals[0], Exception):
            raise self.proposals[0]
        return self.proposals


def run_with(frame, cells, proposer):
    return {r.target.id: r for r in ReverseEngine(frame, "Orders", proposer=proposer).run(ParsedReport(targets=cells), "r", "id").results}


def test_a_proposal_that_computes_to_the_number_is_accepted_and_labelled(frame) -> None:
    # "Sales where Cost > 15" is not something the labels or the search would ever suggest; the arithmetic agrees.
    value = 200.25 + 4242.5
    cell = target(value, ["Mystery"], ["Figure"], ident="S!B2")
    expensive = Measure(Op.SUM, "Sales", (Filter("Cost", Compare.GT, 15),))
    proposer = ScriptedProposer(Measure(Op.SUM, "Cost"), expensive)
    result = run_with(frame, [cell], proposer)["S!B2"]
    assert result.status == REPRODUCED and result.proposed_by == "language model" and result.evidence == "weak" and result.writable
    assert result.expr == expensive and result.recomputed == pytest.approx(value) and "language model suggested" in result.reasons[0]


def test_a_wrong_proposal_changes_nothing(frame) -> None:
    cell = target(777.0, ["Mystery"], ["Figure"], ident="S!B2")
    result = run_with(frame, [cell], ScriptedProposer(Measure(Op.SUM, "Sales"), Measure(Op.SUM, "Cost")))["S!B2"]
    assert result.status == NOT_REPRODUCIBLE and result.expr is None and result.proposed_by is None and not result.writable


def test_a_proposal_cannot_override_a_cell_the_search_already_proved(frame) -> None:
    cell = target(300.75, ["North"], ["Sales"], ident="S!B2")
    proposer = ScriptedProposer(Measure(Op.SUM, "Cost"))
    result = run_with(frame, [cell], proposer)["S!B2"]
    assert result.status == REPRODUCED and result.proposed_by is None and proposer.asked == []  # never even asked


def test_a_proposer_that_fails_never_breaks_the_report(frame) -> None:
    cell = target(777.0, ["Mystery"], ["Figure"], ident="S!B2")
    result = run_with(frame, [cell], ScriptedProposer(RuntimeError("rate limited")))["S!B2"]
    assert result.status == NOT_REPRODUCIBLE and any("rate limited" in note for note in result.notes)


def test_a_proposal_the_gate_rejects_is_ignored(frame) -> None:
    text_frame = frame.assign(Note=["1", "2.5", "n/a"])  # only 2 of 3 are numbers: verify() will not let it be summed
    cell = target(3.5, ["Mystery"], ["Figure"], decimals=1, shown="3.5", ident="S!B2")
    result = run_with(text_frame, [cell], ScriptedProposer(Measure(Op.SUM, "Note")))["S!B2"]
    assert result.status == NOT_REPRODUCIBLE and result.expr is None
