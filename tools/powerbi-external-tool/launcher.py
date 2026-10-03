"""Power BI Desktop External Tools entry point.

Desktop runs this with the open model's address and name (``%server%`` and ``%database%``):

    pythonw.exe launcher.py "localhost:51234" "<model guid>"

It starts (or reuses) one PowerPilot backend for that model and opens the UI in the browser. The backend
serves the built frontend itself, listens only on 127.0.0.1, and exits when Power BI Desktop does.
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Callable, Optional, Sequence

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))

from app.powerbi_live.launch_support import (  # noqa: E402
    default_state_dir,
    find_free_port,
    lock_path,
    reusable_session,
    ui_url,
    write_lock,
)
from app.powerbi_live.security import validate_database_name, validate_model_address  # noqa: E402

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
STARTUP_TIMEOUT_SECONDS = 45


def show_error(message: str) -> None:
    """A message box: pythonw has no console, so printing would show the user nothing."""
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "PowerPilot", 0x10)  # MB_ICONERROR
    else:
        print(message, file=sys.stderr)


def backend_healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def server_python() -> str:
    """The console interpreter next to this one: uvicorn must not be started under pythonw."""
    exe = Path(sys.executable)
    candidate = exe.with_name("python.exe") if exe.name.lower() == "pythonw.exe" else exe
    return str(candidate)


def tail(path: Path, lines: int = 12) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return "(no log was written)"


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    spawn: Callable[..., "subprocess.Popen"] = subprocess.Popen,
    open_browser: Callable[[str], object] = webbrowser.open,
    healthy: Callable[[int], bool] = backend_healthy,
    error: Callable[[str], None] = show_error,
    state_dir: Optional[Path] = None,
    dist: Optional[Path] = None,
    sleep: Callable[[float], None] = time.sleep,
    parent_pid: Optional[int] = None,
) -> int:
    parser = argparse.ArgumentParser(description="Start PowerPilot for the model open in Power BI Desktop.")
    parser.add_argument("server", help="Desktop's %%server%% (localhost:port)")
    parser.add_argument("database", help="Desktop's %%database%% (the model's name)")
    parser.add_argument("--parent-pid", type=int, default=None, help="process to stop with (default: whoever started this)")
    args = parser.parse_args(argv)

    try:
        server = validate_model_address(args.server)
        database = validate_database_name(args.database)
    except ValueError as exc:
        error(f"PowerPilot was given a model address it will not use.\n\n{exc}")
        return 2

    dist = dist or REPO / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        error(f"PowerPilot's interface has not been built.\n\nRun `npm run build` in:\n{dist.parent}")
        return 3

    state = state_dir or default_state_dir()
    existing = reusable_session(server, state, healthy=healthy)
    if existing is not None:
        open_browser(ui_url(int(existing["port"]), server, database, str(existing["token"])))
        return 0

    port, token = find_free_port(), secrets.token_urlsafe(24)
    watched = parent_pid if parent_pid is not None else (args.parent_pid or os.getppid())
    env = {
        **os.environ,
        "POWERPILOT_PBI_SERVER": server,
        "POWERPILOT_PBI_DATABASE": database,
        "POWERPILOT_PBI_TOKEN": token,
        "POWERPILOT_SERVE_FRONTEND": str(dist),
        "POWERPILOT_PARENT_PID": str(watched),
    }
    state.mkdir(parents=True, exist_ok=True)
    log_path = state / f"backend-{port}.log"
    flags = (CREATE_NO_WINDOW | DETACHED_PROCESS) if sys.platform == "win32" else 0

    with open(log_path, "wb") as log:
        process = spawn(
            [server_python(), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(BACKEND),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
        )

    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while not healthy(port):
        if process.poll() is not None or time.monotonic() > deadline:
            if process.poll() is None:
                process.kill()
            error(f"PowerPilot's server did not start.\n\n{tail(log_path)}\n\nLog: {log_path}")
            return 4
        sleep(0.25)

    write_lock(lock_path(server, state), port=port, pid=process.pid, token=token)
    open_browser(ui_url(port, server, database, token))
    return 0


if __name__ == "__main__":
    sys.exit(main())
