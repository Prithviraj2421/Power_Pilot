"""End-to-end tests for the email distribution endpoint.

These drive the real HTTP route, which builds a real PDF from a real analysis and
hands it to the real SMTP client, against a real SMTP server on localhost. The
only thing not exercised is the public internet.
"""

from __future__ import annotations

import email
import email.policy
import socket
from typing import Iterator

import pytest
from aiosmtpd.controller import Controller
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

BASE = "/api/v1/export-center"


class _CollectingHandler:
    def __init__(self) -> None:
        self.messages: list = []

    async def handle_DATA(self, server, session, envelope):  # noqa: N802 - aiosmtpd API
        self.messages.append(
            email.message_from_bytes(envelope.content, policy=email.policy.default)
        )
        return "250 OK"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def mail_server() -> Iterator[_CollectingHandler]:
    """A real SMTP server, wired into the app via a settings override."""
    handler = _CollectingHandler()
    port = _free_port()
    controller = Controller(handler, hostname="127.0.0.1", port=port)
    controller.start()

    base = get_settings()
    app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=base.data_dir,
        smtp_host="127.0.0.1",
        smtp_port=port,
        smtp_from_address="bi@powerpilot.test",
        smtp_from_name="PowerPilot",
        smtp_use_tls=False,
        smtp_use_ssl=False,
        smtp_timeout_seconds=10,
        max_email_recipients=5,
    )
    try:
        yield handler
    finally:
        app.dependency_overrides.pop(get_settings, None)
        controller.stop()


# ---------------------------------------------------------------------------
# Unconfigured server
# ---------------------------------------------------------------------------


def test_status_reports_email_disabled_by_default(client: TestClient) -> None:
    response = client.get(f"{BASE}/email/status")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert "POWERPILOT_SMTP_HOST" in body["detail"]


def test_status_never_echoes_credentials(client: TestClient) -> None:
    body = client.get(f"{BASE}/email/status").json()

    assert "smtp_password" not in body
    assert "password" not in str(body).lower()


def test_send_returns_503_when_smtp_is_unconfigured(
    client: TestClient, registered_dataset_id: str
) -> None:
    """Unconfigured must fail loudly. The old stub reported success and sent nothing."""
    response = client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "exec@example.com"},
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "no message was sent" in detail.lower()


# ---------------------------------------------------------------------------
# Configured server
# ---------------------------------------------------------------------------


def test_status_reports_enabled_once_configured(
    client: TestClient, mail_server: _CollectingHandler
) -> None:
    body = client.get(f"{BASE}/email/status").json()

    assert body["enabled"] is True
    assert body["smtp_host"] == "127.0.0.1"
    assert body["from_address"] == "bi@powerpilot.test"


def test_report_is_actually_delivered(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    response = client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "exec@example.com", "subject": "Q3 Report"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["recipients_accepted"] == ["exec@example.com"]
    assert body["dataset_name"] == "retail.csv"
    assert len(mail_server.messages) == 1, "a message must have reached the server"
    assert mail_server.messages[0]["Subject"] == "Q3 Report"


def test_delivered_message_carries_a_real_pdf(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    """The attachment must be the genuine generated report, not a placeholder."""
    client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "exec@example.com"},
    )

    attachments = list(mail_server.messages[0].iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename().endswith(".pdf")
    assert "retail" in attachments[0].get_filename()

    payload = attachments[0].get_payload(decode=True)
    assert payload[:5] == b"%PDF-"
    assert len(payload) > 10_000, "a real executive report, not a stub"


def test_both_attachments_can_be_requested(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "exec@example.com", "attach": "both"},
    )

    names = [part.get_filename() for part in mail_server.messages[0].iter_attachments()]
    assert any(name.endswith(".pdf") for name in names)
    assert any(name.endswith(".xlsx") for name in names)


def test_multiple_recipients_are_delivered(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    response = client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "a@example.com, b@example.com"},
    )

    assert response.json()["recipients_accepted"] == ["a@example.com", "b@example.com"]
    assert len(mail_server.messages) == 1


def test_custom_body_reaches_the_message(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "exec@example.com", "body_message": "Board review Friday."},
    )

    body = mail_server.messages[0].get_body(preferencelist=("plain",))
    assert "Board review Friday." in body.get_content()


def test_emailing_records_the_export_in_history(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    before = client.get(f"{BASE}/history", params={"dataset_id": registered_dataset_id}).json()

    client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "exec@example.com"},
    )

    after = client.get(f"{BASE}/history", params={"dataset_id": registered_dataset_id}).json()
    assert after["total"] > before["total"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_malformed_recipient_is_rejected_with_400(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    response = client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "not-an-email"},
    )

    assert response.status_code == 400
    assert "Invalid email address" in response.json()["detail"]
    assert mail_server.messages == [], "nothing may be sent when validation fails"


def test_empty_recipient_list_is_rejected_with_400(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    response = client.post(
        f"{BASE}/{registered_dataset_id}/email", params={"recipients": " , , "}
    )

    assert response.status_code == 400
    assert "At least one recipient" in response.json()["detail"]


def test_recipient_limit_is_enforced(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    addresses = ", ".join(f"user{index}@example.com" for index in range(6))
    response = client.post(
        f"{BASE}/{registered_dataset_id}/email", params={"recipients": addresses}
    )

    assert response.status_code == 400
    assert "Too many recipients" in response.json()["detail"]


def test_unknown_dataset_returns_404(
    client: TestClient, mail_server: _CollectingHandler
) -> None:
    response = client.post(
        f"{BASE}/deadbeef/email", params={"recipients": "exec@example.com"}
    )

    assert response.status_code == 404


def test_invalid_attachment_choice_is_rejected(
    client: TestClient, registered_dataset_id: str, mail_server: _CollectingHandler
) -> None:
    response = client.post(
        f"{BASE}/{registered_dataset_id}/email",
        params={"recipients": "exec@example.com", "attach": "docx"},
    )

    assert response.status_code == 422


def test_unreachable_mail_server_returns_502(
    client: TestClient, registered_dataset_id: str
) -> None:
    """A failing upstream mail server is a bad gateway, not a silent success."""
    base = get_settings()
    app.dependency_overrides[get_settings] = lambda: Settings(
        data_dir=base.data_dir,
        smtp_host="127.0.0.1",
        smtp_port=1,  # reserved; nothing listens
        smtp_from_address="bi@powerpilot.test",
        smtp_use_tls=False,
        smtp_timeout_seconds=2,
    )
    try:
        response = client.post(
            f"{BASE}/{registered_dataset_id}/email",
            params={"recipients": "exec@example.com"},
        )
        assert response.status_code == 502
        assert "Could not deliver" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_settings, None)
