"""FastAPI backend server for now-workbench."""

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from now_workbench.ai.actions import execute_autonomous_action
from now_workbench.ai.agent import AgentEventType, ClaudeAgentRunner, make_async_client
from now_workbench.ai.client import OttoClient
from now_workbench.ai.tiles import GenerativeUIResponse, resolve_query_to_tiles
from now_workbench.api.demos import router as demos_router
from now_workbench.api.instances import router as instances_router
from now_workbench.api.profile import router as profile_router
from now_workbench.api.settings_api import router as settings_router
from now_workbench.api.setup import router as setup_router
from now_workbench.api.team import router as team_router
from now_workbench.api.templates import router as templates_router
from now_workbench.api.threads import _load_verified_instances_dict
from now_workbench.api.threads import router as threads_router
from now_workbench.auth.access import AccessValidator
from now_workbench.auth.guard import AccessMiddleware, assert_safe_binding
from now_workbench.auth.models import Role
from now_workbench.auth.owner import operator_owner, owner_scope
from now_workbench.auth.setup import SetupCodes
from now_workbench.capture.engine import PlaywrightCaptureEngine
from now_workbench.config.origins import is_origin_allowed
from now_workbench.config.paths import UnsafePathError, safe_child
from now_workbench.config.settings import settings
from now_workbench.db import (
    ChatMessageRecord,
    DatabaseRepository,
    InstanceCreate,
    TemplateRecord,
    db_session,
)
from now_workbench.sdk.runner import NowSdkRunner


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


def seed_database(repo: DatabaseRepository) -> None:
    """Seed initial instance and template if database is empty."""
    if not repo.list_instances() and settings.sn_instance_url:
        repo.add_instance(
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

    if not repo.list_templates():
        repo.save_template(
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
    with db_session() as repo:
        return repo.get_user_roles(email)


def _setup_pending() -> bool:
    with db_session() as repo:
        return repo.count_admins() == 0


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Check the binding, then seed the database (never at import)."""
    assert_safe_binding(settings.get_host(), app.state.access_validator)
    configured = app.state.access_validator.configured
    with db_session() as repo:
        with owner_scope(operator_owner(repo, local_mode=not configured)):
            seed_database(repo)
        needs_setup = configured and repo.count_admins() == 0
    if needs_setup:
        app.state.setup_codes.issue()
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
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(UnsafePathError)
    async def _reject_unsafe_path(_request: Request, exc: UnsafePathError) -> JSONResponse:
        """Turn a rejected user-supplied id into HTTP 400 on every route (never 500)."""
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.include_router(instances_router)
    app.include_router(templates_router)
    app.include_router(demos_router)
    app.include_router(threads_router)
    app.include_router(settings_router)
    app.include_router(profile_router)
    app.include_router(setup_router)
    app.include_router(team_router)

    sdk_runner = NowSdkRunner(now_sdk_bin=settings.now_sdk_bin, node_bin=settings.node_bin)
    log_broadcaster = LogBroadcaster()

    _register_diagnostics(app, sdk_runner)
    _register_ai_tiles(app)
    _register_build_deploy(app, sdk_runner, log_broadcaster)
    _register_legacy_capture_routes(app)
    _register_websockets(app, log_broadcaster)
    _mount_static_ui(app)

    return app


def _register_diagnostics(app: FastAPI, sdk_runner: NowSdkRunner) -> None:
    """Register health check and administrative diagnostics routes."""

    @app.get("/api/health")
    def health_check() -> dict[str, Any]:
        with db_session() as repo:
            default_inst = repo.get_default_instance()
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
        with db_session() as repo:
            instances = repo.list_instances()
            default_inst = repo.get_default_instance()
        return {
            "app_version": "0.2.0",
            "python_runtime": "3.14.10",
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
        with db_session() as repo:
            action_resp = execute_autonomous_action(req.query, repo)
            if action_resp is not None:
                return action_resp
            instances = _load_verified_instances_dict(repo)
        return resolve_query_to_tiles(req.query, instances=instances)


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
        target = safe_child(settings.get_bundles_dir(), bundle_id)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Demo bundle not found.")
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
        target = safe_child(settings.get_bundles_dir(), bundle_id)
        if not target.exists():
            raise HTTPException(status_code=404, detail="Demo bundle not found.")

        with db_session() as repo:
            target_inst = (
                repo.get_instance(req.instance_id)
                if req.instance_id
                else repo.get_default_instance()
            )
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


def _register_legacy_capture_routes(app: FastAPI) -> None:
    """Register backwards-compatible media capture aliases."""

    @app.get("/api/capture/{bundle_id}/list")
    def legacy_list_captures(bundle_id: str) -> dict[str, Any]:
        engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
        return {"captures": [c.model_dump() for c in engine.list_captures(bundle_id)]}

    @app.delete("/api/capture/{bundle_id}/all")
    def legacy_clear_bundle_captures(bundle_id: str) -> dict[str, Any]:
        engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
        count = engine.clear_all_captures(bundle_id)
        return {"success": True, "bundle_id": bundle_id, "deleted_count": count}

    @app.delete("/api/capture/{filename}")
    def legacy_delete_capture(filename: str) -> dict[str, Any]:
        engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
        for b in settings.get_bundles_dir().iterdir():
            if b.is_dir() and (b / "media" / filename).exists():
                engine.delete_capture(b.name, filename)
                return {"success": True, "bundle_id": b.name, "filename": filename}
        raise HTTPException(status_code=404, detail="Capture artifact not found.")


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
                await _handle_ws_otto_message(websocket, data)
        except WebSocketDisconnect:
            pass


def _save_thread_turn(
    repo: DatabaseRepository, thread_id: str, prompt: str, final_resp: dict[str, Any]
) -> None:
    """Persist completed user prompt and agent response to SQLite thread."""
    repo.add_message(
        ChatMessageRecord(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            thread_id=thread_id,
            role="user",
            content=prompt,
        )
    )
    repo.add_message(
        ChatMessageRecord(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            thread_id=thread_id,
            role="assistant",
            content=final_resp.get("summary", ""),
            widget_type="generative_tiles",
            widget_data=final_resp,
        )
    )


async def _stream_agent_to_ws(
    websocket: WebSocket,
    runner: ClaudeAgentRunner,
    prompt: str,
    thread_id: str | None,
    repo: DatabaseRepository,
) -> None:
    """Stream Claude agent lifecycle events to WebSocket and persist to SQLite."""
    history = repo.list_messages(str(thread_id)) if thread_id else []
    final_resp: dict[str, Any] | None = None
    async for event in runner.stream_run(str(prompt), history):
        await websocket.send_json({"type": event.event_type.value, **event.payload})
        if event.event_type == AgentEventType.TEXT_DELTA:
            await websocket.send_json({"type": "chunk", "text": event.payload.get("text", "")})
        elif event.event_type == AgentEventType.DONE:
            final_resp = event.payload.get("response")

    if thread_id and final_resp:
        _save_thread_turn(repo, str(thread_id), str(prompt), final_resp)
    await websocket.send_json({"type": "done"})


async def _handle_ws_otto_message(websocket: WebSocket, data: dict[str, Any]) -> None:
    """Process a WebSocket Otto chat request with real-time streaming (ADR-011)."""
    prompt = data.get("prompt") or data.get("content")
    thread_id = data.get("thread_id")
    messages = data.get("messages", [])
    context = data.get("context", {})

    with db_session() as repo:
        api_key = repo.get_decrypted_anthropic_api_key()
        prefs = repo.get_workbench_preferences()
        active_key = api_key or settings.anthropic_api_key
        model = prefs.claude_model if api_key else settings.claude_model
        fake_mode = prefs.sdk_fake_mode

    if prompt and active_key:
        with db_session() as repo:
            runner = ClaudeAgentRunner(
                client=make_async_client(active_key),
                model=model,
                repo=repo,
                fake_mode=fake_mode,
            )
            await _stream_agent_to_ws(websocket, runner, str(prompt), thread_id, repo)
    else:
        live_client = OttoClient(api_key=active_key, model=model)
        async for chunk in live_client.stream_chat(messages, context=context):
            await websocket.send_json({"type": "chunk", "text": chunk})
        await websocket.send_json({"type": "done"})


app = create_app()
