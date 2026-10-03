from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from app.powerbi_live.dll_locator import REQUIRED, DllNotFoundError, candidate_dirs, find_dll_dir
from app.powerbi_live.launch_support import (
    find_free_port,
    lock_path,
    proc_stat_state,
    process_alive,
    read_lock,
    reusable_session,
    ui_url,
    watch_process,
    write_lock,
)
from app.powerbi_live.security import token_matches, validate_database_name, validate_model_address

# -- the model address and name are only ever trusted after validation -----------------------------


@pytest.mark.parametrize("server", ["localhost:51234", "127.0.0.1:9", "LOCALHOST:65535", "  localhost:80  "])
def test_loopback_addresses_are_accepted(server: str) -> None:
    assert validate_model_address(server) == server.strip()


@pytest.mark.parametrize(
    "server",
    [
        "example.com:51234", "localhost", "localhost:", "localhost:0", "localhost:65536", "localhost:123;Extra=1",
        "http://localhost:80", "localhost:80/path", "0.0.0.0:80", "192.168.1.5:80", "[::1]:80", "",
        "localhost:80 ", "localhost.evil.com:80", "evil.com#localhost:80",
    ],
)
def test_anything_that_is_not_a_plain_loopback_host_and_port_is_refused(server: str) -> None:
    if server == "localhost:80 ":  # trailing space is trimmed, so this one is valid
        assert validate_model_address(server) == "localhost:80"
        return
    with pytest.raises(ValueError):
        validate_model_address(server)


@pytest.mark.parametrize("name", ["3f2a1c9e-1b2d-4c5e-8f00-123456789abc", "Model_1", "a b", "{GUID-1}"])
def test_ordinary_model_names_are_accepted(name: str) -> None:
    assert validate_database_name(name) == name


@pytest.mark.parametrize("name", ["", "x; Data Source=evil", 'x"y', "a=b", "x" * 200, "line\nbreak", "a'b"])
def test_names_that_could_alter_a_connection_string_are_refused(name: str) -> None:
    with pytest.raises(ValueError):
        validate_database_name(name)


def test_token_comparison() -> None:
    assert token_matches("abc", "abc")
    assert not token_matches("abc", "abd") and not token_matches("abc", "abcd") and not token_matches("abc", None)
    assert not token_matches("", "") and not token_matches("", None) and not token_matches("", "x")
    assert token_matches("tökén", "tökén"), "non-ASCII must not raise"


# -- launcher helpers --------------------------------------------------------------------------


def test_a_free_port_can_be_bound_straight_away() -> None:
    port = find_free_port()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", port))
    assert 1024 <= port <= 65535


def test_process_alive_tells_a_running_process_from_an_exited_one() -> None:
    assert process_alive(os.getpid())
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    assert not process_alive(child.pid)
    assert not process_alive(0) and not process_alive(-5)


def test_probing_a_process_does_not_affect_it() -> None:
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        for _ in range(3):
            assert process_alive(sleeper.pid)
        assert sleeper.poll() is None, "checking liveness must never terminate the process"
    finally:
        sleeper.kill()
        sleeper.wait()


def test_the_watcher_fires_once_the_parent_exits() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.6)"])
    # Reap the child as soon as it exits, as a real parent would; an unreaped child is a zombie on Linux.
    threading.Thread(target=child.wait, daemon=True).start()
    fired = threading.Event()

    watch_process(child.pid, fired.set, interval=0.05)

    assert fired.wait(timeout=15), "the watcher never noticed the process exit"


@pytest.mark.skipif(sys.platform == "win32", reason="zombie processes are a POSIX concept")
def test_a_zombie_counts_as_dead() -> None:
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    try:
        deadline = time.time() + 10
        while process_alive(child.pid) and time.time() < deadline:
            time.sleep(0.05)  # the child has exited but is deliberately not reaped yet
        assert not process_alive(child.pid), "an exited, unreaped child must not look alive"
    finally:
        child.wait()


@pytest.mark.parametrize(
    ("line", "state"),
    [
        ("1234 (python3) S 1 1234 1234 0 -1 4194560 100 0", "S"),
        ("77 (python) Z 1 77 77 0 -1 4227076 0 0", "Z"),
        ("9 (my app (v2) x) R 1 9 9 0 -1 0 0 0", "R"),  # a name with spaces and parentheses
        ("5 (weird) name)) Z 1 5 5 0", "Z"),
    ],
)
def test_the_process_state_is_read_after_the_last_parenthesis(line: str, state: str) -> None:
    assert proc_stat_state(line) == state


def test_the_watcher_stays_quiet_while_the_parent_runs() -> None:
    fired = threading.Event()
    watch_process(os.getpid(), fired.set, interval=0.05)

    assert not fired.wait(timeout=0.5)


def test_lock_files_are_per_model_and_case_insensitive(tmp_path: Path) -> None:
    assert lock_path("localhost:1000", tmp_path) == lock_path("LOCALHOST:1000", tmp_path)
    assert lock_path("localhost:1000", tmp_path) != lock_path("localhost:1001", tmp_path)


def test_a_lock_round_trips_and_garbage_is_ignored(tmp_path: Path) -> None:
    path = lock_path("localhost:1000", tmp_path)
    write_lock(path, port=8123, pid=42, token="t0k")

    assert read_lock(path) == {"port": 8123, "pid": 42, "token": "t0k"}
    path.write_text("not json", encoding="utf-8")
    assert read_lock(path) is None
    path.write_text('{"port": "x"}', encoding="utf-8")
    assert read_lock(path) is None
    assert read_lock(tmp_path / "missing.json") is None


def test_a_second_click_reuses_a_healthy_backend(tmp_path: Path) -> None:
    write_lock(lock_path("localhost:1000", tmp_path), port=8123, pid=42, token="t0k")

    session = reusable_session("localhost:1000", tmp_path, is_alive=lambda pid: True, healthy=lambda port: True)

    assert session == {"port": 8123, "pid": 42, "token": "t0k"}


@pytest.mark.parametrize(("alive", "healthy"), [(False, True), (True, False), (False, False)])
def test_a_dead_or_unresponsive_backend_is_not_reused_and_its_lock_is_cleared(tmp_path: Path, alive, healthy) -> None:
    path = lock_path("localhost:1000", tmp_path)
    write_lock(path, port=8123, pid=42, token="t0k")

    session = reusable_session("localhost:1000", tmp_path, is_alive=lambda pid: alive, healthy=lambda port: healthy)

    assert session is None and not path.exists()


def test_another_models_backend_is_never_reused(tmp_path: Path) -> None:
    write_lock(lock_path("localhost:2000", tmp_path), port=8123, pid=42, token="t0k")

    assert reusable_session("localhost:1000", tmp_path, is_alive=lambda pid: True) is None


def test_the_ui_url_keeps_the_token_in_the_fragment() -> None:
    url = ui_url(8123, "localhost:51234", "{GUID 1}", "tok/en+1=")
    parts = urlsplit(url)

    assert (parts.scheme, parts.hostname, parts.port, parts.path) == ("http", "127.0.0.1", 8123, "/live")
    assert parse_qs(parts.query) == {"server": ["localhost:51234"], "db": ["{GUID 1}"]}
    assert "tok" not in parts.query, "the token must never reach the server or its logs"
    assert parts.fragment == "token=tok%2Fen%2B1%3D"


# -- locating the Analysis Services libraries ---------------------------------------------------


def make_install(folder: Path, missing: tuple[str, ...] = ()) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED:
        if name not in missing:
            (folder / name).write_bytes(b"")
    return folder


def test_the_libraries_are_found_in_a_complete_folder(tmp_path: Path) -> None:
    assert find_dll_dir(candidates=[tmp_path / "nope", make_install(tmp_path / "pbi")]) == tmp_path / "pbi"


def test_a_folder_missing_any_one_library_is_rejected(tmp_path: Path) -> None:
    partial = make_install(tmp_path / "partial", missing=(REQUIRED[1],))

    with pytest.raises(DllNotFoundError):
        find_dll_dir(candidates=[partial])


def test_the_error_says_where_it_looked_and_what_to_do(tmp_path: Path) -> None:
    with pytest.raises(DllNotFoundError) as caught:
        find_dll_dir(candidates=[tmp_path / "a", tmp_path / "b"])

    message = str(caught.value)
    assert str(tmp_path / "a") in message and str(tmp_path / "b") in message
    assert "POWERPILOT_TOM_DLL_DIR" in message and REQUIRED[0] in message


def test_an_explicit_folder_is_tried_before_the_default_locations(tmp_path: Path) -> None:
    assert candidate_dirs(str(tmp_path / "mine"))[0] == tmp_path / "mine"
    assert candidate_dirs("") == candidate_dirs(None) == candidate_dirs("   ")
