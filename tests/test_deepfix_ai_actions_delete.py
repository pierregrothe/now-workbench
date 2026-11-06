# tests/test_deepfix_ai_actions_delete.py
# Regression tests: chat delete path is whole-word, targeted and never destructive
# Author: Pierre Grothe
# Date: 2026-11-06

from now_workbench.ai.actions import execute_autonomous_action
from now_workbench.db import DatabaseRepository, InstanceCreate, db_session


def _seed(repo: DatabaseRepository) -> None:
    repo.add_instance(
        InstanceCreate(id="inst-a", name="Alpha", url="fake://alpha.example.com", is_default=True)
    )
    repo.add_instance(InstanceCreate(id="inst-b", name="Failover Box", url="fake://b.example.com"))
    repo.add_instance(InstanceCreate(id="inst-c", name="Gamma", url="fake://c.example.com"))


def test_execute_autonomous_action_delete_never_deletes() -> None:
    """Delete requests list targets and delete nothing."""
    with db_session() as repo:
        _seed(repo)
        before = len(repo.list_instances())
        resp = execute_autonomous_action("delete the unauthenticated instances", repo)
        assert resp is not None
        assert "Nothing was deleted" in resp.summary
        assert "Admin panel" in resp.summary
        assert len(repo.list_instances()) == before


def test_execute_autonomous_action_delete_named_instance_targets_only_it() -> None:
    """A named instance is the only target even if a filter word is present."""
    with db_session() as repo:
        _seed(repo)
        before = len(repo.list_instances())
        resp = execute_autonomous_action("delete my failover box instance", repo)
        assert resp is not None
        assert "1 instance(s) match: Failover Box" in resp.summary
        assert len(repo.list_instances()) == before


def test_execute_autonomous_action_delete_substring_word_does_not_match() -> None:
    """'badge' must not trigger the 'bad' status filter."""
    with db_session() as repo:
        _seed(repo)
        before = len(repo.list_instances())
        resp = execute_autonomous_action("remove the badge instance", repo)
        assert resp is not None
        assert "No matching" in resp.summary
        assert len(repo.list_instances()) == before
