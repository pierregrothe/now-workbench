// web/src/views/now-capture-studio.ts
// Media Capture Studio view: native Playwright proof generation and artifact management.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { CaptureGalleryController } from '../controllers/capture-gallery-controller.js';
import type { CaptureArtifact } from '../controllers/capture-gallery-controller.js';
import { workbenchStore } from '../context/workbench-context.js';
import { workspaceStyles } from '../styles/workspace-styles.js';
import '../modals/now-media-lightbox.js';
import { StoreController } from '../controllers/store-controller.js';
import './now-workspace-bar.js';

@customElement('now-capture-studio')
export class NowCaptureStudio extends LitElement {
  private gallery = new CaptureGalleryController(this);

  private readonly store = new StoreController(this);
  @state() private uriPath = '/now/nav/ui/classic/params/target/incident_list.do';
  @state() private captureMode: 'screenshot' | 'video' = 'screenshot';
  @state() private captureCaption = 'Live ServiceNow Workspace View';
  @state() private selectedBundleId = 'sample-ai-assistant';
  @state() private activeLightboxArtifact: CaptureArtifact | null = null;

  @property({ type: String })
  set incomingPrompt(val: string) {
    if (val && val.includes('/')) {
      this.uriPath = val.trim();
    }
  }

  static styles = [
    workspaceStyles,
    css`
      .studio-grid {
        display: grid;
        grid-template-columns: 360px 1fr;
        gap: 24px;
        align-items: start;
      }

      .form-group {
        margin-bottom: 14px;
      }

      .form-label {
        display: block;
        font-size: 11.5px;
        font-weight: 600;
        color: var(--now-text-secondary, #4b5563);
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .text-input, .select-input {
        width: 100%;
        box-sizing: border-box;
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid var(--now-border-subtle, #d1d5db);
        background: var(--now-bg-surface-0, #ffffff);
        color: var(--now-text-primary, #111827);
        font-size: 13px;
        font-family: inherit;
      }

      .mode-toggle {
        display: flex;
        gap: 8px;
        margin-bottom: 14px;
      }

      .mode-btn {
        flex: 1;
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid var(--now-border-subtle, #d1d5db);
        background: var(--now-bg-surface-0, #ffffff);
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
      }

      .mode-btn.active {
        background: var(--now-color-primary, #032d42);
        color: #ffffff;
        border-color: var(--now-color-primary, #032d42);
      }

      .gallery-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 16px;
      }

      .artifact-card {
        background: var(--now-bg-surface-0, #ffffff);
        border: 1px solid var(--now-border-subtle, #e5e7eb);
        border-radius: 8px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }

      .artifact-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      }

      .thumbnail-container {
        height: 160px;
        background: #0b1f30;
        position: relative;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .thumbnail-container img, .thumbnail-container video {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .play-overlay {
        position: absolute;
        width: 40px;
        height: 40px;
        background: rgba(0, 0, 0, 0.65);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        pointer-events: none;
      }

      .artifact-info {
        padding: 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .artifact-title {
        font-size: 13px;
        font-weight: 700;
        color: var(--now-text-primary, #111827);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .artifact-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 11px;
        color: var(--now-text-secondary, #6b7280);
      }

      .card-actions {
        display: flex;
        gap: 6px;
        padding: 8px 12px;
        border-top: 1px solid var(--now-border-subtle, #f3f4f6);
        background: var(--now-bg-surface-1, #f9fafb);
      }

      .small-btn {
        padding: 3px 8px;
        font-size: 11px;
        font-weight: 600;
        border-radius: 4px;
        border: 1px solid var(--now-border-subtle, #d1d5db);
        background: #ffffff;
        cursor: pointer;
      }

      .small-btn.danger {
        color: #dc2626;
        border-color: #fca5a5;
      }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    workbenchStore.loadInstances();
    workbenchStore.loadBundles();
    this.gallery.loadCaptures(this.selectedBundleId);
  }


  private async handleTriggerCapture(): Promise<void> {
    await this.gallery.triggerCapture({
      bundleId: this.selectedBundleId,
      uriPath: this.uriPath,
      mode: this.captureMode,
      caption: this.captureCaption,
      instanceId: this.store.state.selectedInstanceId,
    });
  }

  private async handleBundleChange(e: Event): Promise<void> {
    this.selectedBundleId = (e.target as HTMLSelectElement).value;
    await this.gallery.loadCaptures(this.selectedBundleId);
  }


  private async handleRename(filename: string, currentLabel?: string): Promise<void> {
    const newLabel = window.prompt('Enter new caption/label for capture:', currentLabel || '');
    if (newLabel && newLabel.trim()) {
      await this.gallery.renameCapture(filename, newLabel.trim(), this.selectedBundleId);
    }
  }

  private async handleDelete(filename: string): Promise<void> {
    if (window.confirm('Delete this capture proof?')) {
      await this.gallery.deleteCapture(filename, this.selectedBundleId);
      workbenchStore.loadBundles();
    }
  }

  private async handleClearAllCaptures(): Promise<void> {
    if (
      window.confirm(
        `Are you sure you want to delete all ${this.gallery.captures.length} captured media proofs for '${this.selectedBundleId}'? This cannot be undone.`
      )
    ) {
      await this.gallery.clearAllCaptures(this.selectedBundleId);
      workbenchStore.loadBundles();
    }
  }

  render() {
    return html`
      <now-workspace-bar crumb="Media Capture Studio" show-load-error></now-workspace-bar>

      <div class="scroll-canvas">
        <div class="canvas-container">
          <h2 class="section-title">Playwright Media Capture Studio</h2>
          <p class="section-subtitle">
            Generate verifiable full-page screenshots and native WebM video walkthrough proofs using the native Playwright engine.
          </p>

          <div class="studio-grid">
            <div class="card">
              <div class="form-group">
                <label class="form-label">Capture Mode</label>
                <div class="mode-toggle">
                  <button
                    class="mode-btn ${this.captureMode === 'screenshot' ? 'active' : ''}"
                    @click=${() => (this.captureMode = 'screenshot')}
                  >
                    Screenshot Proof
                  </button>
                  <button
                    class="mode-btn ${this.captureMode === 'video' ? 'active' : ''}"
                    @click=${() => (this.captureMode = 'video')}
                  >
                    Video Walkthrough
                  </button>
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Target Demo Bundle</label>
                <select class="select-input" .value=${this.selectedBundleId} @change=${this.handleBundleChange}>
                  ${this.store.state.bundles.length
                    ? this.store.state.bundles.map(
                        (b) => html`<option value=${b.id}>${b.name} (${b.release})</option>`
                      )
                    : html`<option value="sample-ai-assistant">sample-ai-assistant (Zurich)</option>`}
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">ServiceNow Target URI</label>
                <input
                  type="text"
                  class="text-input"
                  .value=${this.uriPath}
                  @input=${(e: Event) => (this.uriPath = (e.target as HTMLInputElement).value)}
                />
              </div>

              <div class="form-group">
                <label class="form-label">Proof Caption / Label</label>
                <input
                  type="text"
                  class="text-input"
                  .value=${this.captureCaption}
                  @input=${(e: Event) => (this.captureCaption = (e.target as HTMLInputElement).value)}
                />
              </div>

              <div style="margin-top: 20px;">
                <button
                  class="pill-btn primary"
                  style="width: 100%; justify-content: center; padding: 10px;"
                  ?disabled=${this.gallery.isCapturing}
                  @click=${this.handleTriggerCapture}
                >
                  ${this.gallery.isCapturing ? 'Recording Proof...' : `Capture ${this.captureMode === 'video' ? 'Video' : 'Screenshot'}`}
                </button>
              </div>

              ${this.gallery.statusMessage
                ? html`<div class="badge info" style="margin-top: 14px; display: block;">${this.gallery.statusMessage}</div>`
                : ''}
            </div>

            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="margin: 0; font-size: 15px; font-weight: 700;">Captured Proofs (${this.gallery.captures.length})</h3>
                <div style="display: flex; gap: 8px;">
                  <button class="small-btn" @click=${() => this.gallery.loadCaptures(this.selectedBundleId)}>Refresh</button>
                  ${this.gallery.captures.length > 0
                    ? html`
                        <button class="small-btn danger" @click=${this.handleClearAllCaptures}>
                          Clear All (${this.gallery.captures.length})
                        </button>
                      `
                    : ''}
                </div>
              </div>

              ${this.gallery.captures.length === 0
                ? html`
                    <div class="card" style="text-align: center; padding: 48px 20px; color: #6b7280;">
                      <p style="font-weight: 600; margin-bottom: 6px;">No capture artifacts found for ${this.selectedBundleId}</p>
                      <p style="font-size: 12px;">Trigger a screenshot or video proof on the left.</p>
                    </div>
                  `
                : html`
                    <div class="gallery-grid">
                      ${this.gallery.captures.map(
                        (cap) => html`
                          <div class="artifact-card">
                            <div class="thumbnail-container" @click=${() => (this.activeLightboxArtifact = cap)}>
                              ${cap.media_type === 'video'
                                ? html`
                                    <video src=${cap.url} preload="metadata"></video>
                                    <div class="play-overlay">
                                      <svg viewBox="0 0 24 24" style="width: 20px; height: 20px; fill: currentColor;"><path d="M8 5v14l11-7z"/></svg>
                                    </div>
                                  `
                                : html`<img src=${cap.url} alt=${cap.label || cap.filename} />`}
                            </div>
                            <div class="artifact-info">
                              <div class="artifact-title" title=${cap.label || cap.filename}>${cap.label || cap.filename}</div>
                              <div class="artifact-meta">
                                <span class="badge ${cap.media_type === 'video' ? 'info' : 'success'}">${cap.media_type}</span>
                                <span>${cap.engine}</span>
                              </div>
                            </div>
                            <div class="card-actions">
                              <button class="small-btn" @click=${() => (this.activeLightboxArtifact = cap)}>View</button>
                              <button class="small-btn" @click=${() => this.handleRename(cap.filename, cap.label)}>Rename</button>
                              <button class="small-btn danger" @click=${() => this.handleDelete(cap.filename)}>Delete</button>
                            </div>
                          </div>
                        `
                      )}
                    </div>
                  `}
            </div>
          </div>
        </div>
      </div>

      <now-media-lightbox
        .artifact=${this.activeLightboxArtifact}
        @close=${() => (this.activeLightboxArtifact = null)}
        @rename=${(e: CustomEvent<{ filename: string; currentLabel?: string }>) =>
          this.handleRename(e.detail.filename, e.detail.currentLabel)}
        @delete=${(e: CustomEvent<{ filename: string }>) => {
          const fn = e.detail.filename;
          this.activeLightboxArtifact = null;
          void this.handleDelete(fn);
        }}
      ></now-media-lightbox>
    `;
  }
}
