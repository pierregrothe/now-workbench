// web/src/views/now-chat-view.ts
// Conversational Chat & Control Tower View with Otto AI and Generative UI tile layouts.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { ThreadController } from '../controllers/thread-controller.js';
import { workbenchStore } from '../context/workbench-context.js';
import type { WorkbenchState } from '../context/workbench-context.js';
import { workspaceStyles } from '../styles/workspace-styles.js';
import '../tiles/now-tile-renderer.js';
import type { UITileSpec } from '../tiles/now-tile-renderer.js';

@customElement('now-chat-view')
export class NowChatView extends LitElement {
  private threadCtrl = new ThreadController(this);

  constructor() {
    super();
    this.threadCtrl.onThreadCreated = (threadId) => {
      this.dispatchEvent(
        new CustomEvent('thread-created', { detail: { threadId }, bubbles: true, composed: true })
      );
    };
  }
  private unsubscribeStore?: () => void;

  @state() private currentStoreState: WorkbenchState = workbenchStore.state;
  @state() private chatInput: string = '';
  @state() private activeMode: 'overview' | 'thread' = 'overview';
  @state() private threadTitle: string = 'Otto Assistant Conversation';
  @state() private activeTiles: UITileSpec[] = [];

  @property({ type: String })
  set activeThreadId(val: string) {
    if (val) {
      this.threadCtrl.setThread(val);
      this.activeMode = 'thread';
    }
  }

  @property({ type: String })
  set incomingPrompt(val: string) {
    if (val && val.trim()) {
      this.chatInput = val;
      void this.submitPrompt(val);
    }
  }

  static styles = [
    workspaceStyles,
    css`
      .hero-section {
        background: var(--now-bg-surface-0, #ffffff);
        border: 1px solid var(--now-border-subtle, #e5e7eb);
        border-radius: 12px;
        padding: 32px 28px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      }

      .hero-title {
        font-size: 20px;
        font-weight: 800;
        margin: 0 0 16px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        color: var(--now-text-primary, #111827);
      }

      .prompt-box {
        display: flex;
        align-items: center;
        background: var(--now-bg-surface-1, #f9fafb);
        border: 2px solid var(--now-border-subtle, #e5e7eb);
        border-radius: 9999px;
        padding: 4px 6px 4px 16px;
        gap: 8px;
        transition: border-color 0.15s ease;
      }

      .prompt-box:focus-within {
        border-color: var(--now-color-primary, #032d42);
        background: #ffffff;
      }

      .prompt-input {
        flex: 1;
        border: none;
        background: transparent;
        font-size: 14px;
        outline: none;
        color: var(--now-text-primary, #111827);
        font-family: inherit;
      }

      .prompt-send-btn {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: var(--now-color-primary, #032d42);
        color: #ffffff;
        border: none;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
      }

      .chips-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 14px;
      }

      .chip-btn {
        padding: 6px 12px;
        border-radius: 9999px;
        border: 1px solid var(--now-border-subtle, #e5e7eb);
        background: var(--now-bg-surface-0, #ffffff);
        font-size: 12px;
        font-weight: 500;
        color: var(--now-text-secondary, #4b5563);
        cursor: pointer;
        transition: all 0.15s ease;
      }

      .chip-btn:hover {
        background: var(--now-bg-surface-1, #f3f4f6);
        color: var(--now-text-primary, #111827);
      }

      .chat-thread-container {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-bottom: 24px;
      }

      .message-bubble {
        padding: 16px 20px;
        border-radius: 12px;
        max-width: 85%;
        font-size: 13.5px;
        line-height: 1.55;
      }

      .message-bubble.user {
        align-self: flex-end;
        background: var(--now-color-primary, #032d42);
        color: #ffffff;
      }

      .message-bubble.agent {
        align-self: flex-start;
        background: var(--now-bg-surface-0, #ffffff);
        border: 1px solid var(--now-border-subtle, #e5e7eb);
        color: var(--now-text-primary, #111827);
      }

      .tiles-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 16px;
        margin-top: 16px;
      }

      .dashboard-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 16px;
      }

      .dash-card {
        background: var(--now-bg-surface-0, #ffffff);
        border: 1px solid var(--now-border-subtle, #e5e7eb);
        border-radius: 8px;
        padding: 20px;
      }

      .dash-metric {
        font-size: 28px;
        font-weight: 800;
        margin: 8px 0;
        color: var(--now-text-primary, #111827);
      }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribeStore = workbenchStore.subscribe((state) => {
      this.currentStoreState = state;
    });
    workbenchStore.loadInstances();
    workbenchStore.loadBundles();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribeStore?.();
  }

  private async submitPrompt(overrideText?: string): Promise<void> {
    const text = (overrideText ?? this.chatInput).trim();
    if (!text) return;

    this.chatInput = '';
    this.activeMode = 'thread';
    this.threadTitle = text.slice(0, 40);

    const result = await this.threadCtrl.sendMessage(text);

    if (result?.tiles && result.tiles.length > 0) {
      this.activeTiles = result.tiles;
    }
  }

  private handleKeyDown(e: KeyboardEvent): void {
    if (e.key === 'Enter') {
      void this.submitPrompt();
    }
  }

  private handleInstanceChange(e: Event): void {
    const val = (e.target as HTMLSelectElement).value;
    workbenchStore.setState({ selectedInstanceId: val });
  }

  private async confirmTool(props: Record<string, any>): Promise<void> {
    const result = await this.threadCtrl.sendMessage(`Confirmed: ${props.plan ?? props.tool}`, {
      widget_type: 'tool_confirm',
      widget_data: { tool: props.tool, input: props.tool_input ?? {} },
    });
    if (result?.tiles && result.tiles.length > 0) {
      this.activeTiles = result.tiles;
    }
  }

  private handleTileAction(e: CustomEvent): void {
    const { actionId, props } = e.detail;
    if (actionId === 'probe' || actionId === 'probe_all') {
      void this.submitPrompt('Run full diagnostic health check on ServiceNow instances');
    } else if (actionId === 'confirm_tool') {
      void this.confirmTool(props);
    } else if (actionId === 'cancel_tool') {
      this.threadCtrl.addSystemNote('Action cancelled. Nothing was changed.');
    } else if (actionId === 'synthesize') {
      this.dispatchEvent(new CustomEvent('nav-change', { detail: { tab: 'synthesizer' }, bubbles: true, composed: true }));
    }
  }

  render() {
    return html`
      <div class="top-utility-bar">
        <div class="workspace-breadcrumb">
          <span class="status-dot"></span>
          <span>Now Workbench</span>
          <span style="color: #9ca3af;">/</span>
          <span>${this.activeMode === 'overview' ? 'Home' : this.threadTitle}</span>
        </div>
        <div class="utility-actions">
          <div class="instance-picker-pill">
            <span class="instance-picker-label">Target:</span>
            <select
              class="instance-picker-select"
              .value=${this.currentStoreState.selectedInstanceId}
              @change=${this.handleInstanceChange}
            >
              ${this.currentStoreState.instances.map(
                (inst) => html`<option value=${inst.id}>${inst.name} (${inst.release})</option>`
              )}
            </select>
          </div>
          ${this.activeMode === 'thread'
            ? html`<button class="pill-btn" @click=${() => (this.activeMode = 'overview')}>&larr; Back to Home</button>`
            : ''}
          <button class="pill-btn" @click=${() => this.dispatchEvent(new CustomEvent('open-welcome', { bubbles: true, composed: true }))}>
            Guide
          </button>
        </div>
      </div>

      <div class="scroll-canvas">
        <div class="canvas-container">
          <div class="hero-section">
            <h1 class="hero-title">
              <svg viewBox="0 0 24 24" style="width: 22px; height: 22px; fill: #16a34a;"><path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z"/></svg>
              <span>Hey Pierre, how can Otto help with your ServiceNow demos today?</span>
            </h1>

            <div class="prompt-box">
              <input
                class="prompt-input"
                type="text"
                placeholder="Ask Otto a question (e.g. 'How many instances do I have?' or 'Show demo recipe bundles')..."
                .value=${this.chatInput}
                @input=${(e: Event) => (this.chatInput = (e.target as HTMLInputElement).value)}
                @keydown=${this.handleKeyDown}
              />
              <button class="prompt-send-btn" @click=${() => void this.submitPrompt()}>
                <svg viewBox="0 0 24 24" style="width: 16px; height: 16px; fill: currentColor;"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
              </button>
            </div>

            <div class="chips-row">
              <button class="chip-btn" @click=${() => void this.submitPrompt('How many instances do I have?')}>
                How many instances do I have?
              </button>
              <button class="chip-btn" @click=${() => void this.submitPrompt('Show demo recipe bundles')}>
                Explore recipe bundles
              </button>
              <button class="chip-btn" @click=${() => void this.submitPrompt('Inspect ServiceNow Zurich Fluent SDK schema contracts')}>
                Inspect Fluent SDK schemas
              </button>
              <button class="chip-btn" @click=${() => void this.submitPrompt('Run full diagnostic health check')}>
                Run instance health check
              </button>
            </div>
          </div>

          ${this.activeMode === 'thread'
            ? html`
                <div class="chat-thread-container">
                  ${this.threadCtrl.messages.map(
                    (msg) => html`
                      <div class="message-bubble ${msg.sender}">
                        <div style="font-weight: 700; font-size: 11px; margin-bottom: 4px; opacity: 0.8;">
                          ${msg.sender === 'user' ? 'You' : 'Otto AI Copilot'} - ${msg.timestamp}
                        </div>
                        <div style="white-space: pre-wrap;">${msg.text}</div>

                        ${msg.tiles && msg.tiles.length > 0
                          ? html`
                              <div class="tiles-grid">
                                ${msg.tiles.map(
                                  (tile) => html`
                                    <now-tile-renderer
                                      .tile=${tile}
                                      @tile-action=${this.handleTileAction}
                                    ></now-tile-renderer>
                                  `
                                )}
                              </div>
                            `
                          : ''}
                      </div>
                    `
                  )}
                  ${this.threadCtrl.isStreaming
                    ? html`<div class="message-bubble agent">Otto is thinking and executing tools...</div>`
                    : ''}
                </div>
              `
            : html`
                <div class="dashboard-cards">
                  <div class="dash-card">
                    <span class="badge info">Active Target</span>
                    <div class="dash-metric">${this.currentStoreState.instances.length}</div>
                    <div style="font-size: 13px; font-weight: 600;">Managed Environments</div>
                    <p style="font-size: 12px; color: #6b7280; margin: 6px 0 0 0;">Configured target instances in local SQLite registry.</p>
                  </div>

                  <div class="dash-card">
                    <span class="badge success">Ready to Seed</span>
                    <div class="dash-metric">${this.currentStoreState.bundles.length || 2}</div>
                    <div style="font-size: 13px; font-weight: 600;">Demo Recipe Bundles</div>
                    <p style="font-size: 12px; color: #6b7280; margin: 6px 0 0 0;">Declarative Fluent SDK bundles with seed data.</p>
                  </div>

                  <div class="dash-card">
                    <span class="badge warning">Security & Tools</span>
                    <div class="dash-metric">100%</div>
                    <div style="font-size: 13px; font-weight: 600;">Local Sandbox Mode</div>
                    <p style="font-size: 12px; color: #6b7280; margin: 6px 0 0 0;">In-memory fakes, strict ratchets, zero cloud leaks.</p>
                  </div>
                </div>
              `}
        </div>
      </div>
    `;
  }
}
