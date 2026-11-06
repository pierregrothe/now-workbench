# src/now_workbench/auth/roles.py
# Map a verified email to roles from configuration.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Role assignment: Cloudflare proves who the person is; these lists say what they may do."""

from now_workbench.auth.models import Role

__all__ = ["parse_emails", "roles_for"]


def parse_emails(raw: str) -> frozenset[str]:
    """Split a comma or whitespace separated list of emails into a lower-case set."""
    return frozenset(part.strip().lower() for part in raw.replace(",", " ").split() if part.strip())


def roles_for(email: str, admin_emails: str, consultant_emails: str) -> frozenset[Role]:
    """Return the roles configured for an email (empty when it is on neither list).

    An address may be on both lists, which grants both roles.
    """
    address = email.strip().lower()
    roles: set[Role] = set()
    if address in parse_emails(admin_emails):
        roles.add(Role.ADMIN)
    if address in parse_emails(consultant_emails):
        roles.add(Role.SOLUTION_CONSULTANT)
    return frozenset(roles)
