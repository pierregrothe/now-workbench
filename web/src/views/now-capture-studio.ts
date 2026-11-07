// web/src/views/now-capture-studio.ts
// Media Capture Studio view: native Playwright proof generation and artifact management.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { CaptureGalleryController } from '../controllers/capture-gallery-controller.js';
import type { CaptureArtifact } from '../controllers/capture-gallery-controller.js';
import { workbenchStore } from '../context/workbench-context.js';
import { workspaceStyles } from '../styles/workspace-styles.js';
import { formStyles } from '../styles/form-styles.js';
import { captureStudioStyles } from './now-capture-studio-styles.js';
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

  static styles = [workspaceStyles, formStyles, captureStudioStyles];

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
                <div class="seg">
                  <button
                    class="seg-item mode-btn ${this.captureMode === 'screenshot' ? 'active' : ''}"
                    @click=${() => (this.captureMode = 'screenshot')}
                  >
                    Screenshot Proof
                  </button>
                  <button
                    class="seg-item mode-btn ${this.captureMode === 'video' ? 'active' : ''}"
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

              <div class="capture-action">
                <button
                  class="btn-primary capture-btn"
                  ?disabled=${this.gallery.isCapturing}
                  @click=${this.handleTriggerCapture}
                >
                  ${this.gallery.isCapturing ? 'Recording Proof...' : `Capture ${this.captureMode === 'video' ? 'Video' : 'Screenshot'}`}
                </button>
              </div>

              ${this.gallery.statusMessage
                ? html`<div class="badge info capture-status">${this.gallery.statusMessage}</div>`
                : ''}
            </div>

            <div>
              <div class="gallery-head">
                <h3 class="gallery-title">Captured Proofs (${this.gallery.captures.length})</h3>
                <div class="gallery-tools">
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
                    <div class="card gallery-empty">
                      <p class="empty-title">No capture artifacts found for ${this.selectedBundleId}</p>
                      <p class="empty-hint">Trigger a screenshot or video proof on the left.</p>
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
                                      <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
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
