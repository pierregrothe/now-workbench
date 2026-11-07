"""Otto agent tools for demonstration media captures (screenshots and videos)."""

from typing import Any

from now_workbench.domains.capture import PlaywrightCaptureEngine
from now_workbench.interfaces.ai.tools.base import (
    BUNDLE_ARG,
    ToolContext,
    ToolResult,
    ToolSpec,
    media_tile,
    register,
    table_tile,
    text_tile,
)
from now_workbench.interfaces.ai.tools.bundles import bundle_access
from now_workbench.platform.config.settings import settings


def _list_demo_captures(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    engine = PlaywrightCaptureEngine(bundles_dir=bundle_access(ctx.conn, bundle_id).root)
    captures = engine.list_captures(bundle_id)
    if not captures:
        return ToolResult(
            summary=f"No media captures recorded for bundle '{bundle_id}'.",
            tiles=[
                text_tile(
                    f"tile-caps-{bundle_id}",
                    "Captures",
                    f"No screenshots or videos recorded for '{bundle_id}'.",
                )
            ],
        )
    columns = ["Filename", "Type", "Label", "URL"]
    rows = [[c.filename, c.media_type.upper(), c.label or "-", c.url] for c in captures]
    tile = table_tile(f"tile-caps-{bundle_id}", f"Media Captures: {bundle_id}", columns, rows)
    tiles = [tile]
    latest = captures[0]
    tiles.append(
        media_tile(
            f"tile-preview-{latest.id}",
            f"Latest {latest.media_type.title()}: {bundle_id}",
            latest.url,
            media_type=latest.media_type,
            label=f"{latest.label} ({latest.created_at[:16].replace('T', ' ')} UTC)",
            actions=[
                {"id": "inspect", "label": "Artifact Library", "variant": "secondary"},
            ],
        )
    )
    sum_text = (
        f"Found {len(captures)} media capture(s) for '{bundle_id}'. Latest: {latest.filename}"
    )
    return ToolResult(
        summary=sum_text,
        data={"captures": [c.model_dump() for c in captures]},
        tiles=tiles,
    )


def _update_demo_capture(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    filename = str(args["filename"])
    label = str(args["label"])
    bundle_access(ctx.conn, bundle_id, write=True)
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    updated = engine.update_capture(bundle_id, filename, label=label)
    return ToolResult(
        summary=f"Updated capture '{filename}' label to: '{updated.label}'.",
        data=updated.model_dump(),
        tiles=[
            text_tile(
                f"tile-cap-up-{filename}",
                "Capture Updated",
                f"{filename}\nLabel: {updated.label}\nType: {updated.media_type.upper()}",
            )
        ],
    )


def _plan_delete_demo_capture(ctx: ToolContext, args: dict[str, Any]) -> str:
    return (
        f"Permanently delete media capture '{args.get('filename')}' "
        f"from bundle '{args.get('bundle_id')}'."
    )


def _delete_demo_capture(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    filename = str(args["filename"])
    bundle_access(ctx.conn, bundle_id, write=True)
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    engine.delete_capture(bundle_id, filename)
    remaining = engine.list_captures(bundle_id)
    return ToolResult(
        summary=(
            f"Deleted capture '{filename}' from bundle '{bundle_id}'. "
            f"{len(remaining)} capture(s) remain."
        ),
        data={"remaining": len(remaining)},
        tiles=[
            text_tile(
                f"tile-cap-del-{filename}",
                "Capture Deleted",
                f"'{filename}' was permanently deleted from '{bundle_id}'.",
            )
        ],
    )


register(
    ToolSpec(
        name="list_demo_captures",
        description="List all screenshots and videos captured for a demonstration bundle.",
        properties={"bundle_id": BUNDLE_ARG},
        required=["bundle_id"],
        handler=_list_demo_captures,
        category="bundle",
        cli_equivalent="demo list-captures",
    )
)
register(
    ToolSpec(
        name="update_demo_capture",
        description="Update label or caption of a screenshot or video artifact.",
        properties={
            "bundle_id": BUNDLE_ARG,
            "filename": {"type": "string"},
            "label": {"type": "string"},
        },
        required=["bundle_id", "filename", "label"],
        handler=_update_demo_capture,
        category="bundle",
        cli_equivalent="demo update-capture",
    )
)
register(
    ToolSpec(
        name="delete_demo_capture",
        description="Permanently delete a screenshot or video capture artifact file.",
        properties={
            "bundle_id": BUNDLE_ARG,
            "filename": {"type": "string"},
        },
        required=["bundle_id", "filename"],
        handler=_delete_demo_capture,
        plan=_plan_delete_demo_capture,
        destructive=True,
        category="bundle",
        cli_equivalent="demo delete-capture",
    )
)
