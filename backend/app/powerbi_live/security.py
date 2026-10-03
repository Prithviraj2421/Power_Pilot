from __future__ import annotations

import re
import secrets
from typing import Optional

# Desktop's embedded Analysis Services always listens on localhost with a random port.
_ADDRESS = re.compile(r"^(?:localhost|127\.0\.0\.1):(?P<port>\d{1,5})$", re.IGNORECASE)
_DATABASE = re.compile(r"^[A-Za-z0-9._\-{} ]{1,128}$")

TOKEN_HEADER = "X-PowerPilot-Token"


def validate_model_address(server: str) -> str:
    """The model address if it is loopback ``host:port``; otherwise ``ValueError``.

    The address is only ever taken from the launcher's environment, but it is still validated: a
    tool that connects wherever it is told and then writes to that endpoint is a poor primitive.
    """
    candidate = server.strip()
    match = _ADDRESS.match(candidate)
    if not match or not 0 < int(match.group("port")) < 65536:
        raise ValueError(f"'{server}' is not a local Power BI model address (expected localhost:<port>)")
    return candidate


def validate_database_name(database: str) -> str:
    """The model name if it contains nothing that could alter a connection string."""
    candidate = database.strip()
    if not _DATABASE.match(candidate):
        raise ValueError("the model name contains characters that are not allowed")
    return candidate


def token_matches(expected: str, supplied: Optional[str]) -> bool:
    """Constant-time comparison. An empty expected token never matches, so it cannot be left open."""
    if not expected or not supplied:
        return False
    return secrets.compare_digest(expected.encode("utf-8"), supplied.encode("utf-8"))
