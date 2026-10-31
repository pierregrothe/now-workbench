// web/src/controllers/capture-gallery-controller.ts
// ReactiveController managing media capture runs and artifact gallery CRUD.
// Author: Pierre Grothe
// Date: 2026-10-31

import type { ReactiveController, ReactiveControllerHost } from 'lit';

export interface CaptureArtifact {
  id: string;
  bundle_id: string;
  instance_url: string;
  target_path: string;
  media_type: 'screenshot' | 'video';
  label: string;
  filename: string;
  file_path: string;
  url: string;
  engine: string;
  created_at: string;
}

export interface CaptureTriggerParams {
  bundleId: string;
  uriPath: string;
  mode: 'screenshot' | 'video';
  caption: string;
  instanceId?: string;
}

export class CaptureGalleryController implements ReactiveController {
  private host: ReactiveControllerHost;
  public captures: CaptureArtifact[] = [];
  public isLoading: boolean = false;
  public isCapturing: boolean = false;
  public previewCapture: CaptureArtifact | null = null;
  public error: string | null = null;
  public statusMessage: string = '';

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {}
  hostDisconnected(): void {}

  async loadCaptures(bundleId: string = 'sample-ai-assistant'): Promise<void> {
    this.isLoading = true;
    this.error = null;
    this.host.requestUpdate();

    try {
      const res = await fetch(`/api/capture/${encodeURIComponent(bundleId)}/list`);
      if (res.ok) {
        const data = await res.json();
        this.captures = data.captures || [];
      }
    } catch (err: any) {
      this.error = err.message || 'Failed to load captures';
    } finally {
      this.isLoading = false;
      this.host.requestUpdate();
    }
  }

  async triggerCapture(params: CaptureTriggerParams): Promise<CaptureArtifact | null> {
    this.isCapturing = true;
    this.error = null;
    this.statusMessage = `Triggering ${params.mode} capture via native driver...`;
    this.host.requestUpdate();

    try {
      const payload: Record<string, any> = {
        bundle_id: params.bundleId,
        target_path: params.uriPath,
        media_type: params.mode,
        label: params.caption,
      };
      if (params.instanceId) {
        payload.instance_id = params.instanceId;
      }

      const res = await fetch('/api/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Capture failed (HTTP ${res.status})`);
      }

      const data = await res.json();
      this.statusMessage = `${params.mode === 'video' ? 'Video proof' : 'Screenshot'} captured successfully!`;
      await this.loadCaptures(params.bundleId);
      return data;
    } catch (err: any) {
      this.error = err.message || 'Capture failed';
      this.statusMessage = `Error: ${this.error}`;
      return null;
    } finally {
      this.isCapturing = false;
      this.host.requestUpdate();
    }
  }

  async renameCapture(filename: string, newLabel: string, bundleId: string = 'sample-ai-assistant'): Promise<boolean> {
    try {
      const res = await fetch(`/api/capture/metadata/${encodeURIComponent(filename)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: newLabel }),
      });
      if (res.ok) {
        await this.loadCaptures(bundleId);
        return true;
      }
      return false;
    } catch (err: any) {
      this.error = err.message || 'Rename failed';
      this.host.requestUpdate();
      return false;
    }
  }

  async deleteCapture(filename: string, bundleId: string = 'sample-ai-assistant'): Promise<boolean> {
    try {
      const res = await fetch(`/api/capture/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        if (this.previewCapture?.filename === filename) {
          this.previewCapture = null;
        }
        await this.loadCaptures(bundleId);
        return true;
      }
      return false;
    } catch (err: any) {
      this.error = err.message || 'Delete failed';
      this.host.requestUpdate();
      return false;
    }
  }

  setPreview(artifact: CaptureArtifact | null): void {
    this.previewCapture = artifact;
    this.host.requestUpdate();
  }
}
