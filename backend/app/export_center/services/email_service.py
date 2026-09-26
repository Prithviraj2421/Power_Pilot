"""Outbound email delivery over SMTP.

This replaces a stub that awaited ``asyncio.sleep(0.5)`` and returned
``{"status": "success"}`` without contacting any mail server, while the UI showed
a success toast for the report it had silently discarded.

Plain SMTP is used rather than a provider SDK so one set of settings works
against Gmail, Amazon SES's SMTP endpoint, SendGrid's SMTP relay or a self-hosted
server. Delivery is synchronous and blocking; callers are FastAPI's sync route
handlers, which run in the worker threadpool, so the event loop is not held.
"""

from __future__ import annotations

import re
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Mapping, Optional, Sequence

from app.common.logger import get_logger
from app.core.config import Settings, get_settings

logger = get_logger("EmailService")

# Deliberately permissive: real deliverability is decided by the mail server, and
# an over-strict client-side pattern rejects valid addresses. This only catches
# obvious typos before a connection is opened.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")


class EmailError(Exception):
    """Base class for email delivery failures."""


class EmailNotConfiguredError(EmailError):
    """Raised when SMTP settings are absent, so no send can be attempted."""


class InvalidRecipientError(EmailError):
    """Raised when the recipient list is empty or malformed."""


class EmailDeliveryError(EmailError):
    """Raised when the mail server rejected or failed to accept the message."""


@dataclass(slots=True, frozen=True)
class EmailMessageSpec:
    """Everything needed to build one outbound message."""

    recipients: tuple[str, ...]
    subject: str
    body: str
    attachments: Mapping[str, bytes] = field(default_factory=dict)


def parse_recipients(raw: str, max_recipients: int) -> tuple[str, ...]:
    """Split and validate a comma-separated recipient string.

    Raises ``InvalidRecipientError`` with a client-safe message.
    """
    candidates = [part.strip() for part in raw.split(",")]
    recipients = [candidate for candidate in candidates if candidate]

    if not recipients:
        raise InvalidRecipientError("At least one recipient email address is required.")

    if len(recipients) > max_recipients:
        raise InvalidRecipientError(
            f"Too many recipients: {len(recipients)}. The maximum is {max_recipients}."
        )

    invalid = [address for address in recipients if not _EMAIL_PATTERN.match(address)]
    if invalid:
        raise InvalidRecipientError(
            f"Invalid email address(es): {', '.join(invalid)}."
        )

    # Preserve order while removing duplicates, so one person is not mailed twice.
    seen: set[str] = set()
    unique: list[str] = []
    for address in recipients:
        lowered = address.lower()
        if lowered not in seen:
            seen.add(lowered)
            unique.append(address)

    return tuple(unique)


class EmailDeliveryService:
    """Builds and sends report emails over SMTP."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = get_settings() if settings is None else settings

    @property
    def enabled(self) -> bool:
        return self._settings.email_enabled

    def build_message(self, spec: EmailMessageSpec) -> EmailMessage:
        """Assemble the MIME message, including any attachments."""
        settings = self._settings

        message = EmailMessage()
        message["From"] = settings.smtp_sender
        message["To"] = ", ".join(spec.recipients)
        message["Subject"] = spec.subject
        message.set_content(spec.body)

        for filename, payload in spec.attachments.items():
            maintype, subtype = _guess_mime(filename)
            message.add_attachment(
                payload, maintype=maintype, subtype=subtype, filename=filename
            )

        return message

    def send(self, spec: EmailMessageSpec) -> dict[str, object]:
        """Deliver the message. Raises rather than reporting a success it cannot verify."""
        settings = self._settings

        if not settings.email_enabled:
            raise EmailNotConfiguredError(
                "Email delivery is not configured. Set POWERPILOT_SMTP_HOST and "
                "POWERPILOT_SMTP_FROM_ADDRESS (see backend/.env.example) to enable it."
            )

        if not spec.recipients:
            raise InvalidRecipientError("At least one recipient email address is required.")

        message = self.build_message(spec)

        try:
            with self._connect() as client:
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password)
                refused = client.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            logger.error(f"SMTP authentication failed for {settings.smtp_host}: {exc}")
            raise EmailDeliveryError(
                "The mail server rejected the configured credentials."
            ) from exc
        except (smtplib.SMTPException, OSError) as exc:
            logger.error(f"SMTP delivery to {settings.smtp_host} failed: {exc}")
            raise EmailDeliveryError(f"Could not deliver the email: {exc}") from exc

        accepted = [address for address in spec.recipients if address not in (refused or {})]
        rejected = sorted(refused or {})

        if not accepted:
            raise EmailDeliveryError(
                f"The mail server rejected every recipient: {', '.join(rejected)}."
            )

        logger.info(
            f"Delivered '{spec.subject}' to {len(accepted)} recipient(s) via "
            f"{settings.smtp_host}:{settings.smtp_port}"
            + (f"; rejected: {rejected}" if rejected else "")
        )

        return {
            "status": "success",
            "recipients_accepted": accepted,
            "recipients_rejected": rejected,
            "attachments_included": list(spec.attachments),
            "message": (
                f"Delivered to {len(accepted)} recipient(s)."
                + (f" {len(rejected)} address(es) were rejected." if rejected else "")
            ),
        }

    def _connect(self) -> smtplib.SMTP:
        """Open an SMTP connection using the configured transport security."""
        settings = self._settings

        if settings.smtp_use_ssl:
            return smtplib.SMTP_SSL(
                host=settings.smtp_host,
                port=settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
                context=ssl.create_default_context(),
            )

        client = smtplib.SMTP(
            host=settings.smtp_host,
            port=settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        )
        if settings.smtp_use_tls:
            client.starttls(context=ssl.create_default_context())
        return client


def _guess_mime(filename: str) -> tuple[str, str]:
    """Map a report filename to its MIME type.

    mimetypes.guess_type does not know the Office XML types on every platform, so
    the formats this application actually produces are mapped explicitly.
    """
    lowered = filename.lower()
    if lowered.endswith(".pdf"):
        return "application", "pdf"
    if lowered.endswith(".xlsx"):
        return (
            "application",
            "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    if lowered.endswith(".docx"):
        return (
            "application",
            "vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    if lowered.endswith(".csv"):
        return "text", "csv"
    if lowered.endswith(".html"):
        return "text", "html"
    if lowered.endswith(".json"):
        return "application", "json"
    return "application", "octet-stream"
