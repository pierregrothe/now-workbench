// web/src/views/now-chat-view.ts
// Conversational Chat & Control Tower View with Otto AI and Generative UI tile layouts.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { ThreadController } from '../controllers/thread-controller.js';
import { workbenchStore } from '../context/workbench-context.js';
import { attachIcon, openArrowIcon, ottoGlyph, sendIcon, tapIcon } from '../icons.js';
import { renderAvatar } from '../profile/avatars.js';
import { bundlePanel, instancePanel } from './panel-items.js';
import type { PanelItem } from './panel-items.js';
import './now-item-panel.js';
import type { ChatMessage } from '../controllers/thread-controller.js';
import { workspaceStyles } from '../styles/workspace-styles.js';
import { chatViewStyles } from './chat-view-styles.js';
import '../tiles/now-tile-renderer.js';
import '../components/now-markdown.js';
import type { UITileSpec } from '../tiles/now-tile-renderer.js';
import { StoreController } from '../controllers/store-controller.js';
import './now-workspace-bar.js';
import './now-reply-feedback.js';

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

const SPARKLE = ottoGlyph(16);

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

  private readonly store = new StoreController(this);
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


  private async submitPrompt(overrideText?: string): Promise<void> {
    const text = (overrideText ?? this.chatInput).trim();
    if (!text && this.threadCtrl.pending.length === 0) return;

    this.chatInput = '';
    this.activeMode = 'thread';
    this.threadTitle = (text || 'Attached files').slice(0, 40);

    this.applyReply(await this.threadCtrl.sendMessage(text));
  }

  /**
   * Act on a reply that just arrived (never on reloaded history): follow Otto's interface
   * commands, and when Otto used tools, reload the shared lists so its changes show (ADR-026).
   */
  private applyReply(reply: ChatMessage | null): void {
    if (!reply) return;
    if (reply.tiles && reply.tiles.length > 0) {
      this.activeTiles = reply.tiles;
    }
    if (reply.steps && reply.steps.length > 0) {
      void workbenchStore.loadInstances();
      void workbenchStore.loadBundles();
      void workbenchStore.loadProfile();
      this.dispatchEvent(new CustomEvent('threads-refresh', { bubbles: true, composed: true }));
    }
    for (const cmd of reply.ui ?? []) {
      if (cmd.type === 'navigate') {
        this.dispatchEvent(
          new CustomEvent('nav-change', {
            detail: { tab: cmd.tab, section: cmd.section, action: cmd.action, args: cmd.args },
            bubbles: true,
            composed: true,
          })
        );
      }
    }
  }

  private handleKeyDown(e: KeyboardEvent): void {
    if (e.key === 'Enter') {
      void this.submitPrompt();
    }
  }


  private renderHomeTiles() {
    const { instances, selectedInstanceId, bundles } = this.store.state;
    const target = instances.find((i) => i.id === selectedInstanceId);
    const open = (label: string, onClick: () => void) =>
      html`<button type="button" class="open-btn" aria-label=${label} title=${label} @click=${onClick}>${openArrowIcon(14)}</button>`;
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
        ${this.threadCtrl.pending.length
          ? html`<div class="attach-chips">
              ${this.threadCtrl.pending.map(
                (a) => html`<span class="attach-chip">
                  ${a.filename} <span class="attach-size">${Math.max(1, Math.round(a.size_bytes / 1024))} KB</span>
                  <button aria-label="Remove ${a.filename}" @click=${() => void this.threadCtrl.detach(a.id)}>&times;</button>
                </span>`
              )}
            </div>`
          : ''}
        ${this.threadCtrl.attachError
          ? html`<div class="attach-error" role="alert">${this.threadCtrl.attachError}</div>`
          : ''}
        ${this.threadCtrl.usageWarning
          ? html`<div class="usage-warning" role="status">${this.threadCtrl.usageWarning}</div>`
          : ''}
        <div class="prompt-foot">
          <span class="prompt-foot-left">
            <button
              class="attach-btn"
              aria-label="Attach files"
              title="Attach PDFs, images or text files"
              ?disabled=${this.threadCtrl.isUploading}
              @click=${() => this.renderRoot.querySelector<HTMLInputElement>('#attach-input')?.click()}
            >
              ${attachIcon(18)}
            </button>
            <input
              id="attach-input"
              type="file"
              multiple
              hidden
              accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.md,.csv,.json,.log,.xml,.yaml,.yml"
              @change=${(e: Event) => {
                const input = e.target as HTMLInputElement;
                void this.threadCtrl.attach(Array.from(input.files ?? []));
                input.value = '';
              }}
            />
            ${this.threadCtrl.isUploading ? html`<span>Uploading...</span>` : ''}
            <span>${this.store.state.instances.find((i) => i.id === this.store.state.selectedInstanceId)?.name ?? 'No instance'}</span>
          </span>
          <button class="prompt-send-btn" aria-label="Send" @click=${() => void this.submitPrompt()}>
            ${sendIcon(16)}
          </button>
        </div>
      </div>
    `;
  }

  private renderTile(tile: UITileSpec, msgKey: string, isLastMessage: boolean, layout?: string) {
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
        .layout=${layout ?? 'auto'}
        @tile-action=${(e: CustomEvent) => this.handleTileAction(e, `${msgKey}:${tile.id}`)}
      ></now-tile-renderer>
    `;
  }

  private renderMessage(msg: ChatMessage, isLast: boolean, index: number) {
    const msgKey = msg.id ?? `idx-${index}`;
    const tiles =
      msg.tiles && msg.tiles.length > 0
        ? html`<div class="tiles-grid">
            ${msg.tiles.map((tile) => this.renderTile(tile, msgKey, isLast, msg.layout))}
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
        <div class="agent-head">${renderAvatar(this.store.state.profile, 24)}<span>${this.store.state.profile?.display_name || 'You'}</span><span class="when">${msg.timestamp}</span></div>
        <div style="white-space: pre-wrap;">${msg.text}</div>
      </div>`;
    }
    if (msg.sender === 'system') {
      return html`<div class="message-bubble system">${msg.text}</div>`;
    }
    return html`<div class="message-bubble agent">
      <div class="agent-head">${SPARKLE}<span>Otto</span><span class="when">${msg.timestamp}</span></div>
      ${steps}
      <now-markdown .text=${msg.text}></now-markdown>
      ${tiles}
      ${msg.id ? html`<now-reply-feedback .messageId=${msg.id} .rating=${msg.rating ?? null}></now-reply-feedback>` : ''}
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
    this.applyReply(result);
  }

  private handleTileAction(e: CustomEvent, decisionKey: string): void {
    const { actionId, props } = e.detail;
    if (actionId === 'open_item') {
      this.openItem =
        props?.kind === 'bundle'
          ? bundlePanel(props)
          : instancePanel(
              this.store.state.instances.find((i) => i.id === props?.instance_id) ?? {
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
    if (actionId === 'ask' && typeof props?.prompt === 'string') {
      // A follow-up Otto offered on a tile (ADR-025): ask it as the person's next message.
      void this.submitPrompt(props.prompt);
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
      <now-workspace-bar .crumb=${this.activeMode === 'overview' ? 'Home' : this.threadCtrl.title || this.threadTitle}>
        ${this.activeMode === 'thread'
          ? html`<button class="pill-btn" @click=${() => (this.activeMode = 'overview')}>&larr; Back to Home</button>`
          : ''}
        <button
          class="learn-more-pill"
          @click=${() => this.dispatchEvent(new CustomEvent('open-welcome', { bubbles: true, composed: true }))}
        >
          ${tapIcon(14)}<span>Learn more</span>
        </button>
      </now-workspace-bar>

      <div class="split">
      <div class="scroll-canvas">
        <div class="canvas-container">
          ${this.activeMode === 'overview'
            ? html`
                <div class="hero">
                  <h1 class="hero-title">${ottoGlyph(30)} ${greeting()}${this.store.state.profile?.display_name ? `, ${this.store.state.profile.display_name.split(' ')[0]}` : ''}!</h1>
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
