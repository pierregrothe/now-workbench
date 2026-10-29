"""FastAPI backend server for now-workbench."""

from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from now_workbench.ai.client import OttoClient
from now_workbench.bundles.manager import BundleManager
from now_workbench.bundles.models import DemoBundleInfo
from now_workbench.config.settings import settings
from now_workbench.sdk.runner import NowSdkRunner


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI app."""
    app = FastAPI(
        title="now-workbench",
        description="AI-native developer & demonstration workbench for ServiceNow SDK",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    bundle_mgr = BundleManager(storage_dir=settings.bundles_dir)
    sdk_runner = NowSdkRunner(now_sdk_bin=settings.now_sdk_bin, node_bin=settings.node_bin)
    otto_client = OttoClient(api_key=settings.anthropic_api_key, model=settings.claude_model)

    # ── Health & Diagnostics ──────────────────────────────────────────────────
    @app.get("/api/health")
    def health_check() -> dict[str, Any]:
        env_probe = sdk_runner.probe_environment()
        return {
            "status": "healthy",
            "app": settings.app_name,
            "instance": {
                "configured": bool(settings.sn_instance_url),
                "url": settings.sn_instance_url,
            },
            "claude_connected": bool(settings.anthropic_api_key),
            "toolchain": env_probe,
        }

    # ── Demo Bundles ──────────────────────────────────────────────────────────
    @app.get("/api/demos", response_model=list[DemoBundleInfo])
    def get_demos() -> list[DemoBundleInfo]:
        return bundle_mgr.list_bundles()

    @app.get("/api/demos/{bundle_id}", response_model=DemoBundleInfo)
    def get_demo_detail(bundle_id: str) -> DemoBundleInfo:
        target = settings.bundles_dir / bundle_id
        if not target.exists():
            raise HTTPException(status_code=404, detail="Demo bundle not found")
        return bundle_mgr.inspect_bundle(target)

    @app.get("/api/demos/{bundle_id}/export")
    def export_demo(bundle_id: str) -> FileResponse:
        output_file = settings.workspace_dir / f"{bundle_id}.sn-demo.zip"
        try:
            bundle_mgr.export_bundle(bundle_id, output_file)
            return FileResponse(
                path=output_file,
                filename=f"{bundle_id}.sn-demo.zip",
                media_type="application/zip",
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ── Build & Deploy Operations ─────────────────────────────────────────────
    class BuildRequest(BaseModel):
        stream_logs: bool = True

    @app.post("/api/demos/{bundle_id}/build")
    async def build_demo(bundle_id: str, req: BuildRequest) -> dict[str, Any]:
        target = settings.bundles_dir / bundle_id
        if not target.exists():
            raise HTTPException(status_code=404, detail="Demo bundle not found")
        res = await sdk_runner.build(target)
        return {
            "success": res.success,
            "exit_code": res.exit_code,
            "output": res.output,
        }

    @app.post("/api/demos/{bundle_id}/deploy")
    async def deploy_demo(bundle_id: str, req: BuildRequest) -> dict[str, Any]:
        target = settings.bundles_dir / bundle_id
        if not target.exists():
            raise HTTPException(status_code=404, detail="Demo bundle not found")
        res = await sdk_runner.deploy(target)
        return {
            "success": res.success,
            "exit_code": res.exit_code,
            "output": res.output,
        }

    # ── Otto Copilot WebSocket ────────────────────────────────────────────────
    @app.websocket("/ws/otto")
    async def ws_otto_chat(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_json()
                messages = data.get("messages", [])
                context = data.get("context", {})

                # Stream response chunks back to the client
                async for chunk in otto_client.stream_chat(messages, context=context):
                    await websocket.send_json({"type": "chunk", "text": chunk})
                await websocket.send_json({"type": "done"})
        except WebSocketDisconnect:
            pass

    # ── Static Web UI (Lit / Vite build) ──────────────────────────────────────
    if settings.static_dir.exists() and (settings.static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="static")

    return app


app = create_app()
