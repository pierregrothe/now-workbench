# src/now_workbench/interfaces/ai/tools/sharing.py
# Otto's sharing tools: groups, membership, versions, shares and the approval inbox.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Sharing tools (ADR-018, ADR-025).

Every tool calls the sharing service as the signed-in person, so Otto is held to exactly the
rules of the Groups, Approvals and Share screens. Changes that remove access or decide for
others ask for confirmation first.
"""

from typing import Any

from now_workbench.domains import sharing
from now_workbench.domains.groups import Group, GroupKind, MemberRole
from now_workbench.domains.sharing import ShareTarget
from now_workbench.interfaces.ai.tools.base import (
    BUNDLE_ARG,
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    table_tile,
)
from now_workbench.platform.errors import InvalidInputError

__all__: list[str] = []

_GROUP = {"type": "string", "description": "Group name or id"}
_EMAIL = {"type": "string", "description": "Email address of a team member"}


def _find_group(ctx: ToolContext, ref: str) -> Group:
    """Resolve a group by id or (case-insensitive) name among those the person can see."""
    groups = sharing.list_groups(ctx.conn, ctx.actor())
    wanted = ref.strip().lower()
    for g in groups:
        if g.id == ref or g.name.lower() == wanted:
            return g
    matches = [g for g in groups if wanted in g.name.lower()]
    if len(matches) == 1:
        return matches[0]
    names = ", ".join(g.name for g in matches) or "none"
    raise InvalidInputError(f"No single group matches '{ref}' (candidates: {names}).")


def _groups_tile(groups: list[Group]) -> Any:
    rows = [
        [g.name, g.kind.value, g.member_count, g.my_role.value if g.my_role else "--"]
        for g in groups
    ]
    return table_tile("tile-groups", "Groups", ["Group", "Kind", "Members", "Your role"], rows)


# --- groups ------------------------------------------------------------------------------


def _list_groups(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    groups = sharing.list_groups(ctx.conn, ctx.actor())
    return ToolResult(
        summary=f"{len(groups)} group(s).",
        data={"groups": [g.model_dump() for g in groups]},
        tiles=[_groups_tile(groups)],
    )


def _create_group(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    group = sharing.create_group(
        ctx.conn,
        ctx.actor(),
        str(args["name"]),
        GroupKind(args["kind"]),
        str(args.get("description") or ""),
    )
    return ToolResult(summary=f"Created group '{group.name}'.", data=group.model_dump())


def _delete_group(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    group = _find_group(ctx, str(args["group"]))
    sharing.delete_group(ctx.conn, ctx.actor(), group.id)
    return ToolResult(summary=f"Deleted group '{group.name}' with its memberships and shares.")


def _join_group(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    group = sharing.join_group(ctx.conn, ctx.actor(), _find_group(ctx, str(args["group"])).id)
    status = group.my_status.value if group.my_status else "requested"
    return ToolResult(summary=f"Asked to join '{group.name}' (status: {status}).")


def _list_members(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    group = _find_group(ctx, str(args["group"]))
    members = sharing.list_group_members(ctx.conn, ctx.actor(), group.id)
    rows = [[m.email, m.role.value, m.status.value] for m in members]
    return ToolResult(
        summary=f"'{group.name}' has {len(members)} member(s) or request(s).",
        data={"members": [m.model_dump() for m in members]},
        tiles=[
            table_tile("tile-members", f"{group.name}: members", ["Email", "Role", "Status"], rows)
        ],
    )


def _put_member(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    group = _find_group(ctx, str(args["group"]))
    role = MemberRole(args.get("role") or MemberRole.MEMBER.value)
    sharing.put_group_member(ctx.conn, ctx.actor(), group.id, str(args["email"]), role)
    return ToolResult(summary=f"{args['email']} is now a {role.value} of '{group.name}'.")


def _remove_member(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    group = _find_group(ctx, str(args["group"]))
    sharing.remove_group_member(ctx.conn, ctx.actor(), group.id, str(args["email"]))
    return ToolResult(summary=f"Removed {args['email']} from '{group.name}'.")


# --- versions and shares -------------------------------------------------------------------


def _list_versions(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    versions = sharing.list_versions(ctx.conn, ctx.actor(), str(args["bundle_id"]))
    rows = [[v.version, v.note or "--", v.created_by, v.created_at[:19]] for v in versions]
    return ToolResult(
        summary=f"{len(versions)} saved version(s).",
        data={"versions": [v.model_dump() for v in versions]},
        tiles=[table_tile("tile-versions", "Versions", ["Version", "Note", "By", "When"], rows)],
    )


def _save_version(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    v = sharing.save_new_version(
        ctx.conn, ctx.actor(), str(args["bundle_id"]), str(args.get("note") or "")
    )
    return ToolResult(summary=f"Saved version {v.version} of '{v.name}'.", data=v.model_dump())


def _list_shares(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    shares = sharing.list_shares(ctx.conn, ctx.actor(), str(args["bundle_id"]))
    rows = [[s.target.value, s.group_name or "everyone", s.version, s.status.value] for s in shares]
    return ToolResult(
        summary=f"{len(shares)} share(s).",
        data={"shares": [s.model_dump() for s in shares]},
        tiles=[table_tile("tile-shares", "Shares", ["Target", "With", "Version", "Status"], rows)],
    )


def _share_bundle(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    target = ShareTarget(args["target"])
    group_id = _find_group(ctx, str(args["group"])).id if args.get("group") else None
    share = sharing.request_share(ctx.conn, ctx.actor(), str(args["bundle_id"]), target, group_id)
    who = share.group_name or "everyone"
    return ToolResult(
        summary=f"Version {share.version} shared with {who}: {share.status.value}.",
        data=share.model_dump(),
    )


def _withdraw_share(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    sharing.withdraw_share(ctx.conn, ctx.actor(), str(args["bundle_id"]), str(args["share_id"]))
    return ToolResult(summary="Share withdrawn.")


# --- approvals -----------------------------------------------------------------------------


def _approval_inbox(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    inbox = sharing.approval_inbox(ctx.conn, ctx.actor())
    share_rows = [
        [s.id, s.artifact_name or s.artifact_id, s.version, s.group_name or "everyone"]
        for s in inbox.shares
    ]
    join_rows = [
        [inbox.group_names.get(j.group_id, j.group_id), j.email] for j in inbox.join_requests
    ]
    tiles = [
        table_tile(
            "tile-pending-shares",
            "Shares to approve",
            ["Id", "Bundle", "Version", "With"],
            share_rows,
        ),
        table_tile("tile-join-requests", "Join requests", ["Group", "Email"], join_rows),
    ]
    return ToolResult(
        summary=(
            f"{len(inbox.shares)} share(s) and {len(inbox.join_requests)} join request(s) "
            "wait for you."
        ),
        data=inbox.model_dump(),
        tiles=tiles,
        layout="2-col",
    )


def _decide_share(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    approve = bool(args["approve"])
    share = sharing.decide_share(ctx.conn, ctx.actor(), str(args["share_id"]), approve)
    return ToolResult(
        summary=f"Share {share.id} is now {share.status.value}.", data=share.model_dump()
    )


register(
    ToolSpec(
        name="list_groups",
        description="List groups and your standing in each.",
        handler=_list_groups,
        properties={},
        category="sharing",
    )
)
register(
    ToolSpec(
        name="create_group",
        description="Create a group (administrators). Kind: region, territory or business_unit.",
        handler=_create_group,
        properties={
            "name": {"type": "string"},
            "kind": {"type": "string", "enum": [k.value for k in GroupKind]},
            "description": {"type": "string"},
        },
        required=["name", "kind"],
        admin_only=True,
        category="sharing",
    )
)
register(
    ToolSpec(
        name="delete_group",
        description="Delete a group with its memberships and shares (administrators).",
        handler=_delete_group,
        properties={"group": _GROUP},
        required=["group"],
        admin_only=True,
        category="sharing",
        destructive=True,
        plan=lambda ctx, a: f"Delete group '{a.get('group')}' and everything shared with it.",
    )
)
register(
    ToolSpec(
        name="join_group",
        description="Ask to join a group.",
        handler=_join_group,
        properties={"group": _GROUP},
        required=["group"],
        category="sharing",
    )
)
register(
    ToolSpec(
        name="list_group_members",
        description="List a group's members and pending join requests (group administrators).",
        handler=_list_members,
        properties={"group": _GROUP},
        required=["group"],
        category="sharing",
    )
)
register(
    ToolSpec(
        name="set_group_member",
        description=(
            "Accept a join request or add a team member to a group; role member or admin "
            "(only administrators appoint group admins)."
        ),
        handler=_put_member,
        properties={
            "group": _GROUP,
            "email": _EMAIL,
            "role": {"type": "string", "enum": [r.value for r in MemberRole]},
        },
        required=["group", "email"],
        category="sharing",
        destructive=True,
        plan=lambda ctx, a: (
            f"Make {a.get('email')} a {a.get('role') or 'member'} of '{a.get('group')}'."
        ),
    )
)
register(
    ToolSpec(
        name="remove_group_member",
        description="Remove someone from a group, decline a request, or leave a group.",
        handler=_remove_member,
        properties={"group": _GROUP, "email": _EMAIL},
        required=["group", "email"],
        category="sharing",
        destructive=True,
        plan=lambda ctx, a: f"Remove {a.get('email')} from '{a.get('group')}'.",
    )
)
register(
    ToolSpec(
        name="list_versions",
        description="List a bundle's saved versions (owner).",
        handler=_list_versions,
        properties={"bundle_id": BUNDLE_ARG},
        required=["bundle_id"],
        category="sharing",
    )
)
register(
    ToolSpec(
        name="save_version",
        description="Freeze a bundle you own as its next version (needed before sharing).",
        handler=_save_version,
        properties={"bundle_id": BUNDLE_ARG, "note": {"type": "string"}},
        required=["bundle_id"],
        category="sharing",
    )
)
register(
    ToolSpec(
        name="list_shares",
        description="List who a bundle you own is shared with.",
        handler=_list_shares,
        properties={"bundle_id": BUNDLE_ARG},
        required=["bundle_id"],
        category="sharing",
    )
)
register(
    ToolSpec(
        name="share_bundle",
        description=(
            "Share a bundle's newest version with one of your groups or with everyone; it "
            "waits for approval unless you approve that target yourself."
        ),
        handler=_share_bundle,
        properties={
            "bundle_id": BUNDLE_ARG,
            "target": {"type": "string", "enum": [t.value for t in ShareTarget]},
            "group": _GROUP,
        },
        required=["bundle_id", "target"],
        category="sharing",
    )
)
register(
    ToolSpec(
        name="withdraw_share",
        description="Stop sharing a bundle (or withdraw a pending request).",
        handler=_withdraw_share,
        properties={"bundle_id": BUNDLE_ARG, "share_id": {"type": "string"}},
        required=["bundle_id", "share_id"],
        category="sharing",
        destructive=True,
        plan=lambda ctx, a: f"Stop sharing '{a.get('bundle_id')}' (share {a.get('share_id')}).",
    )
)
register(
    ToolSpec(
        name="approval_inbox",
        description="List shares and join requests waiting for your decision.",
        handler=_approval_inbox,
        properties={},
        category="sharing",
    )
)
register(
    ToolSpec(
        name="decide_share",
        description="Approve or reject a pending share you may decide.",
        handler=_decide_share,
        properties={"share_id": {"type": "string"}, "approve": {"type": "boolean"}},
        required=["share_id", "approve"],
        category="sharing",
        destructive=True,
        plan=lambda ctx, a: (
            f"{('Approve' if a.get('approve') else 'Reject')} share {a.get('share_id')}."
        ),
    )
)
