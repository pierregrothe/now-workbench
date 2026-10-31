// web/src/modals/now-media-lightbox.ts
// Modal lightbox dialog for full-screen screenshot inspection and video proof playback.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { CaptureArtifact } from '../controllers/capture-gallery-controller.js';

@customElement('now-media-lightbox')
export class NowMediaLightbox extends LitElement {
  @property({ type: Object })
  artifact: CaptureArtifact | null = null;

  static styles = css`
    :host {
      display: block;
    }

    .lightbox-overlay {
      position: fixed;
      inset: 0;
      background: rgba(3, 45, 66, 0.75);
      backdrop-filter: blur(6px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      padding: 24px;
    }

    .lightbox-card {
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: var(--now-radius-lg, 12px);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.3);
      max-width: 980px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .lightbox-header {
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-1, #f8fafc);
    }

    .lightbox-title {
      font-weight: 700;
      font-size: 15px;
      color: var(--now-text-primary, #111827);
    }

    .lightbox-meta {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: var(--now-text-secondary, #6b7280);
      margin-top: 4px;
    }

    .media-badge {
      font-weight: 700;
      color: var(--now-color-brand-green, #62d84e);
      text-transform: uppercase;
    }

    .close-btn {
      border: 1px solid #cbd5e1;
      background: #ffffff;
      border-radius: 6px;
      padding: 4px 10px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      color: #475569;
    }

    .close-btn:hover {
      background: #f1f5f9;
    }

    .lightbox-body {
      padding: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0b1f30;
      overflow: auto;
      max-height: 65vh;
    }

    .lightbox-body img,
    .lightbox-body video {
      max-width: 100%;
      max-height: 60vh;
      border-radius: 6px;
      object-fit: contain;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }

    .lightbox-footer {
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-0, #ffffff);
      font-size: 12px;
    }

    .target-path {
      color: var(--now-text-secondary, #6b7280);
      font-family: monospace;
      font-size: 11px;
    }

    .actions {
      display: flex;
      gap: 10px;
      align-items: center;
    }

    .action-btn {
      display: inline-flex;
      align-items: center;
      padding: 4px 12px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      cursor: pointer;
      text-decoration: none;
      color: #334155;
    }

    .action-btn:hover {
      background: #f8fafc;
    }
  `;

  connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener('keydown', this.handleKeyDown);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this.handleKeyDown);
  }

  private handleKeyDown = (e: KeyboardEvent): void => {
    if (e.key === 'Escape') {
      this.close();
    }
  };

  private close(): void {
    this.dispatchEvent(new CustomEvent('close', { bubbles: true, composed: true }));
  }

  private handleRename(): void {
    if (!this.artifact) return;
    this.dispatchEvent(
      new CustomEvent('rename', {
        detail: { filename: this.artifact.filename, currentLabel: this.artifact.label },
        bubbles: true,
        composed: true,
      })
    );
  }

  private formatDate(isoString?: string): string {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  }

  render() {
    if (!this.artifact) return '';
    const cap = this.artifact;

    return html`
      <div
        class="lightbox-overlay"
        @click=${(e: Event) => {
          if (e.target === e.currentTarget) this.close();
        }}
      >
        <div class="lightbox-card" role="dialog" aria-modal="true">
          <div class="lightbox-header">
            <div>
              <div class="lightbox-title">${cap.label || cap.filename}</div>
              <div class="lightbox-meta">
                <span class="media-badge">${cap.media_type}</span>
                <span>|</span>
                <span>${this.formatDate(cap.created_at)}</span>
                <span>|</span>
                <span>${cap.engine}</span>
              </div>
            </div>
            <button class="close-btn" @click=${this.close} title="Close viewer">X</button>
          </div>

          <div class="lightbox-body">
            ${cap.media_type === 'video'
              ? html`
                  <video
                    src=${cap.url}
                    controls
                    autoplay
                    playsinline
                  ></video>
                `
              : html`
                  <img
                    src=${cap.url}
                    alt=${cap.label || cap.filename}
                  />
                `}
          </div>

          <div class="lightbox-footer">
            <div class="target-path">${cap.target_path}</div>
            <div class="actions">
              <a
                class="action-btn"
                style="color: #2563eb;"
                href=${cap.url}
                target="_blank"
                rel="noopener"
              >
                Open in New Tab
              </a>
              <button
                class="action-btn"
                style="color: #4338ca; border-color: #c7d2fe;"
                @click=${this.handleRename}
              >
                Rename
              </button>
              <a
                class="action-btn"
                style="color: var(--now-color-brand-green, #62d84e);"
                href=${cap.url}
                download=${cap.filename}
              >
                Download
              </a>
              <button class="action-btn" @click=${this.close}>Close</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
