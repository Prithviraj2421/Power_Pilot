"""The real server, in a real process, against a stand-in for Power BI's model port.

Regression test for a bug found in real use: the server shut itself down about five seconds after every
launch, because it watched the process that launched it, and Power BI Desktop starts external tools
through a short-lived helper. The server's life must follow the model it serves, which owns a port.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from app.powerbi_live.launch_support import find_free_port

BACKEND = Path(__file__).resolve().parents[2]


def listening_socket() -> tuple[socket.socket, int]:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    return sock, sock.getsockname()[1]


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def kill_tree(process: subprocess.Popen) -> None:
    """On Windows the venv's python.exe starts the real interpreter as a child: kill both."""
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
    else:
        process.kill()
    process.wait(timeout=30)


def read(path: Path) -> str:
    return path.read_text(errors="replace")


@pytest.fixture
def server(tmp_path: Path):
    model, model_port = listening_socket()
    port = find_free_port()
    log_path = tmp_path / "server.log"
    env = {
        **os.environ,
        "POWERPILOT_DATA_DIR": str(tmp_path / "data"),
        "POWERPILOT_PBI_SERVER": f"localhost:{model_port}",
        "POWERPILOT_PBI_DATABASE": "stand-in-model",
        "POWERPILOT_PBI_TOKEN": "t0ken",
        "POWERPILOT_PBI_WATCH_INTERVAL_SECONDS": "0.3",
        "POWERPILOT_PBI_WATCH_FAILURES": "3",
    }
    with open(log_path, "wb") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=str(BACKEND),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
        try:
            deadline = time.time() + 90
            while not healthy(port):
                assert process.poll() is None, f"the server exited while starting:\n{read(log_path)}"
                assert time.time() < deadline, "the server never became healthy"
                time.sleep(0.25)
            yield process, model, log_path
        finally:
            model.close()
            kill_tree(process)


def test_the_servers_life_follows_its_model(server) -> None:
    process, model, log_path = server

    # 1. While the model is open the server stays up, far longer than the ~1 s it takes to notice a closed
    #    port. The original bug shut it down after ~5 s because it watched the launching process instead.
    time.sleep(4)
    assert process.poll() is None, f"the server stopped by itself:\n{read(log_path)}"

    # 2. Once the model goes away (the report was closed) the server stops by itself, and says why.
    model.close()
    try:
        process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        pytest.fail(f"the server kept running after its model went away:\n{read(log_path)}")
    assert "is gone; shutting down" in read(log_path)
