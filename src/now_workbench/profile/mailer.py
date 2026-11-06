# src/now_workbench/profile/mailer.py
# Mail delivery for verification codes: SMTP in production, in-memory fake for tests.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Mailers that deliver the verification code."""

import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

from now_workbench.profile.models import MailSettings

__all__ = ["InMemoryMailer", "MailError", "Mailer", "SentMail", "SmtpMailer"]

_TIMEOUT_SECONDS = 10.0


class MailError(Exception):
    """The message could not be delivered."""


class Mailer(Protocol):
    """Anything that can send a plain-text email."""

    def send(self, to: str, subject: str, body: str) -> None:
        """Deliver one message.

        Raises:
            MailError: Delivery failed.
        """
        ...


@dataclass(frozen=True)
class SentMail:
    """A message captured by the in-memory mailer."""

    to: str
    subject: str
    body: str


@dataclass
class InMemoryMailer:
    """Test double that records messages instead of sending them (no network)."""

    sent: list[SentMail] = field(default_factory=list)
    fail_with: str | None = None

    def send(self, to: str, subject: str, body: str) -> None:
        """Record the message, or fail when ``fail_with`` is set."""
        if self.fail_with:
            raise MailError(self.fail_with)
        self.sent.append(SentMail(to, subject, body))


class SmtpMailer:
    """Sends mail through the SMTP server configured in Settings."""

    def __init__(self, settings: MailSettings, password: str) -> None:
        self._settings = settings
        self._password = password

    def send(self, to: str, subject: str, body: str) -> None:
        """Send over SMTP (implicit TLS on 465, STARTTLS otherwise when enabled)."""
        cfg = self._settings
        message = EmailMessage()
        message["From"] = cfg.from_address
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        context = ssl.create_default_context()
        try:
            if cfg.port == 465:
                server: smtplib.SMTP = smtplib.SMTP_SSL(
                    cfg.host, cfg.port, timeout=_TIMEOUT_SECONDS, context=context
                )
            else:
                server = smtplib.SMTP(cfg.host, cfg.port, timeout=_TIMEOUT_SECONDS)
            with server:
                if cfg.port != 465 and cfg.starttls:
                    server.starttls(context=context)
                if cfg.username:
                    server.login(cfg.username, self._password)
                server.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise MailError(f"Could not send the email: {exc}") from exc
