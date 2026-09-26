"""Tests for SMTP email delivery.

The headline test starts a real SMTP server on localhost and sends a real message
through the real client, then inspects what arrived. That is what distinguishes
this from the stub it replaced -- a stub passes any mock-based test happily, so
the assertion that matters is that bytes reached a server.
"""

from __future__ import annotations

import email
import email.policy
import smtplib
import socket
from email.message import EmailMessage
from typing import Iterator

import pytest
from aiosmtpd.controller import Controller

from app.core.config import Settings
from app.export_center.services.email_service import (
    EmailDeliveryError,
    EmailDeliveryService,
    EmailMessageSpec,
    EmailNotConfiguredError,
    InvalidRecipientError,
    parse_recipients,
)

PDF_BYTES = b"%PDF-1.4 fake report body"


class _CollectingHandler:
    """Accepts every message and keeps the raw bytes for inspection."""

    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []
        self.rcpt_tos: list[list[str]] = []

    async def handle_DATA(self, server, session, envelope):  # noqa: N802 - aiosmtpd API
        # policy=default is required for the modern EmailMessage API; the implicit
        # Compat32 policy has no content_manager, so get_content() raises.
        parsed = email.message_from_bytes(envelope.content, policy=email.policy.default)
        self.messages.append(parsed)
        self.rcpt_tos.append(list(envelope.rcpt_tos))
        return "250 Message accepted for delivery"


def _free_port() -> int:
    """Reserve a free TCP port and release it for the server to bind.

    aiosmtpd's own ``port=0`` support does not work on Windows: its readiness probe
    dials ``controller.port``, which is still 0 at that moment, and the connection
    fails with WinError 10049.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def smtp_server() -> Iterator[tuple[_CollectingHandler, int]]:
    """A real SMTP server listening on localhost."""
    handler = _CollectingHandler()
    port = _free_port()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()
    try:
        yield handler, port
    finally:
        controller.stop()


def _settings(port: int, **overrides) -> Settings:
    base = dict(
        smtp_host="127.0.0.1",
        smtp_port=port,
        smtp_from_address="bi@powerpilot.test",
        smtp_from_name="PowerPilot",
        # The local test server speaks plain SMTP, so no transport security.
        smtp_use_tls=False,
        smtp_use_ssl=False,
        smtp_timeout_seconds=10,
    )
    base.update(overrides)
    return Settings(**base)


# ---------------------------------------------------------------------------
# Real delivery
# ---------------------------------------------------------------------------


def test_message_actually_reaches_an_smtp_server(smtp_server) -> None:
    handler, port = smtp_server
    service = EmailDeliveryService(settings=_settings(port))

    result = service.send(
        EmailMessageSpec(
            recipients=("exec@example.com",),
            subject="Q3 Executive Report",
            body="The attached report covers Q3.",
            attachments={"Report.pdf": PDF_BYTES},
        )
    )

    assert result["status"] == "success"
    assert result["recipients_accepted"] == ["exec@example.com"]
    assert len(handler.messages) == 1, "the server must have actually received a message"


def test_delivered_message_has_the_expected_headers(smtp_server) -> None:
    handler, port = smtp_server
    EmailDeliveryService(settings=_settings(port)).send(
        EmailMessageSpec(
            recipients=("a@example.com", "b@example.com"),
            subject="Q3 Executive Report",
            body="Body text.",
        )
    )

    received = handler.messages[0]
    assert received["Subject"] == "Q3 Executive Report"
    assert received["From"] == "PowerPilot <bi@powerpilot.test>"
    assert "a@example.com" in received["To"]
    assert "b@example.com" in received["To"]


def test_every_recipient_is_in_the_envelope(smtp_server) -> None:
    handler, port = smtp_server
    EmailDeliveryService(settings=_settings(port)).send(
        EmailMessageSpec(
            recipients=("a@example.com", "b@example.com", "c@example.com"),
            subject="s",
            body="b",
        )
    )

    assert sorted(handler.rcpt_tos[0]) == ["a@example.com", "b@example.com", "c@example.com"]


def test_attachment_arrives_intact(smtp_server) -> None:
    """The attachment is the deliverable; a report that arrives corrupted is useless."""
    handler, port = smtp_server
    EmailDeliveryService(settings=_settings(port)).send(
        EmailMessageSpec(
            recipients=("exec@example.com",),
            subject="s",
            body="b",
            attachments={"Executive_Report.pdf": PDF_BYTES},
        )
    )

    attachments = list(handler.messages[0].iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "Executive_Report.pdf"
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_payload(decode=True) == PDF_BYTES


def test_multiple_attachments_all_arrive(smtp_server) -> None:
    handler, port = smtp_server
    xlsx = b"PK\x03\x04 fake workbook"

    EmailDeliveryService(settings=_settings(port)).send(
        EmailMessageSpec(
            recipients=("exec@example.com",),
            subject="s",
            body="b",
            attachments={"Report.pdf": PDF_BYTES, "Cleaned.xlsx": xlsx},
        )
    )

    by_name = {
        part.get_filename(): part for part in handler.messages[0].iter_attachments()
    }
    assert set(by_name) == {"Report.pdf", "Cleaned.xlsx"}
    assert by_name["Cleaned.xlsx"].get_payload(decode=True) == xlsx
    assert by_name["Cleaned.xlsx"].get_content_type() == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_body_text_is_preserved(smtp_server) -> None:
    handler, port = smtp_server
    EmailDeliveryService(settings=_settings(port)).send(
        EmailMessageSpec(
            recipients=("exec@example.com",),
            subject="s",
            body="Please review the Q3 figures.",
            attachments={"Report.pdf": PDF_BYTES},
        )
    )

    body = handler.messages[0].get_body(preferencelist=("plain",))
    assert "Please review the Q3 figures." in body.get_content()


def test_sender_omits_the_display_name_when_none_is_configured(smtp_server) -> None:
    handler, port = smtp_server
    settings = _settings(port, smtp_from_name="")

    EmailDeliveryService(settings=settings).send(
        EmailMessageSpec(recipients=("a@example.com",), subject="s", body="b")
    )

    assert handler.messages[0]["From"] == "bi@powerpilot.test"


# ---------------------------------------------------------------------------
# Failure paths -- each must raise rather than report an unverifiable success
# ---------------------------------------------------------------------------


def test_unconfigured_smtp_refuses_to_send() -> None:
    service = EmailDeliveryService(settings=Settings())

    assert service.enabled is False
    with pytest.raises(EmailNotConfiguredError, match="not configured"):
        service.send(EmailMessageSpec(recipients=("a@example.com",), subject="s", body="b"))


def test_missing_from_address_counts_as_unconfigured() -> None:
    service = EmailDeliveryService(settings=Settings(smtp_host="smtp.example.com"))
    assert service.enabled is False


def test_unreachable_server_raises_delivery_error() -> None:
    # Port 1 is reserved and nothing listens there.
    service = EmailDeliveryService(settings=_settings(1, smtp_timeout_seconds=2))

    with pytest.raises(EmailDeliveryError, match="Could not deliver"):
        service.send(EmailMessageSpec(recipients=("a@example.com",), subject="s", body="b"))


def test_server_rejecting_every_recipient_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """send_message returning refusals for all recipients is a failure, not a success."""
    service = EmailDeliveryService(settings=_settings(2525))

    class _RefusingClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, *args):
            return None

        def send_message(self, message):
            return {"a@example.com": (550, b"mailbox unavailable")}

    monkeypatch.setattr(service, "_connect", lambda: _RefusingClient())

    with pytest.raises(EmailDeliveryError, match="rejected every recipient"):
        service.send(EmailMessageSpec(recipients=("a@example.com",), subject="s", body="b"))


def test_partial_rejection_still_succeeds_but_reports_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EmailDeliveryService(settings=_settings(2525))

    class _PartialClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, *args):
            return None

        def send_message(self, message):
            return {"bad@example.com": (550, b"no such user")}

    monkeypatch.setattr(service, "_connect", lambda: _PartialClient())

    result = service.send(
        EmailMessageSpec(
            recipients=("good@example.com", "bad@example.com"), subject="s", body="b"
        )
    )

    assert result["recipients_accepted"] == ["good@example.com"]
    assert result["recipients_rejected"] == ["bad@example.com"]
    assert "rejected" in str(result["message"])


def test_authentication_failure_is_reported_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    service = EmailDeliveryService(settings=_settings(2525, smtp_username="user"))

    class _AuthFailingClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, *args):
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

        def send_message(self, message):  # pragma: no cover - never reached
            return {}

    monkeypatch.setattr(service, "_connect", lambda: _AuthFailingClient())

    with pytest.raises(EmailDeliveryError, match="rejected the configured credentials"):
        service.send(EmailMessageSpec(recipients=("a@example.com",), subject="s", body="b"))


# ---------------------------------------------------------------------------
# Recipient parsing
# ---------------------------------------------------------------------------


def test_parses_a_comma_separated_list() -> None:
    assert parse_recipients("a@example.com, b@example.com", 10) == (
        "a@example.com",
        "b@example.com",
    )


def test_trims_whitespace_and_ignores_empty_entries() -> None:
    assert parse_recipients("  a@example.com ,, b@example.com ,", 10) == (
        "a@example.com",
        "b@example.com",
    )


def test_deduplicates_case_insensitively_preserving_order() -> None:
    assert parse_recipients("A@example.com, b@example.com, a@EXAMPLE.com", 10) == (
        "A@example.com",
        "b@example.com",
    )


def test_empty_recipient_list_is_rejected() -> None:
    with pytest.raises(InvalidRecipientError, match="At least one recipient"):
        parse_recipients("   ,  ,", 10)


def test_malformed_addresses_are_rejected() -> None:
    with pytest.raises(InvalidRecipientError, match="Invalid email address"):
        parse_recipients("not-an-email, a@example.com", 10)


def test_recipient_limit_is_enforced() -> None:
    addresses = ", ".join(f"user{i}@example.com" for i in range(6))
    with pytest.raises(InvalidRecipientError, match="Too many recipients"):
        parse_recipients(addresses, 5)
