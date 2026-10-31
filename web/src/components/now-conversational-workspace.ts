// web/src/components/now-conversational-workspace.ts
// Modular conversational workspace dispatcher (ADR-010).
// Delegates to now-chat-view, now-synthesizer-view, and now-capture-studio.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import '../views/now-chat-view.js';
import '../views/now-synthesizer-view.js';
import '../views/now-capture-studio.js';
import type { UITileSpec, GenerativeUIResponse } from '../tiles/now-tile-renderer.js';

export type { UITileSpec, GenerativeUIResponse };

@customElement('now-conversational-workspace')
export class NowConversationalWorkspace extends LitElement {
  @property({ type: String }) viewMode: 'home' | 'synthesizer' | 'capture' = 'home';
  @property({ type: String }) activeThreadId = '';
  @property({ type: String }) incomingPrompt = '';

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background-color: var(--now-bg-canvas, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      overflow: hidden;
    }

    .view-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      width: 100%;
    }
  `;

  render() {
    return html`
      <div class="view-container">
        ${this.viewMode === 'synthesizer'
          ? html`
              <now-synthesizer-view
                .incomingPrompt=${this.incomingPrompt}
                @nav-change=${this.handleBubble}
                @open-welcome=${this.handleBubble}
                @open-walkthrough=${this.handleBubble}
              ></now-synthesizer-view>
            `
          : this.viewMode === 'capture'
          ? html`
              <now-capture-studio
                .incomingPrompt=${this.incomingPrompt}
                @nav-change=${this.handleBubble}
                @open-welcome=${this.handleBubble}
                @open-walkthrough=${this.handleBubble}
              ></now-capture-studio>
            `
          : html`
              <now-chat-view
                .activeThreadId=${this.activeThreadId}
                .incomingPrompt=${this.incomingPrompt}
                @nav-change=${this.handleBubble}
                @open-welcome=${this.handleBubble}
                @open-walkthrough=${this.handleBubble}
                @open-otto=${this.handleBubble}
                @intent-submit=${this.handleBubble}
                @thread-created=${this.handleBubble}
                @threads-refresh=${this.handleBubble}
                @collapse-rail=${this.handleBubble}
              ></now-chat-view>
            `}
      </div>
    `;
  }

  private handleBubble(e: Event): void {
    // Re-dispatch if not already composed/bubbling
    if (!e.bubbles) {
      this.dispatchEvent(new CustomEvent(e.type, { detail: (e as any).detail, bubbles: true, composed: true }));
    }
  }
}
