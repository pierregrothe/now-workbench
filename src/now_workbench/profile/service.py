# src/now_workbench/profile/service.py
# Send and confirm the one-time email code that approves the profile.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Verification workflow: send a code to the profile's servicenow.com address, confirm it."""

from datetime import UTC, datetime

from now_workbench.db import DatabaseRepository
from now_workbench.profile.mailer import Mailer
from now_workbench.profile.models import SERVICENOW_EMAIL_PATTERN
from now_workbench.profile.verification import (
    CODE_TTL,
    MAX_ATTEMPTS,
    RESEND_COOLDOWN,
    code_matches,
    format_code,
    hash_code,
    new_code,
    new_salt,
)

__all__ = [
    "CodeExpiredError",
    "CooldownError",
    "MailNotConfiguredError",
    "NoEmailError",
    "NoPendingCodeError",
    "TooManyAttemptsError",
    "VerificationError",
    "WrongCodeError",
    "confirm_code",
    "send_code",
]


class VerificationError(Exception):
    """Base class for verification workflow failures."""


class NoEmailError(VerificationError):
    """The profile has no servicenow.com email to verify."""


class MailNotConfiguredError(VerificationError):
    """Email delivery is not configured in Settings."""


class CooldownError(VerificationError):
    """A code was sent too recently."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Wait {retry_after} seconds before requesting another code.")
        self.retry_after = retry_after


class NoPendingCodeError(VerificationError):
    """There is no code waiting to be confirmed."""


class CodeExpiredError(VerificationError):
    """The code is older than its validity window."""


class TooManyAttemptsError(VerificationError):
    """Too many wrong codes; a new one must be requested."""


class WrongCodeError(VerificationError):
    """The entered code does not match."""

    def __init__(self, remaining: int) -> None:
        super().__init__(f"That code is not correct. {remaining} attempt(s) left.")
        self.remaining = remaining


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def send_code(repo: DatabaseRepository, mailer: Mailer, now: datetime | None = None) -> str:
    """Email a new one-time code to the profile's servicenow.com address.

    Args:
        repo: Open repository.
        mailer: Delivery channel.
        now: Current time (UTC); injectable for tests.

    Returns:
        The address the code was sent to.

    Raises:
        NoEmailError: No valid servicenow.com address on the profile.
        MailNotConfiguredError: Email delivery is not configured.
        CooldownError: A code was sent less than a minute ago.
        MailError: The message could not be delivered (no code is stored in that case).
    """
    moment = now or datetime.now(UTC)
    profile = repo.get_profile()
    if not SERVICENOW_EMAIL_PATTERN.match(profile.email):
        raise NoEmailError("Save your servicenow.com email address first.")
    if not repo.get_mail_settings().configured:
        raise MailNotConfiguredError("Email delivery is not configured. Add SMTP settings first.")
    if profile.code_sent_at:
        elapsed = moment - datetime.fromisoformat(profile.code_sent_at)
        if elapsed < RESEND_COOLDOWN:
            raise CooldownError(int((RESEND_COOLDOWN - elapsed).total_seconds()) + 1)

    code = new_code()
    minutes = int(CODE_TTL.total_seconds() // 60)
    body = (
        f"Your now-workbench approval code is {format_code(code)}.\n\n"
        f"It is valid for {minutes} minutes. If you did not ask for it, ignore this message."
    )
    mailer.send(profile.email, "now-workbench approval code", body)
    salt = new_salt()
    repo.store_verification_code(hash_code(code, salt), salt, _iso(moment + CODE_TTL), _iso(moment))
    return profile.email


def confirm_code(repo: DatabaseRepository, entered: str, now: datetime | None = None) -> None:
    """Approve the profile when the entered code matches the pending one.

    Raises:
        NoPendingCodeError: No code was requested.
        CodeExpiredError: The code expired (it is discarded).
        TooManyAttemptsError: Too many wrong attempts (the code is discarded).
        WrongCodeError: The code does not match.
    """
    moment = now or datetime.now(UTC)
    profile = repo.get_profile()
    if not (profile.code_hash and profile.code_salt and profile.code_expires_at):
        raise NoPendingCodeError("Request a code first.")
    if moment > datetime.fromisoformat(profile.code_expires_at):
        repo.clear_verification_code()
        raise CodeExpiredError("That code has expired. Request a new one.")
    if code_matches(entered, profile.code_hash, profile.code_salt):
        repo.mark_email_verified(_iso(moment))
        return
    attempts = repo.record_failed_attempt()
    if attempts >= MAX_ATTEMPTS:
        repo.clear_verification_code()
        raise TooManyAttemptsError("Too many wrong codes. Request a new one.")
    raise WrongCodeError(MAX_ATTEMPTS - attempts)
