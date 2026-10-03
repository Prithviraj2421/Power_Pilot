"""The External Tools launcher, with its process, browser and health check replaced by fakes."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from app.powerbi_live.launch_support import lock_path, read_lock, write_lock

LAUNCHER = Path(__file__).parents[3] / "tools" / "powerbi-external-tool" / "launcher.py"
SERVER, DB = "localhost:51234", "3f2a1c9e-aaaa-bbbb-cccc-123456789abc"


@pytest.fixture(scope="module")
def launcher():
    spec = importlib.util.spec_from_file_location("pp_launcher", LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeProcess:
    pid = 4242

    def __init__(self, exits_with=None) -> None:
        self.exits_with = exits_with
        self.killed = False

    def poll(self):
        return self.exits_with

    def kill(self) -> None:
        self.killed = True


class Recorder:
    def __init__(self, process=None) -> None:
        self.process = process or FakeProcess()
        self.spawned: list[dict] = []
        self.opened: list[str] = []
        self.errors: list[str] = []

    def spawn(self, command, **kwargs):
        self.spawned.append({"command": command, **kwargs})
        return self.process

    def run(self, launcher, tmp_path: Path, argv, *, healthy=lambda port: True, dist=True, **kwargs) -> int:
        built = tmp_path / "dist"
        if dist:
            built.mkdir(exist_ok=True)
            (built / "index.html").write_text("<html></html>", encoding="utf-8")
        return launcher.main(
            argv,
            spawn=self.spawn,
            open_browser=self.opened.append,
            healthy=healthy,
            error=self.errors.append,
            state_dir=tmp_path / "state",
            dist=built,
            sleep=lambda s: None,
            **kwargs,
        )


def test_a_fresh_launch_starts_one_loopback_server_with_the_models_address_and_a_token(launcher, tmp_path) -> None:
    rec = Recorder()

    code = rec.run(launcher, tmp_path, [SERVER, DB], parent_pid=777)

    assert code == 0 and rec.errors == []
    (call,) = rec.spawned
    command, env = call["command"], call["env"]
    assert command[1:5] == ["-m", "uvicorn", "app.main:app", "--host"] and command[5] == "127.0.0.1"
    assert env["POWERPILOT_PBI_SERVER"] == SERVER and env["POWERPILOT_PBI_DATABASE"] == DB
    assert env["POWERPILOT_PARENT_PID"] == "777"
    assert env["POWERPILOT_SERVE_FRONTEND"] == str(tmp_path / "dist")
    assert len(env["POWERPILOT_PBI_TOKEN"]) >= 24
    assert call["cwd"].endswith("backend")


def test_the_browser_opens_the_live_page_with_the_token_in_the_fragment_only(launcher, tmp_path) -> None:
    rec = Recorder()
    rec.run(launcher, tmp_path, [SERVER, DB])

    (url,) = rec.opened
    parts = urlsplit(url)
    token = rec.spawned[0]["env"]["POWERPILOT_PBI_TOKEN"]
    port = int(rec.spawned[0]["command"][-1])
    assert (parts.hostname, parts.port, parts.path) == ("127.0.0.1", port, "/live")
    assert parse_qs(parts.query) == {"server": [SERVER], "db": [DB]}
    assert parts.fragment == f"token={token}" and token not in parts.query


def test_the_running_server_is_recorded_so_the_next_click_can_find_it(launcher, tmp_path) -> None:
    rec = Recorder()
    rec.run(launcher, tmp_path, [SERVER, DB])

    lock = read_lock(lock_path(SERVER, tmp_path / "state"))

    assert lock["pid"] == 4242 and lock["port"] == int(rec.spawned[0]["command"][-1])
    assert lock["token"] == rec.spawned[0]["env"]["POWERPILOT_PBI_TOKEN"]


def test_a_second_click_reuses_the_running_server_and_its_token(launcher, tmp_path) -> None:
    # The recorded backend is a process that really is alive: this test process.
    write_lock(lock_path(SERVER, tmp_path / "state"), port=8123, pid=os.getpid(), token="existing-token")
    rec = Recorder()

    code = rec.run(launcher, tmp_path, [SERVER, DB])

    assert code == 0 and rec.spawned == [], "no second server for the same model"
    assert rec.opened == [f"http://127.0.0.1:8123/live?server=localhost%3A51234&db={DB}#token=existing-token"]


def test_a_different_model_gets_its_own_server(launcher, tmp_path) -> None:
    write_lock(lock_path("localhost:60000", tmp_path / "state"), port=8123, pid=os.getpid(), token="other-models")
    rec = Recorder()

    rec.run(launcher, tmp_path, [SERVER, DB])

    assert len(rec.spawned) == 1 and "other-models" not in rec.opened[0]


@pytest.mark.parametrize(
    ("argv", "fragment"),
    [
        (["example.com:51234", DB], "local Power BI model address"),
        (["localhost:51234;x=1", DB], "local Power BI model address"),
        ([SERVER, "x; Data Source=evil"], "not allowed"),
    ],
)
def test_an_address_or_name_it_will_not_trust_is_reported_and_nothing_starts(launcher, tmp_path, argv, fragment) -> None:
    rec = Recorder()

    code = rec.run(launcher, tmp_path, argv)

    assert code == 2 and rec.spawned == [] and rec.opened == []
    assert fragment in rec.errors[0]


def test_a_missing_frontend_build_says_how_to_build_it(launcher, tmp_path) -> None:
    rec = Recorder()

    code = rec.run(launcher, tmp_path, [SERVER, DB], dist=False)

    assert code == 3 and "npm run build" in rec.errors[0] and rec.spawned == []


def test_a_server_that_dies_on_start_is_reported_with_its_log(launcher, tmp_path) -> None:
    rec = Recorder(FakeProcess(exits_with=1))

    code = rec.run(launcher, tmp_path, [SERVER, DB], healthy=lambda port: False)

    assert code == 4 and "did not start" in rec.errors[0] and "Log:" in rec.errors[0]
    assert rec.opened == [] and read_lock(lock_path(SERVER, tmp_path / "state")) is None


def test_a_server_that_never_answers_is_killed_and_reported(launcher, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(launcher, "STARTUP_TIMEOUT_SECONDS", -1)
    process = FakeProcess()
    rec = Recorder(process)

    code = rec.run(launcher, tmp_path, [SERVER, DB], healthy=lambda port: False)

    assert code == 4 and process.killed and rec.opened == []


def test_the_launcher_waits_for_the_server_before_opening_the_browser(launcher, tmp_path) -> None:
    answers = iter([False, False, True])
    rec = Recorder()

    rec.run(launcher, tmp_path, [SERVER, DB], healthy=lambda port: next(answers))

    assert len(rec.opened) == 1


# -- the registration file the installer writes ----------------------------------------------------


def test_the_registration_template_is_valid_and_uses_only_the_two_documented_placeholders() -> None:
    template = Path(__file__).parents[3] / "tools" / "powerbi-external-tool" / "powerpilot.pbitool.json"
    data = json.loads(template.read_text(encoding="utf-8"))

    assert data["name"] == "PowerPilot" and data["version"] == "1.0.0"
    assert data["path"] == "__PYTHONW__" and "__LAUNCHER__" in data["arguments"]
    assert data["arguments"].endswith('"%server%" "%database%"')
    assert data["iconData"].startswith("image/png;base64,"), "Desktop wants a data URI without the 'data:' prefix"


def test_a_recorded_backend_that_has_died_is_replaced_not_reused(launcher, tmp_path) -> None:
    import subprocess
    import sys

    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    write_lock(lock_path(SERVER, tmp_path / "state"), port=8123, pid=gone.pid, token="stale-token")
    rec = Recorder()

    rec.run(launcher, tmp_path, [SERVER, DB])

    assert len(rec.spawned) == 1 and "stale-token" not in rec.opened[0]
    assert read_lock(lock_path(SERVER, tmp_path / "state"))["token"] != "stale-token"
