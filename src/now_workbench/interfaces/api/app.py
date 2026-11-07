"""FastAPI backend server for now-workbench."""

import logging
import platform
import sqlite3
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from now_workbench.domains.identity import (
    AuthUser,
    Role,
    SetupCodes,
    UserRepository,
    effective_user,
    operator_owner,
)
from now_workbench.domains.instances import InstanceCreate, InstanceRepository
from now_workbench.domains.sharing import resolve_bundle, sync_registry
from now_workbench.domains.templates import TemplateRecord, TemplateRepository
from now_workbench.interfaces.ai.tile_routing import resolve_query_to_tiles
from now_workbench.interfaces.ai.tiles import GenerativeUIResponse
from now_workbench.interfaces.api.access import AccessValidator
from now_workbench.interfaces.api.actions import router as actions_router
from now_workbench.interfaces.api.attachments import attachments_router, limits_router
from now_workbench.interfaces.api.captures import router as captures_router
from now_workbench.interfaces.api.demos import router as demos_router
from now_workbench.interfaces.api.errors import install_error_handlers
from now_workbench.interfaces.api.feedback import router as feedback_router
from now_workbench.interfaces.api.guard import AccessMiddleware, assert_safe_binding
from now_workbench.interfaces.api.impersonation import router as impersonation_router
from now_workbench.interfaces.api.instances import router as instances_router
from now_workbench.interfaces.api.otto_ws import handle_ws_otto_message
from now_workbench.interfaces.api.profile import router as profile_router
from now_workbench.interfaces.api.properties import router as properties_router
from now_workbench.interfaces.api.replies import load_verified_instances_dict
from now_workbench.interfaces.api.retention import telemetry_retention
from now_workbench.interfaces.api.settings_api import router as settings_router
from now_workbench.interfaces.api.setup import router as setup_router
from now_workbench.interfaces.api.sharing import approvals_router, artifacts_router, groups_router
from now_workbench.interfaces.api.team import router as team_router
from now_workbench.interfaces.api.templates import router as templates_router
from now_workbench.interfaces.api.threads import router as threads_router
from now_workbench.interfaces.api.usage import router as usage_router
from now_workbench.platform.config.origins import is_origin_allowed
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import owner_scope
from now_workbench.platform.sdk.runner import NowSdkRunner


async def _accept_if_origin_allowed(websocket: WebSocket) -> bool:
    """Accept the handshake, or close with 1008 when its Origin is not allowed."""
    origin = websocket.headers.get("origin")
    if not is_origin_allowed(origin, settings.cors_origin_regex):
        await websocket.close(code=1008)
        return False
    await websocket.accept()
    return True


class LogBroadcaster:
    """Manages active WebSocket connections for live terminal log streaming."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> bool:
        """Accept the socket unless its Origin is disallowed; return whether accepted."""
        if not await _accept_if_origin_allowed(websocket):
            return False
        self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, line: str) -> None:
        for connection in list(self.active_connections):
            try:
                await connection.send_json({"type": "log", "line": line})
            except Exception:
                self.disconnect(connection)


def seed_database(conn: sqlite3.Connection) -> None:
    """Seed initial instance and template if database is empty."""
    instance_repo = InstanceRepository(conn)
    template_repo = TemplateRepository(conn)
    if not instance_repo.list_instances() and settings.sn_instance_url:
        instance_repo.add_instance(
            InstanceCreate(
                id="default-instance",
                name="Primary ServiceNow Instance",
                url=settings.sn_instance_url,
                username=settings.sn_username or "admin",
                password=settings.sn_password or "",
                auth_type=settings.sn_auth_type or "basic",
                is_default=True,
            )
        )

    if not template_repo.list_templates():
        template_repo.save_template(
            TemplateRecord(
                id="agentic-router-template",
                name="GenAI Agentic Incident Router Template",
                description="Customizable AI routing and triage application for IT incidents",
                version="1.0.0",
                base_bundle_id="template-customer-service-ai",
                parameters_schema={
                    "customer_name": {"type": "string", "default": "Customer Corp"},
                    "primary_color": {"type": "string", "default": "#23a17e"},
                    "secondary_color": {"type": "string", "default": "#0284c7"},
                    "assignment_group": {"type": "string", "default": "IT Tier 1"},
                },
            )
        )


def _mount_static_ui(app: FastAPI) -> None:
    """Mount compiled frontend static files if present."""
    if settings.static_dir.exists() and (settings.static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="static")


def _log_setup_code(code: str) -> None:
    """Write the first-run setup code to the server log (``docker logs``)."""
    log = logging.getLogger("uvicorn.error")
    log.warning("=" * 60)
    log.warning("FIRST-RUN SETUP CODE: %s", code)
    log.warning("Open the workbench, sign in, and enter this code to become administrator.")
    log.warning("=" * 60)


def _stored_roles(email: str) -> frozenset[Role]:
    with db_session() as conn:
        return UserRepository(conn).get_user_roles(email)


def _act_as(user: AuthUser) -> AuthUser:
    with db_session() as conn:
        return effective_user(conn, user)


def _setup_pending() -> bool:
    with db_session() as conn:
        return UserRepository(conn).count_admins() == 0


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Check the binding, then seed the database (never at import)."""
    assert_safe_binding(settings.get_host(), app.state.access_validator)
    configured = app.state.access_validator.configured
    with db_session() as conn:
        operator = operator_owner(conn, local_mode=not configured)
        with owner_scope(operator):
            seed_database(conn)
        sync_registry(conn, operator)
        needs_setup = configured and UserRepository(conn).count_admins() == 0
    if needs_setup:
        app.state.setup_codes.issue()
    async with telemetry_retention():
        yield


def create_app(
    access_validator: AccessValidator | None = None,
    announce_setup_code: Callable[[str], None] | None = None,
) -> FastAPI:
    """Factory creating and configuring the FastAPI app.

    Args:
        access_validator: Cloudflare Access validator; built from settings when omitted.
        announce_setup_code: Receives a newly issued first-run setup code (the server log
            when omitted).
    """
    app = FastAPI(
        title="now-workbench",
        description="AI-native developer & demonstration workbench for ServiceNow SDK",
        version="0.2.0",
        lifespan=_lifespan,
    )

    validator = access_validator or AccessValidator(
        settings.get_access_team_domain(), settings.get_access_audience()
    )
    app.state.access_validator = validator
    app.state.setup_codes = SetupCodes(announce_setup_code or _log_setup_code)
    # Added first so it sits inside CORS: preflight requests are answered before sign-in checks.
    app.add_middleware(
        AccessMiddleware,
        validator=validator,
        lookup_roles=_stored_roles,
        setup_pending=_setup_pending,
        act_as=_act_as,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)

    app.include_router(instances_router)
    app.include_router(templates_router)
    app.include_router(demos_router)
    app.include_router(captures_router)
    app.include_router(properties_router)
    app.include_router(threads_router)
    app.include_router(feedback_router)
    app.include_router(usage_router)
    app.include_router(settings_router)
    app.include_router(profile_router)
    app.include_router(setup_router)
    app.include_router(team_router)
    app.include_router(groups_router)
    app.include_router(artifacts_router)
    app.include_router(approvals_router)
    app.include_router(impersonation_router)
    app.include_router(attachments_router)
    app.include_router(limits_router)
    app.include_router(actions_router)

    sdk_runner = NowSdkRunner(now_sdk_bin=settings.now_sdk_bin, node_bin=settings.node_bin)
    log_broadcaster = LogBroadcaster()

    _register_diagnostics(app, sdk_runner)
    _register_ai_tiles(app)
    _register_build_deploy(app, sdk_runner, log_broadcaster)
    _register_websockets(app, log_broadcaster)
    _mount_static_ui(app)

    return app


def _register_diagnostics(app: FastAPI, sdk_runner: NowSdkRunner) -> None:
    """Register health check and administrative diagnostics routes."""

    @app.get("/api/health")
    def health_check() -> dict[str, Any]:
        with db_session() as conn:
            default_inst = InstanceRepository(conn).get_default_instance()
        return {
            "status": "healthy",
            "app": settings.app_name,
            "instance": {
                "configured": default_inst is not None,
                "name": default_inst.name if default_inst else "",
                "url": default_inst.url if default_inst else "",
                "status": default_inst.status if default_inst else "unconfigured",
            },
            "otto_connected": bool(settings.anthropic_api_key),
        }

    @app.get("/api/admin/diagnostics")
    def admin_diagnostics() -> dict[str, Any]:
        env_probe = sdk_runner.probe_environment()
        with db_session() as conn:
            instance_repo = InstanceRepository(conn)
            instances = instance_repo.list_instances()
            default_inst = instance_repo.get_default_instance()
        return {
            "app_version": "0.2.0",
            "python_runtime": platform.python_version(),
            "toolchain": env_probe,
            "instances_count": len(instances),
            "active_instance": default_inst.name if default_inst else "None",
            "active_instance_url": default_inst.url if default_inst else "None",
            "otto_status": "Ready" if settings.anthropic_api_key else "Simulated",
        }


def _register_ai_tiles(app: FastAPI) -> None:
    """Register generative AI tile resolution endpoint."""

    class GenerativeUIQueryRequest(BaseModel):
        model_config = ConfigDict(extra="forbid", frozen=True)
        query: str

    @app.post("/api/ai/tiles", response_model=GenerativeUIResponse)
    def query_generative_ui(req: GenerativeUIQueryRequest) -> GenerativeUIResponse:
        with db_session() as conn:
            instances = load_verified_instances_dict(conn)
        return resolve_query_to_tiles(req.query, instances=instances)


def _accessible_bundle(bundle_id: str) -> Path:
    """Return a bundle the signed-in person owns or was shared (ADR-018), else 404."""
    with db_session() as conn:
        try:
            return resolve_bundle(conn, bundle_id).path
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Demo bundle not found.") from exc


def _register_build_deploy(
    app: FastAPI, sdk_runner: NowSdkRunner, log_broadcaster: LogBroadcaster
) -> None:
    """Register demo build and deployment execution endpoints."""

    class BuildRequest(BaseModel):
        model_config = ConfigDict(extra="forbid", frozen=True)
        stream_logs: bool = True
        instance_id: str | None = None

    @app.post("/api/demos/{bundle_id}/build")
    async def build_demo(bundle_id: str, req: BuildRequest) -> dict[str, Any]:
        target = _accessible_bundle(bundle_id)
        await log_broadcaster.broadcast(f"[build:start] Building bundle '{bundle_id}'...")
        res = await sdk_runner.build(
            target,
            stream_callback=log_broadcaster.broadcast if req.stream_logs else None,
        )
        await log_broadcaster.broadcast(
            f"[build:done] Finished with exit code {res.exit_code} (success={res.success})"
        )
        return {
            "success": res.success,
            "exit_code": res.exit_code,
            "output": res.output,
        }

    @app.post("/api/demos/{bundle_id}/deploy")
    async def deploy_demo(bundle_id: str, req: BuildRequest) -> dict[str, Any]:
        target = _accessible_bundle(bundle_id)

        with db_session() as conn:
            target_inst = InstanceRepository(conn).resolve(req.instance_id)
        if target_inst is None:
            if req.instance_id:
                raise HTTPException(status_code=404, detail="Instance not found")
            raise HTTPException(status_code=409, detail="No target instance registered")
        inst_url = target_inst.url
        inst_user = target_inst.username
        inst_pwd = target_inst.password

        await log_broadcaster.broadcast(
            f"[deploy:start] Deploying bundle '{bundle_id}' to target: {inst_url}..."
        )
        res = await sdk_runner.deploy(
            target,
            instance_url=inst_url,
            username=inst_user,
            password=inst_pwd,
            stream_callback=log_broadcaster.broadcast if req.stream_logs else None,
        )
        await log_broadcaster.broadcast(
            f"[deploy:done] Finished deployment (success={res.success})"
        )
        return {
            "success": res.success,
            "exit_code": res.exit_code,
            "output": res.output,
            "target_instance": target_inst.name,
            "target_instance_id": target_inst.id,
            "target_instance_name": target_inst.name,
        }


def _register_websockets(app: FastAPI, log_broadcaster: LogBroadcaster) -> None:
    """Register terminal log and Otto copilot WebSocket endpoints."""

    @app.websocket("/ws/logs")
    async def ws_logs(websocket: WebSocket) -> None:
        if not await log_broadcaster.connect(websocket):
            return
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            log_broadcaster.disconnect(websocket)

    @app.websocket("/ws/otto")
    async def ws_otto_chat(websocket: WebSocket) -> None:
        if not await _accept_if_origin_allowed(websocket):
            return
        try:
            while True:
                data = await websocket.receive_json()
                await handle_ws_otto_message(websocket, data)
        except WebSocketDisconnect:
            pass


app = create_app()
