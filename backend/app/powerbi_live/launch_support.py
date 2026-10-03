"""Small, testable pieces of the External Tool launcher and server lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote, urlencode

STILL_ACTIVE = 259


def find_free_port(host: str = "127.0.0.1") -> int:
    """A TCP port nothing is listening on right now (the OS picks it)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def proc_stat_state(stat_text: str) -> str:
    """The state letter from a Linux ``/proc/<pid>/stat`` line (``Z`` is a zombie).

    The command name sits in parentheses and may itself contain spaces and parentheses, so the
    state is read after the *last* closing parenthesis.
    """
    return stat_text.rsplit(")", 1)[1].split()[0]


def process_alive(pid: int) -> bool:
    """Whether a process is still running, without affecting it.

    On Windows ``os.kill(pid, 0)`` does not probe: it *terminates* the process, so the Win32 API is used.
    """
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    # An exited child that has not been reaped yet still answers kill(pid, 0). It is dead.
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as stat:
            return proc_stat_state(stat.read()) != "Z"
    except OSError:
        return True


def watch_process(pid: int, on_gone: Callable[[], None], interval: float = 5.0) -> threading.Thread:
    """Call ``on_gone`` once ``pid`` has exited. Used so the server stops with Power BI Desktop."""

    def run() -> None:
        while process_alive(pid):
            time.sleep(interval)
        on_gone()

    thread = threading.Thread(target=run, name=f"watch-pid-{pid}", daemon=True)
    thread.start()
    return thread


# -- one backend per open model -----------------------------------------------------------------


def default_state_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(root) / "PowerPilot" / "live"


def lock_path(server: str, state_dir: Optional[Path] = None) -> Path:
    """The file recording the backend serving one model (``server`` is unique per open model)."""
    digest = hashlib.sha1(server.strip().lower().encode("utf-8")).hexdigest()[:12]
    return (state_dir or default_state_dir()) / f"{digest}.json"


def write_lock(path: Path, *, port: int, pid: int, token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"port": port, "pid": pid, "token": token}), encoding="utf-8")


def read_lock(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not all(isinstance(data.get(k), (int, str)) for k in ("port", "pid", "token")):
        return None
    return data


def reusable_session(
    server: str,
    state_dir: Optional[Path] = None,
    is_alive: Callable[[int], bool] = process_alive,
    healthy: Callable[[int], bool] = lambda port: True,
) -> Optional[dict]:
    """The running backend for this model, if there is one, so a second click reuses it."""
    path = lock_path(server, state_dir)
    data = read_lock(path)
    if data is None:
        return None
    if is_alive(int(data["pid"])) and healthy(int(data["port"])):
        return data
    try:
        path.unlink()
    except OSError:
        pass
    return None


def ui_url(port: int, server: str, database: str, token: str) -> str:
    """Where to open the UI. The token rides in the fragment so it is never sent to a server or logged."""
    query = urlencode({"server": server, "db": database}, quote_via=quote)
    return f"http://127.0.0.1:{port}/live?{query}#token={quote(token, safe='')}"
