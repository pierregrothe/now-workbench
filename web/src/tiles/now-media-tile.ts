// web/src/tiles/now-media-tile.ts
// Reusable media player & screenshot tile component.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('now-media-tile')
export class NowMediaTile extends LitElement {
  @property({ type: String }) title: string = '';
  @property({ type: String }) url: string = '';
  @property({ type: String }) mediaType: 'screenshot' | 'video' = 'screenshot';
  @property({ type: String }) label: string = '';
  @property({ type: Array }) actions: Array<{ id: string; label: string; variant?: string }> = [];

  static styles = css`
    :host {
      display: block;
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .media-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e5e7eb);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .title {
      font-size: 14px;
      font-weight: 700;
      color: var(--now-text-primary, #16181d);
      margin: 0;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      background: #ecfdf5;
      color: #047857;
      text-transform: uppercase;
    }

    .label {
      font-size: 12px;
      color: var(--now-text-secondary, #6b7280);
    }

    .preview-container {
      background: #0f172a;
      border-radius: 6px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 180px;
      max-height: 280px;
      cursor: pointer;
    }

    video, img {
      max-width: 100%;
      max-height: 280px;
      object-fit: contain;
    }

    .actions-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 4px;
    }

    .action-btn {
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid var(--now-border-subtle, #cbd5e1);
      background: #ffffff;
      color: #334155;
      cursor: pointer;
    }

    .action-btn.primary {
      background: var(--now-color-primary, #032d42);
      color: #ffffff;
      border-color: var(--now-color-primary, #032d42);
    }
  `;

  private handleAction(actionId: string): void {
    this.dispatchEvent(
      new CustomEvent('tile-action', {
        detail: { actionId, url: this.url, mediaType: this.mediaType },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleMediaClick(): void {
    this.dispatchEvent(
      new CustomEvent('media-click', {
        detail: { url: this.url, mediaType: this.mediaType, label: this.label, title: this.title },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    const isVideo = this.mediaType === 'video' || this.url.endsWith('.webm') || this.url.endsWith('.mp4');

    return html`
      <div class="media-card">
        <div class="header-row">
          <h4 class="title">${this.title || 'Demonstration Media'}</h4>
          <span class="badge">${isVideo ? 'Video Proof' : 'Screenshot'}</span>
        </div>
        ${this.label ? html`<div class="label">${this.label}</div>` : ''}
        <div class="preview-container" @click=${this.handleMediaClick}>
          ${isVideo
            ? html`<video src=${this.url} controls playsinline preload="metadata"></video>`
            : html`<img src=${this.url} alt=${this.title || 'Demonstration Proof'} />`}
        </div>
        ${this.actions.length > 0
          ? html`
              <div class="actions-row">
                ${this.actions.map(
                  (act) => html`
                    <button
                      class="action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      @click=${() => this.handleAction(act.id)}
                    >
                      ${act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }
}
