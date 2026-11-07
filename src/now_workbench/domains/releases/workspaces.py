"""ServiceNow workspace naming, routing, and version evolution resolver."""

from now_workbench.domains.releases.compatibility import compare_releases, normalize_release
from now_workbench.domains.releases.models import WorkspaceRoute


def resolve_workspace(workspace_type: str, release: str) -> WorkspaceRoute:
    """Resolve the authentic workspace name and URI path for a given release family.

    Takes into account workspace evolution (e.g., Agent Workspace in Rome becoming
    Service Operations Workspace in San Diego+, or AI Agent Studio available only in Xanadu+).
    """
    norm_rel = normalize_release(release)
    clean_type = workspace_type.lower().strip()

    # 1. IT Service Management / Operations
    if clean_type in ("itsm", "it", "incident", "sow", "agent_workspace"):
        if compare_releases(norm_rel, "San Diego") < 0:
            return WorkspaceRoute(
                workspace_type="itsm",
                release=norm_rel,
                display_name="Agent Workspace",
                path="/now/workspace/agent/",
                description="Legacy Agent Workspace for IT (Rome and earlier)",
            )
        return WorkspaceRoute(
            workspace_type="itsm",
            release=norm_rel,
            display_name="Service Operations Workspace",
            path="/now/sow/",
            description="Service Operations Workspace (SOW) for ITSM & ITOM (San Diego+)",
        )

    # 2. Customer Service Management
    if clean_type in ("csm", "customer_service", "case"):
        if compare_releases(norm_rel, "Utah") < 0:
            return WorkspaceRoute(
                workspace_type="csm",
                release=norm_rel,
                display_name="Customer Service Workspace",
                path="/now/workspace/csm/",
                description="Classic Customer Service Workspace (pre-Utah)",
            )
        return WorkspaceRoute(
            workspace_type="csm",
            release=norm_rel,
            display_name="Configurable CSM Workspace",
            path="/now/csm/",
            description="Configurable Customer Service Workspace (Utah+)",
        )

    # 3. AI Agent Studio / Now Assist Administration
    if clean_type in ("ai_studio", "agent_studio", "ai_agent_studio", "now_assist"):
        if compare_releases(norm_rel, "Xanadu") < 0:
            return WorkspaceRoute(
                workspace_type="ai_studio",
                release=norm_rel,
                display_name="Not Available (Pre-Xanadu)",
                path="",
                is_available=False,
                description=(
                    "AI Agent Studio was introduced in Xanadu and is not available on this release."
                ),
            )
        return WorkspaceRoute(
            workspace_type="ai_studio",
            release=norm_rel,
            display_name="AI Agent Studio",
            path="/now/now-assist-admin/",
            description="Autonomous AI Agent Studio and Now Assist Administration (Xanadu+)",
        )

    # 4. HR Service Delivery / Employee Center
    if clean_type in ("hr", "hrsd", "employee_center", "onboarding"):
        return WorkspaceRoute(
            workspace_type="hr",
            release=norm_rel,
            display_name="Employee Center Workspace",
            path="/esc",
            description="Unified Employee Center and HR Service Delivery Portal",
        )

    # 5. Standard Classic Navigation
    if compare_releases(norm_rel, "San Diego") < 0:
        return WorkspaceRoute(
            workspace_type="classic",
            release=norm_rel,
            display_name="Classic UI16 Navigation",
            path="/nav_to.do?uri=",
            description="Legacy ServiceNow UI16 Application Navigator",
        )
    return WorkspaceRoute(
        workspace_type="classic",
        release=norm_rel,
        display_name="Next Experience Navigation",
        path="/now/nav/ui/classic/params/target/",
        description="Unified Next Experience Polaris Navigation",
    )


def translate_workspace_url(target_path: str, release: str) -> str:
    """Translate generic or symbolic workspace paths according to release capabilities."""
    norm_rel = normalize_release(release)

    if "@workspace/itsm" in target_path:
        route = resolve_workspace("itsm", norm_rel)
        return target_path.replace("@workspace/itsm", route.path.rstrip("/"))

    if "@workspace/csm" in target_path:
        route = resolve_workspace("csm", norm_rel)
        return target_path.replace("@workspace/csm", route.path.rstrip("/"))

    if "@workspace/ai_studio" in target_path:
        route = resolve_workspace("ai_studio", norm_rel)
        return target_path.replace("@workspace/ai_studio", route.path.rstrip("/"))

    # If legacy URL used on older platform
    if compare_releases(norm_rel, "San Diego") < 0:
        if "/now/nav/ui/classic/params/target/" in target_path:
            return target_path.replace("/now/nav/ui/classic/params/target/", "/nav_to.do?uri=")
        if "/now/sow/" in target_path:
            return target_path.replace("/now/sow/", "/now/workspace/agent/")

    return target_path
