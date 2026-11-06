// web/src/views/now-chat-view.ts
// Conversational Chat & Control Tower View with Otto AI and Generative UI tile layouts.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { ThreadController } from '../controllers/thread-controller.js';
import { workbenchStore } from '../context/workbench-context.js';
import type { WorkbenchState } from '../context/workbench-context.js';
import { renderAvatar } from '../profile/avatars.js';
import { bundlePanel, instancePanel } from './panel-items.js';
import type { PanelItem } from './panel-items.js';
import './now-item-panel.js';
import type { ChatMessage } from '../controllers/thread-controller.js';
import { workspaceStyles } from '../styles/workspace-styles.js';
import { chatViewStyles } from './chat-view-styles.js';
import '../tiles/now-tile-renderer.js';
import type { UITileSpec } from '../tiles/now-tile-renderer.js';

/** Time-of-day greeting, like the Otto home screen. */
const greeting = (): string => {
  const hour = new Date().getHours();
  return hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
};

/** Tile actions that ask Otto something. */
const TILE_PROMPTS: Record<string, (name: string) => string> = {
  probe: (name) => `Check authentication for ${name}`,
  probe_all: () => 'Run full diagnostic health check on ServiceNow instances',
  show_instances: () => 'How many instances do I have?',
  show_bundles: () => 'Show demo recipe bundles',
  activate: (name) => `Make ${name} my default instance`,
};

/** Tile actions that open another workbench area (destructive work is confirmed there). */
const TILE_NAV: Record<string, string> = {
  synthesize: 'synthesizer',
  inspect: 'fluent',
  manage: 'admin',
  delete_instance: 'admin',
  delete_unauthenticated: 'admin',
};

const SPARKLE = html`<svg viewBox="0 0 24 24" style="width: 16px; height: 16px; fill: #16a34a;"><path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z"/></svg>`;

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
  /** Approval cards decided in this session, keyed by message key and tile id. */
  @state() private decisions: Record<string, 'confirmed' | 'cancelled'> = {};
  private lastMessageCount = 0;
  @state() private openItem: PanelItem | null = null;
  @state() private hasClaudeKey: boolean | null = null;

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

  static styles = [workspaceStyles, chatViewStyles];

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribeStore = workbenchStore.subscribe((state) => {
      this.currentStoreState = state;
    });
    workbenchStore.loadInstances();
    workbenchStore.loadBundles();
    void this.loadKeyState();
  }

  private async loadKeyState(): Promise<void> {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        this.hasClaudeKey = Boolean((await res.json()).has_anthropic_api_key);
      }
    } catch {
      this.hasClaudeKey = null;
    }
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

  private renderHomeTiles() {
    const { instances, selectedInstanceId, bundles } = this.currentStoreState;
    const target = instances.find((i) => i.id === selectedInstanceId);
    const open = (label: string, onClick: () => void) =>
      html`<button type="button" class="open-btn" aria-label=${label} title=${label} @click=${onClick}>&#8599;</button>`;
    const nav = (tab: string) => () =>
      this.dispatchEvent(new CustomEvent('nav-change', { detail: { tab }, bubbles: true, composed: true }));
    return html`
      <div class="dash-card">
        <div class="dash-head"><span>Target instance</span>${target ? open('Open instance details', () => (this.openItem = instancePanel(target))) : ''}</div>
        ${target
          ? html`<div class="dash-metric">${target.name}</div>
              <p class="dash-sub">${[target.release, target.status].filter(Boolean).join(' - ')}</p>`
          : html`<div class="dash-metric">None yet</div>
              <p class="dash-sub">Register an instance so Otto can work against it.</p>
              <button type="button" class="chip-btn" @click=${nav('admin')}>Add an instance</button>`}
      </div>
      <div class="dash-card">
        <div class="dash-head"><span>Demo bundles</span>${open('Open Artifact library', nav('artifacts'))}</div>
        <div class="dash-metric">${bundles.length}</div>
        <p class="dash-sub">${bundles.slice(0, 3).map((b) => b.name).join(', ') || 'No bundles yet'}</p>
      </div>
      ${this.hasClaudeKey === null
        ? ''
        : html`<div class="dash-card">
            <div class="dash-head"><span>Claude</span>${open('Open settings', nav('admin'))}</div>
            <div class="dash-metric">${this.hasClaudeKey ? 'Connected' : 'No API key'}</div>
            <p class="dash-sub">${this.hasClaudeKey ? 'Otto answers with Claude.' : 'Add a key in Settings to enable Otto.'}</p>
          </div>`}
    `;
  }

  private renderPrompt() {
    return html`
      <div class="prompt-box">
        <input
          class="prompt-input"
          type="text"
          placeholder="Find answers, automate tasks, or create content instantly"
          .value=${this.chatInput}
          @input=${(e: Event) => (this.chatInput = (e.target as HTMLInputElement).value)}
          @keydown=${this.handleKeyDown}
        />
        <div class="prompt-foot">
          <span>${this.currentStoreState.instances.find((i) => i.id === this.currentStoreState.selectedInstanceId)?.name ?? 'No instance'}</span>
          <button class="prompt-send-btn" aria-label="Send" @click=${() => void this.submitPrompt()}>
            <svg viewBox="0 0 24 24" style="width: 16px; height: 16px; fill: currentColor;"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>
      </div>
    `;
  }

  private renderTile(tile: UITileSpec, msgKey: string, isLastMessage: boolean) {
    const isApproval = tile.id.startsWith('tile-confirm-');
    if (isApproval) {
      const decisionKey = `${msgKey}:${tile.id}`;
      const decision = this.decisions[decisionKey];
      if (decision || !isLastMessage) {
        const cancelled = decision === 'cancelled';
        return html`
          <div class="outcome-card ${cancelled ? 'cancelled' : ''}">
            <span class="mark">${cancelled ? '-' : '\u2713'}</span>
            <div>
              <div class="outcome-title">
                ${decision === 'confirmed' ? 'Approved' : cancelled ? 'Cancelled' : 'Already handled'}
              </div>
              <div class="outcome-body">${(tile.props as any)?.body ?? tile.title}</div>
            </div>
          </div>
        `;
      }
    }
    return html`
      <now-tile-renderer
        .tile=${tile}
        @tile-action=${(e: CustomEvent) => this.handleTileAction(e, `${msgKey}:${tile.id}`)}
      ></now-tile-renderer>
    `;
  }

  private renderMessage(msg: ChatMessage, isLast: boolean, index: number) {
    const msgKey = msg.id ?? `idx-${index}`;
    const tiles =
      msg.tiles && msg.tiles.length > 0
        ? html`<div class="tiles-grid">
            ${msg.tiles.map((tile) => this.renderTile(tile, msgKey, isLast))}
          </div>`
        : '';
    const stepList = msg.steps ?? [];
    const steps =
      stepList.length > 0
        ? html`<details class="steps">
            <summary>Thought for a moment \u00b7 ${stepList.length} ${stepList.length === 1 ? 'step' : 'steps'}</summary>
            <ul>
              ${stepList.map(
                (st) => html`<li class=${st.ok ? 'done' : 'failed'}>${st.ok ? '\u2713' : '\u2717'} ${st.label}</li>`
              )}
            </ul>
          </details>`
        : '';
    if (msg.sender === 'user') {
      return html`<div class="message-bubble user">
        <div class="agent-head">${renderAvatar(this.currentStoreState.profile, 24)}<span>${this.currentStoreState.profile?.display_name || 'You'}</span><span class="when">${msg.timestamp}</span></div>
        <div style="white-space: pre-wrap;">${msg.text}</div>
      </div>`;
    }
    if (msg.sender === 'system') {
      return html`<div class="message-bubble system">${msg.text}</div>`;
    }
    return html`<div class="message-bubble agent">
      <div class="agent-head">${SPARKLE}<span>Otto</span><span class="when">${msg.timestamp}</span></div>
      ${steps}
      <div style="white-space: pre-wrap;">${msg.text}</div>
      ${tiles}
    </div>`;
  }

  updated(): void {
    const count = this.threadCtrl.messages.length;
    if (count !== this.lastMessageCount) {
      this.lastMessageCount = count;
      this.renderRoot.querySelector('#thread-end')?.scrollIntoView({ block: 'end', behavior: 'smooth' });
    }
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

  private handleTileAction(e: CustomEvent, decisionKey: string): void {
    const { actionId, props } = e.detail;
    if (actionId === 'open_item') {
      this.openItem =
        props?.kind === 'bundle'
          ? bundlePanel(props)
          : instancePanel(
              this.currentStoreState.instances.find((i) => i.id === props?.instance_id) ?? {
                id: String(props?.instance_id ?? ''),
                name: String(props?.name ?? 'Instance'),
                url: String(props?.url ?? ''),
                username: '',
                release: String(props?.release ?? ''),
                is_default: Boolean(props?.is_default),
                status: String(props?.status ?? ''),
                last_checked: null,
              }
            );
      return;
    }
    const name = props?.name ?? props?.title ?? 'this instance';
    const prompt = TILE_PROMPTS[actionId]?.(name);
    const tab = TILE_NAV[actionId];
    if (prompt) {
      void this.submitPrompt(prompt);
    } else if (tab) {
      this.dispatchEvent(new CustomEvent('nav-change', { detail: { tab }, bubbles: true, composed: true }));
    } else if (actionId === 'confirm_tool') {
      this.decisions = { ...this.decisions, [decisionKey]: 'confirmed' };
      void this.confirmTool(props);
    } else if (actionId === 'cancel_tool') {
      this.decisions = { ...this.decisions, [decisionKey]: 'cancelled' };
      this.threadCtrl.addSystemNote('Action cancelled. Nothing was changed.');
    }
  }

  render() {
    return html`
      <div class="top-utility-bar">
        <div class="workspace-breadcrumb">
          <span class="status-dot"></span>
          <span>Now Workbench</span>
          <span style="color: #9ca3af;">/</span>
          <span>${this.activeMode === 'overview' ? 'Home' : this.threadCtrl.title || this.threadTitle}</span>
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

      <div class="split">
      <div class="scroll-canvas">
        <div class="canvas-container">
          ${this.activeMode === 'overview'
            ? html`
                <div class="hero">
                  <h1 class="hero-title">${greeting()}${this.currentStoreState.profile?.display_name ? `, ${this.currentStoreState.profile.display_name.split(' ')[0]}` : ''}!</h1>
                  ${this.renderPrompt()}
                  <div class="chips-row">
                    <button class="chip-btn" @click=${() => void this.submitPrompt('How many instances do I have?')}>How many instances do I have?</button>
                    <button class="chip-btn" @click=${() => void this.submitPrompt('Show demo recipe bundles')}>Explore recipe bundles</button>
                    <button class="chip-btn" @click=${() => void this.submitPrompt('Inspect the Fluent SDK schema contracts')}>Inspect Fluent SDK schemas</button>
                    <button class="chip-btn" @click=${() => void this.submitPrompt('Run full diagnostic health check')}>Run instance health check</button>
                  </div>
                </div>
              `
            : ''}

          ${this.activeMode === 'thread'
            ? html`
                <div class="chat-thread-container">
                  ${this.threadCtrl.messages.map((msg, index) =>
                    this.renderMessage(msg, index === this.threadCtrl.messages.length - 1, index)
                  )}
                  ${this.threadCtrl.isStreaming
                    ? html`<div class="message-bubble agent"><div class="agent-head">${SPARKLE}<span>Otto</span><span class="when">is working...</span></div></div>`
                    : ''}
                  <div id="thread-end"></div>
                </div>
                <div class="dock">
                  ${this.renderPrompt()}
                  <div class="ai-footnote">Some answers are generated by AI. Check them for accuracy.</div>
                </div>
              `
            : html`
                <div class="dashboard-cards">${this.renderHomeTiles()}</div>
              `}
        </div>
      </div>
      ${this.openItem
        ? html`<now-item-panel
        .item=${this.openItem}
        @panel-close=${() => (this.openItem = null)}
        @panel-action=${(e: CustomEvent<string>) => {
          this.openItem = null;
          this.dispatchEvent(new CustomEvent('nav-change', { detail: { tab: e.detail }, bubbles: true, composed: true }));
        }}
      ></now-item-panel>`
        : ''}
      </div>
    `;
  }
}
