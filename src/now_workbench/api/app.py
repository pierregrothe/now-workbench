"""FastAPI backend server for now-workbench."""

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from now_workbench.ai.actions import execute_autonomous_action
from now_workbench.ai.agent import AgentEventType, ClaudeAgentRunner, make_async_client
from now_workbench.ai.client import OttoClient
from now_workbench.ai.tiles import GenerativeUIResponse, resolve_query_to_tiles
from now_workbench.api.demos import router as demos_router
from now_workbench.api.instances import router as instances_router
from now_workbench.api.settings_api import router as settings_router
from now_workbench.api.templates import router as templates_router
from now_workbench.api.threads import _load_verified_instances_dict
from now_workbench.api.threads import router as threads_router
from now_workbench.config.settings import settings
from now_workbench.db import (
    ChatMessageRecord,
    DatabaseRepository,
    InstanceCreate,
    TemplateRecord,
    db_session,
)
from now_workbench.sdk.runner import NowSdkRunner


class LogBroadcaster:
    """Manages active WebSocket connections for live terminal log streaming."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

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
                release="Zurich",
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


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI app."""
    app = FastAPI(
        title="now-workbench",
        description="AI-native developer & demonstration workbench for ServiceNow SDK",
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    with db_session() as repo:
        seed_database(repo)

    app.include_router(instances_router)
    app.include_router(templates_router)
    app.include_router(demos_router)
    app.include_router(threads_router)
    app.include_router(settings_router)

    sdk_runner = NowSdkRunner(now_sdk_bin=settings.now_sdk_bin, node_bin=settings.node_bin)
    log_broadcaster = LogBroadcaster()

    # -- Health & Diagnostics --------------------------------------------------
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

    # -- Generative UI Tile Resolution -----------------------------------------
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

    # -- Build & Deploy Operations ---------------------------------------------
    class BuildRequest(BaseModel):
        model_config = ConfigDict(extra="forbid", frozen=True)

        stream_logs: bool = True
        instance_id: str | None = None

    @app.post("/api/demos/{bundle_id}/build")
    async def build_demo(bundle_id: str, req: BuildRequest) -> dict[str, Any]:
        target = settings.get_bundles_dir() / bundle_id
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
        target = settings.get_bundles_dir() / bundle_id
        if not target.exists():
            raise HTTPException(status_code=404, detail="Demo bundle not found.")

        with db_session() as repo:
            target_inst = (
                repo.get_instance(req.instance_id)
                if req.instance_id
                else repo.get_default_instance()
            )
        inst_url = target_inst.url if target_inst else None
        inst_user = target_inst.username if target_inst else None
        inst_pwd = target_inst.password if target_inst else None

        await log_broadcaster.broadcast(
            f"[deploy:start] Deploying bundle '{bundle_id}' to target: {inst_url or 'default'}..."
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
            "target_instance": target_inst.name if target_inst else "default",
        }

    # -- WebSockets & Static UI ------------------------------------------------
    _register_websockets(app, log_broadcaster)
    _mount_static_ui(app)

    return app


def _register_websockets(app: FastAPI, log_broadcaster: LogBroadcaster) -> None:
    """Register terminal log and Otto copilot WebSocket endpoints."""

    @app.websocket("/ws/logs")
    async def ws_logs(websocket: WebSocket) -> None:
        await log_broadcaster.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            log_broadcaster.disconnect(websocket)

    @app.websocket("/ws/otto")
    async def ws_otto_chat(websocket: WebSocket) -> None:
        await websocket.accept()
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
