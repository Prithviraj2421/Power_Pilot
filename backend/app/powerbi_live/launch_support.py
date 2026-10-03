"""Small, testable pieces of the External Tool launcher and server lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import signal
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


def port_open(port: int, timeout: float = 1.0) -> bool:
    """Whether something accepts connections on this local port (the engine listens on IPv4 and IPv6).

    Windows takes about two seconds to refuse a connection to a closed local port, so the timeout also
    bounds how long a check on a closed port can take; a timeout is simply a miss.
    """
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def watch_port(
    port: int,
    on_gone: Callable[[], None],
    *,
    interval: float = 5.0,
    failures: int = 3,
    is_open: Callable[[int], bool] = port_open,
) -> threading.Thread:
    """Call ``on_gone`` once nothing has accepted connections on ``port`` for ``failures`` checks in a row.

    The server exists to serve one open Power BI model, and that model's engine owns this port, so the
    port closing is the real signal that the report was closed. Watching a process instead does not
    work: Power BI Desktop starts external tools through a short-lived helper, so the launching
    process exits within seconds while the report is still open. A single failed check is ignored,
    and the first check only happens after one full interval.
    """

    def run() -> None:
        misses = 0
        while True:
            time.sleep(interval)
            misses = 0 if is_open(port) else misses + 1
            if misses >= failures:
                on_gone()
                return

    thread = threading.Thread(target=run, name=f"watch-port-{port}", daemon=True)
    thread.start()
    return thread


def shutdown_gracefully(grace: float = 10.0) -> None:
    """Stop the server the way Ctrl+C would, and force the exit if it has not stopped within ``grace``."""
    timer = threading.Timer(grace, lambda: os._exit(0))
    timer.daemon = True
    timer.start()
    signal.raise_signal(signal.SIGTERM)


def start_model_watchdog(
    server: str,
    *,
    interval: float,
    failures: int,
    stop: Callable[[], None] = shutdown_gracefully,
    watch: Callable[..., threading.Thread] = watch_port,
) -> Optional[threading.Thread]:
    """Stop the server when the model at ``server`` ("localhost:<port>") goes away. None if there is no model."""
    from app.powerbi_live.security import validate_model_address

    if not server.strip():
        return None
    try:
        port = int(validate_model_address(server).rsplit(":", 1)[1])
    except ValueError:
        return None
    return watch(port, stop, interval=interval, failures=failures)


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
