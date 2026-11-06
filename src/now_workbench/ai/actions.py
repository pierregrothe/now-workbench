"""Autonomous action execution engine for Otto Copilot."""

import re
from typing import Any, Literal

from now_workbench.ai.tiles import (
    GenerativeUIResponse,
    UITileSpec,
    build_instance_response,
)
from now_workbench.bundles.manager import BundleManager
from now_workbench.config.settings import settings
from now_workbench.connectivity import check_and_record_instance
from now_workbench.db import (
    DatabaseRepository,
    InstanceCreate,
    InstanceRecord,
)
from now_workbench.db.models import WorkbenchPreferencesUpdate

_DELETE_VERBS = ("delete", "remove", "clean", "purge", "prune", "drop", "clear")
_UNAUTH_FILTERS = (
    "unauthenticated",
    "unauth",
    "unreachable",
    "failed",
    "fail",
    "broken",
    "offline",
    "invalid",
    "bad",
    "unverified",
    "inactive",
    "refused",
)
_VERIFY_VERBS = (
    "check auth",
    "test auth",
    "verify auth",
    "check connectivity",
    "test connectivity",
    "verify connectivity",
    "test instance",
    "test all",
    "check instance",
    "verify instance",
    "ping instance",
    "retest",
)


def _records_to_dicts(instances: list[InstanceRecord]) -> list[dict[str, Any]]:
    """Convert InstanceRecord models to dictionaries for tile builders."""
    return [
        {
            "id": inst.id,
            "name": inst.name,
            "url": inst.url,
            "release": inst.release,
            "status": inst.status,
            "is_default": inst.is_default,
        }
        for inst in instances
    ]


def _has_word(text: str, term: str) -> bool:
    """Return True when ``term`` appears in ``text`` delimited by non-word characters."""
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def _select_instances_to_delete(
    lower: str,
    instances: list[InstanceRecord],
) -> list[InstanceRecord]:
    """Identify which instances match the user's deletion criteria.

    A specifically named instance always wins and never falls through to the
    broad status filters. Keyword matching is whole-word only.
    """
    named = [
        i for i in instances if any(_has_word(lower, t.lower()) for t in (i.id, i.name, i.url) if t)
    ]
    if named:
        return named
    if any(_has_word(lower, tok) for tok in _UNAUTH_FILTERS):
        return [i for i in instances if i.status != "authenticated"]
    if _has_word(lower, "non-default") or _has_word(lower, "secondary"):
        return [i for i in instances if not i.is_default]
    return []


def _try_delete_instances_action(
    lower: str,
    repo: DatabaseRepository,
) -> GenerativeUIResponse | None:
    """Preview instance deletion; never deletes from free-text chat.

    Deleting is destructive, so the chat path only lists the instances that
    would be removed and directs the user to confirm in the Admin panel.
    """
    if not any(_has_word(lower, v) for v in _DELETE_VERBS):
        return None

    instances = repo.list_instances()
    targets = _select_instances_to_delete(lower, instances)

    has_inst_noun = any(
        _has_word(lower, n)
        for n in ("instance", "instances", "instande", "instence", "target", "targets")
    ) or any(_has_word(lower, tok) for tok in _UNAUTH_FILTERS)
    if not (has_inst_noun or targets):
        return None

    base = build_instance_response(_records_to_dicts(instances), detail_level="summary")
    if not targets:
        summary = (
            "No matching unauthenticated or removable instances were found. "
            f"You currently manage {len(instances)} instance(s)."
        )
    else:
        names = ", ".join(t.name for t in targets)
        summary = (
            f"Nothing was deleted. {len(targets)} instance(s) match: {names}. "
            "Deleting instances is destructive; confirm and delete them in the Admin panel."
        )
    return GenerativeUIResponse(summary=summary, layout=base.layout, tiles=base.tiles)


def _try_verify_instances_action(
    lower: str,
    repo: DatabaseRepository,
) -> GenerativeUIResponse | None:
    """Execute live authentication verification across all managed instances."""
    if not any(phrase in lower for phrase in _VERIFY_VERBS):
        return None

    instances = repo.list_instances()
    prefs = repo.get_workbench_preferences()
    for inst in instances:
        check_and_record_instance(repo, inst, timeout=3.0, fake_mode=prefs.sdk_fake_mode)

    updated = repo.list_instances()
    detail_mode: Literal["summary", "detailed"] = (
        "detailed" if "detail" in lower or "list" in lower else "summary"
    )
    base_resp = build_instance_response(_records_to_dicts(updated), detail_level=detail_mode)
    auth_ok = sum(1 for i in updated if i.status == "authenticated")
    fail_cnt = len(updated) - auth_ok
    return GenerativeUIResponse(
        summary=(
            f"Checked live authentication across {len(updated)} instance(s): "
            f"{auth_ok} Authenticated, {fail_cnt} Unauthenticated/Unreachable."
        ),
        layout=base_resp.layout,
        tiles=base_resp.tiles,
    )


def _try_switch_default_instance_action(
    lower: str,
    repo: DatabaseRepository,
) -> GenerativeUIResponse | None:
    """Switch the primary default ServiceNow instance by name or ID."""
    is_switch = any(
        p in lower
        for p in ("set default", "make default", "set primary", "make primary", "switch to")
    )
    if not is_switch:
        return None

    instances = repo.list_instances()
    matched = next(
        (
            i
            for i in instances
            if i.id.lower() in lower or i.name.lower() in lower or i.url.lower() in lower
        ),
        None,
    )
    if not matched:
        return None

    repo.set_default_instance(matched.id)
    updated = repo.list_instances()
    base_resp = build_instance_response(_records_to_dicts(updated), detail_level="summary")
    return GenerativeUIResponse(
        summary=f"Switched primary default target to '{matched.name}' ({matched.url}).",
        layout=base_resp.layout,
        tiles=base_resp.tiles,
    )


def _try_add_instance_action(
    lower: str,
    raw_query: str,
    repo: DatabaseRepository,
) -> GenerativeUIResponse | None:
    """Register a new ServiceNow instance when the user provides a URL in chat."""
    if not any(p in lower for p in ("add instance", "register instance", "create instance")):
        return None
    url_match = re.search(r"(https?://[^\s,]+|fake://[^\s,]+)", raw_query)
    if not url_match:
        return None

    target_url = url_match.group(1).rstrip("/")
    host_slug = target_url.split("://")[-1].split(".")[0].split("/")[0]
    created = repo.add_instance(
        InstanceCreate(
            name=f"ServiceNow ({host_slug})",
            url=target_url,
            username="admin",
            is_default=len(repo.list_instances()) == 0,
        )
    )
    prefs = repo.get_workbench_preferences()
    status, _, _ = check_and_record_instance(
        repo, created, timeout=3.0, fake_mode=prefs.sdk_fake_mode
    )

    updated = repo.list_instances()
    base_resp = build_instance_response(_records_to_dicts(updated), detail_level="summary")
    return GenerativeUIResponse(
        summary=f"Registered instance '{created.name}' ({target_url}) with status '{status}'.",
        layout=base_resp.layout,
        tiles=base_resp.tiles,
    )


def _try_delete_bundle_action(lower: str) -> GenerativeUIResponse | None:
    """Delete a non-core demo bundle when requested in chat."""
    has_del = any(v in lower for v in _DELETE_VERBS)
    has_bundle = any(b in lower for b in ("bundle", "demo", "artifact", "recipe"))
    if not (has_del and has_bundle):
        return None

    manager = BundleManager(settings.get_bundles_dir())
    bundles = manager.list_bundles()
    target = next(
        (b for b in bundles if b.manifest.id.lower() in lower or b.manifest.name.lower() in lower),
        None,
    )
    if not target or target.manifest.id == "sample-ai-assistant":
        return None

    manager.delete_bundle(target.manifest.id)
    remaining = manager.list_bundles()
    tile = UITileSpec(
        id="tile-bundle-deleted",
        type="instance-kpi",
        title="Demo Recipe Deleted",
        props={
            "count": len(remaining),
            "label": "Remaining Demo Recipes",
            "subtitle": f"Deleted '{target.manifest.name}' ({target.manifest.id})",
            "status": "Catalog Updated",
            "badge": "Action Executed",
            "accent": "green",
            "actions": [
                {"id": "show_bundles", "label": "Show Recipe Details", "variant": "primary"},
                {"id": "inspect", "label": "Open Artifact Library", "variant": "secondary"},
            ],
        },
    )
    return GenerativeUIResponse(
        summary=(
            f"Deleted demo bundle '{target.manifest.name}'. "
            f"{len(remaining)} recipe bundle(s) remain in the library."
        ),
        layout="1-col",
        tiles=[tile],
    )


def _try_update_preferences_action(
    lower: str,
    repo: DatabaseRepository,
) -> GenerativeUIResponse | None:
    """Update theme or simulation mode when requested in chat."""
    if "dark mode" in lower or "dark theme" in lower:
        repo.update_workbench_preferences(WorkbenchPreferencesUpdate(theme_mode="dark"))
        mode_msg = "Switched Workbench theme preference to Dark Mode."
    elif "light mode" in lower or "light theme" in lower:
        repo.update_workbench_preferences(WorkbenchPreferencesUpdate(theme_mode="light"))
        mode_msg = "Switched Workbench theme preference to Light Mode."
    else:
        return None

    tile = UITileSpec(
        id="tile-prefs-updated",
        type="rich-text",
        title="Workbench Preference Updated",
        props={
            "body": f"{mode_msg} Your preference has been saved to SQLite.",
            "actions": [
                {"id": "manage", "label": "Open Workbench Settings", "variant": "secondary"},
            ],
        },
    )
    return GenerativeUIResponse(
        summary=mode_msg,
        layout="1-col",
        tiles=[tile],
    )


def execute_autonomous_action(
    query: str,
    repo: DatabaseRepository,
) -> GenerativeUIResponse | None:
    """Detect and autonomously execute user action requests in conversation."""
    lower = query.lower().strip()

    for res in (
        _try_delete_instances_action(lower, repo),
        _try_verify_instances_action(lower, repo),
        _try_switch_default_instance_action(lower, repo),
        _try_add_instance_action(lower, query, repo),
        _try_delete_bundle_action(lower),
        _try_update_preferences_action(lower, repo),
    ):
        if res is not None:
            return res

    return None
