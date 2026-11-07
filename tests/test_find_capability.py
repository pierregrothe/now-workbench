# tests/test_find_capability.py
# Capability search: the index, the lexical ranking and the Jev-backed semantic pass (STORY-071).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for ADR-033's find_capability.py; Jev is replaced by httpx.MockTransport (never called)."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "find_capability", ROOT / "scripts/dev-tools/find_capability.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["find_capability"] = module
    spec.loader.exec_module(module)
    return module


fc = _load()


@pytest.fixture
def src(tmp_path: Path) -> Path:
    """A miniature `src/now_workbench` with one domain exporting two names."""
    domain = tmp_path / "src" / "now_workbench" / "domains" / "widgets"
    domain.mkdir(parents=True)
    (domain / "__init__.py").write_text(
        '__all__ = ["make_widget", "WidgetRepository"]\n'
        "from now_workbench.domains.widgets.core import make_widget, WidgetRepository\n"
    )
    (domain / "core.py").write_text(
        '"""Widgets."""\n'
        "def make_widget(spec):\n"
        '    """Build a widget from its spec, validating every field first."""\n'
        "class WidgetRepository:\n"
        '    """Store and list widgets owned by the current person."""\n'
        "def count_gadgets():\n"
        '    """Count gadgets."""\n'
        "def _private_helper():\n"
        '    """Never indexed."""\n'
    )
    return tmp_path / "src" / "now_workbench"


def test_words_split_names_fold_plurals_and_drop_stop_words() -> None:
    assert fc.words("WidgetRepository list_widgets for the Categories") == [
        "widget",
        "repository",
        "list",
        "widget",
        "category",
    ]
    assert fc.words("class address") == ["class", "address"]


def test_index_collects_public_symbols_with_their_tier_and_summary(src: Path) -> None:
    field = {c.name: c for c in fc.index(src)}
    assert set(field) == {"make_widget", "WidgetRepository", "count_gadgets"}
    assert field["make_widget"].tier == "export"
    assert field["count_gadgets"].tier == "public"
    assert (
        field["WidgetRepository"].summary == "Store and list widgets owned by the current person."
    )
    assert field["make_widget"].location == "src/now_workbench/domains/widgets/core.py:2"


def test_lexical_search_ranks_name_matches_first_and_drops_non_matches(src: Path) -> None:
    field = fc.index(src)
    ranked = [c.name for _, c in fc.lexical_search("list the widgets someone owns", field)]
    assert ranked == ["WidgetRepository", "make_widget"]
    assert fc.lexical_search("quantum teleport", field) == []


def test_index_covers_the_real_source() -> None:
    field = fc.index()
    names = {c.name for c in field}
    assert {"safe_child", "check_allowance", "db_session"} <= names
    best = fc.lexical_search("encrypt a secret", field, limit=1)
    assert best[0][1].name == "seal_secret"


# --------------------------------------------------------------------------- semantic


def _jev(
    answer: dict[str, float] | None, status: int = 200, seen: list | None = None
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if seen is not None:
            seen.append((request, body))
        if status != 200:
            return httpx.Response(status)
        ids = list(body["questions"])
        values = answer if answer is not None else {}
        return httpx.Response(200, json={"answers": {i: {"noul": values.get(i, 0.1)} for i in ids}})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_semantic_search_ranks_by_probability_and_sends_one_noul_per_candidate(
    src: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TYPESAFE_MODEL", raising=False)
    field = fc.index(src)
    seen: list = []
    results, reason = fc.semantic_search(
        "a store of widgets per user", field, api_key="k", client=_jev({"c1": 0.9}, seen=seen)
    )
    assert reason is None
    assert [c.name for _, c in results][0] == "WidgetRepository"
    [(request, body)] = seen
    assert request.url == fc.ENDPOINT
    assert request.headers["Authorization"] == "Bearer k"
    assert body["model"] == fc.DEFAULT_MODEL
    assert "a store of widgets per user" in body["state"]
    # count_gadgets' summary is too short to judge, so two questions, not three
    assert sorted(body["questions"]) == ["c0", "c1"]
    assert body["questions"]["c1"]["type"] == "noul"
    assert "`WidgetRepository` (export)" in body["questions"]["c1"]["instructions"]


def test_semantic_search_uses_the_model_from_the_environment(
    src: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TYPESAFE_MODEL", "jev-9.9.9")
    seen: list = []
    fc.semantic_search("x", fc.index(src), api_key="k", client=_jev(None, seen=seen))
    assert seen[0][1]["model"] == "jev-9.9.9"


@pytest.mark.parametrize(
    ("api_key", "client_status", "reason"),
    [
        (None, 200, "TYPESAFE_API_KEY is not set"),
        ("k", 401, "a request did not resolve"),
    ],
)
def test_semantic_search_says_why_it_did_not_run(
    src: Path, api_key: str | None, client_status: int, reason: str
) -> None:
    results, why = fc.semantic_search(
        "x", fc.index(src), api_key=api_key, client=_jev(None, status=client_status)
    )
    assert results == []
    assert why is not None and why.startswith(reason)


def test_semantic_search_refuses_a_short_reply(src: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"answers": {"c0": {"noul": 0.9}}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    results, why = fc.semantic_search("x", fc.index(src), api_key="k", client=client)
    assert results == []
    assert why is not None and "short reply" in why


def test_semantic_search_retries_a_busy_service(src: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fc.time, "sleep", lambda _s: None)
    replies = iter([httpx.Response(503), httpx.Response(429)])

    def handler(request: httpx.Request) -> httpx.Response:
        ids = list(json.loads(request.content)["questions"])
        fallback = httpx.Response(200, json={"answers": {i: {"noul": 0.5} for i in ids}})
        return next(replies, fallback)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    results, why = fc.semantic_search("x", fc.index(src), api_key="k", client=client)
    assert why is None
    assert len(results) == 2


def test_semantic_search_needs_candidates_with_a_summary(tmp_path: Path) -> None:
    results, why = fc.semantic_search("x", [], api_key="k", client=_jev(None))
    assert (results, why) == ([], "no capability carries a summary to judge")


def test_main_prints_lexical_and_says_semantic_did_not_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert fc.main(["encrypt", "a", "secret", "--semantic", "--limit", "2"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("[LEXICAL]\n")
    assert "seal_secret" in out
    assert out.rstrip().endswith("[SEMANTIC] not run -- TYPESAFE_API_KEY is not set")


def test_main_shows_nothing_found_plainly(capsys: pytest.CaptureFixture[str]) -> None:
    assert fc.main(["zzqx", "vvplm"]) == 0
    assert capsys.readouterr().out == "[LEXICAL]\n  (nothing)\n"
