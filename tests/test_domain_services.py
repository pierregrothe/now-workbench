# tests/test_domain_services.py
# Domain services refuse on their own, whichever front door (API or Otto) calls them.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for the rules held by domain services (ADR-025)."""

import pytest

from now_workbench.domains import identity
from now_workbench.domains.identity import AuthUser, Role
from now_workbench.platform.db.session import db_session
from now_workbench.platform.errors import ForbiddenError

CONSULTANT = AuthUser(
    email="ana@example.com", roles=frozenset({Role.SOLUTION_CONSULTANT}), mode="cloudflare"
)


def test_list_team_refuses_a_non_administrator() -> None:
    """The team service checks the role itself, not only the API route."""
    with db_session() as conn, pytest.raises(ForbiddenError, match="Only administrators"):
        identity.list_team(conn, CONSULTANT)
