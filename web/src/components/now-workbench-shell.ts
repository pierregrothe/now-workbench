import { sendIcon } from '../icons.js';
import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import '../views/now-access-gate.js';
import type { GateMode } from '../views/now-access-gate.js';
import './now-nav-rail.js';
import type { NavThreadItem } from './now-nav-rail.js';
import './now-conversational-workspace.js';
import './now-demo-catalog.js';
import './now-fluent-explorer.js';
import './now-workbench-settings.js';
import type { WorkbenchPreferences } from './now-workbench-settings.js';
import './now-presenter-hud.js';
import './now-welcome-modal.js';
import '../views/now-impersonation.js';
import './now-command-palette.js';
import { smartTooltip } from '../utils/tooltip.js';
import { workbenchStore } from '../context/workbench-context.js';

interface DetectedIntent {
  tab: string;
  menuLabel: string;
  explanation: string;
  isQuestion?: boolean;
}

const VALID_SHELL_TABS = new Set([
  'home',
  'artifacts',
  'synthesizer',
  'capture',
  'fluent',
  'admin',
]);

function resolveInitialTab(): string {
  if (typeof window !== 'undefined') {
    const rawHash = window.location.hash.replace(/^#\/?/, '').trim();
    if (VALID_SHELL_TABS.has(rawHash)) {
      return rawHash;
    }
    try {
      const stored = localStorage.getItem('now-workbench-active-tab');
      if (stored && VALID_SHELL_TABS.has(stored)) {
        return stored;
      }
    } catch {}
  }
  return 'home';
}

@customElement('now-workbench-shell')
export class NowWorkbenchShell extends LitElement {
  static styles = css`
    :host {
      display: flex;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
      background-color: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .content-area {
      flex: 1;
      height: 100vh;
      overflow: hidden;
      position: relative;
      display: flex;
      flex-direction: column;
      background: var(--now-bg-canvas, #ffffff);
    }

    .thread-error-banner {
      padding: 8px 16px;
      background: #fdecea;
      color: #b3261e;
      font-size: 13px;
    }

    .active-view-stage {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    /* Docked Bottom Chat Bar (shown whenever activeTab !== 'home') */
    .bottom-chat-dock {
      flex-shrink: 0;
      padding: 10px 36px 14px 36px;
      background: var(--otto-canvas, #efece7);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      z-index: 20;
    }

    .intent-route-caption {
      width: 100%;
      max-width: 768px;
      font-size: 11.5px;
      color: var(--now-text-secondary, #6b7280);
      text-align: center;
    }

    .bottom-prompt-box {
      width: calc(100% - 16px);
      max-width: 752px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #ffffff;
      border-radius: 32px;
      padding: 18px 14px 12px 24px;
      margin: 8px 0 4px;
      box-sizing: border-box;
      box-shadow:
        0 0 0 8px #f4f3f0,
        0 0 8px 8px rgba(0, 0, 0, 0.05),
        0 20px 25px 3px rgba(0, 0, 0, 0.1);
    }

    .bottom-prompt-box input {
      border: none;
      background: transparent;
      font-family: inherit;
      font-size: 16px;
      line-height: 24px;
      color: var(--now-text-primary, #16181d);
      outline: none;
    }

    .bottom-prompt-foot {
      display: flex;
      justify-content: flex-end;
    }

    .bottom-send-btn {
      position: relative;
      appearance: none;
      border: none;
      background: #c9f0c1;
      color: #4b5f4b;
      width: 36px;
      height: 36px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      cursor: pointer;
      transition: background 0.12s ease, transform 0.1s ease;
    }

    .bottom-send-btn:hover {
      opacity: 0.9;
      transform: scale(1.05);
    }

    .bottom-send-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }
  `;

  @state() private activeTab = resolveInitialTab();
  @state() private activeThreadId = '';
  @state() private selectedBundleId = 'sample-ai-assistant';
  @state() private welcomeModalOpen =
    typeof localStorage !== 'undefined'
      ? localStorage.getItem('now-workbench-show-welcome') !== 'false'
      : true;
  @state() private autoRouteIntent = true;
  @state() private railCollapsed = false;

  private setActiveTab(tab: string): void {
    const target = VALID_SHELL_TABS.has(tab) ? tab : 'home';
    this.activeTab = target;
    workbenchStore.setState({ activeTab: target });
    if (typeof window !== 'undefined') {
      if (window.location.hash !== `#${target}`) {
        window.location.hash = `#${target}`;
      }
      try {
        localStorage.setItem('now-workbench-active-tab', target);
      } catch {}
    }
  }

  private handleWindowHashChange = (): void => {
    const rawHash = window.location.hash.replace(/^#\/?/, '').trim();
    if (VALID_SHELL_TABS.has(rawHash) && rawHash !== this.activeTab) {
      this.activeTab = rawHash;
      try {
        localStorage.setItem('now-workbench-active-tab', rawHash);
      } catch {}
    }
  };

  connectedCallback(): void {
    super.connectedCallback();
    void this.checkAccess();
    smartTooltip.init();
    if (typeof window !== 'undefined') {
      window.addEventListener('hashchange', this.handleWindowHashChange);
      if (!window.location.hash && this.activeTab) {
        window.location.hash = `#${this.activeTab}`;
      }
    }
    void this.loadInitialPreferences();
    void this.loadThreads();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (typeof window !== 'undefined') {
      window.removeEventListener('hashchange', this.handleWindowHashChange);
    }
  }

  private async loadThreads(): Promise<void> {
    try {
      const res = await fetch('/api/threads?include_archived=true');
      if (res.ok) {
        const list = (await res.json()) as Array<{
          id: string;
          title: string;
          archived?: boolean;
          target_tab?: string;
          tokens_used?: number;
          max_tokens?: number;
        }>;
        this.recentThreads = list.map((t) => ({
          id: t.id,
          title: t.title,
          targetTab: t.target_tab || 'home',
          archived: Boolean(t.archived),
          tokensUsed: t.tokens_used ?? 0,
          maxTokens: t.max_tokens ?? 2000000,
        }));
      }
    } catch {
      // Offline preview keeps existing threads
    }
  }

  private async loadInitialPreferences(): Promise<void> {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const prefs = (await res.json()) as WorkbenchPreferences;
        const storedShowWelcome = localStorage.getItem('now-workbench-show-welcome');
        if (storedShowWelcome !== null) {
          this.welcomeModalOpen = storedShowWelcome !== 'false';
        } else {
          this.welcomeModalOpen = prefs.show_welcome_on_startup;
        }
        this.autoRouteIntent = prefs.auto_route_intent;
      }
    } catch {
      // Offline preview keeps the defaults
    }
  }
  @state() private presenterHudVisible = false;
  @state() private bottomChatInput = '';
  @state() private routedPrompt = '';
  @state() private lastIntentExplanation =
    'AI Intent Router active. Describe an action below to switch menus or update the current workspace.';

  @state() private recentThreads: NavThreadItem[] = [];
  @state() private threadError = '';

  private detectIntentFromPrompt(prompt: string): DetectedIntent {
    const lower = prompt.toLowerCase().trim();

    // 1. Informational Questions & Conversational Otto Sessions
    const isQuestion =
      lower.endsWith('?') ||
      lower.startsWith('what') ||
      lower.startsWith('how') ||
      lower.startsWith('why') ||
      lower.startsWith('where') ||
      lower.startsWith('who') ||
      lower.startsWith('when') ||
      lower.startsWith('which') ||
      lower.startsWith('can ') ||
      lower.startsWith('could ') ||
      lower.startsWith('would ') ||
      lower.startsWith('tell me') ||
      lower.startsWith('explain') ||
      lower.startsWith('describe') ||
      lower.startsWith('help') ||
      lower.startsWith('is ') ||
      lower.startsWith('are ') ||
      lower.startsWith('does ') ||
      lower.startsWith('do ') ||
      lower.startsWith('show ') ||
      lower.startsWith('review ') ||
      lower.startsWith('investigate') ||
      lower.includes('what is') ||
      lower.includes('what are') ||
      lower.includes('how do') ||
      lower.includes('how can') ||
      lower.includes('how to') ||
      lower.includes('tell me about') ||
      lower.includes('instande') ||
      lower.includes('recipe') ||
      lower.includes('update set') ||
      lower.includes('demohub');

    if (isQuestion) {
      return {
        tab: 'home',
        menuLabel: 'Otto AI Copilot',
        explanation: 'Conversational question -> Answered by Otto AI Copilot',
        isQuestion: true,
      };
    }

    // 2. Explicit Navigation Commands to Settings
    const isExplicitSettings =
      (lower.startsWith('go to') ||
        lower.startsWith('open') ||
        lower.startsWith('navigate to') ||
        lower === 'settings' ||
        lower === 'admin') &&
      (lower.includes('setting') ||
        lower.includes('admin') ||
        lower.includes('config') ||
        lower.includes('instance') ||
        lower.includes('preference'));

    if (isExplicitSettings) {
      return {
        tab: 'admin',
        menuLabel: 'Instance Settings',
        explanation: 'Explicit navigation -> Opening Workbench Settings',
      };
    }

    // 3. Media Capture Intent
    if (
      lower.includes('screenshot') ||
      lower.includes('video') ||
      lower.includes('capture') ||
      lower.includes('.webm') ||
      lower.includes('.png') ||
      lower.includes('record')
    ) {
      return {
        tab: 'capture',
        menuLabel: 'Media Capture',
        explanation: `Detected media capture intent -> Routed to Media Capture for "${prompt.slice(0, 64)}"`,
      };
    }

    // 4. Fluent SDK Schema Intent
    if (
      lower.includes('fluent') ||
      lower.includes('schema') ||
      lower.includes('.now.ts') ||
      lower.includes('diff') ||
      lower.includes('column')
    ) {
      return {
        tab: 'fluent',
        menuLabel: 'Fluent SDK Explorer',
        explanation: 'Detected Fluent schema intent -> Routed to Fluent SDK Explorer',
      };
    }

    // 5. Artifact Library / Demo Catalog Intent
    if (
      lower.includes('catalog') ||
      lower.includes('artifact') ||
      lower.includes('library') ||
      lower.includes('rollback') ||
      lower.includes('unseed')
    ) {
      return {
        tab: 'artifacts',
        menuLabel: 'Artifact Library',
        explanation: 'Detected bundle catalog intent -> Routed to Artifact Library',
      };
    }

    // 6. Default to Use-Case Synthesis
    return {
      tab: 'synthesizer',
      menuLabel: 'Use-Case Synthesizer',
      explanation: 'Detected use-case demo synthesis intent -> Routed to Use-Case Synthesizer & SC Narrative Studio',
    };
  }

  private async handleIntentPrompt(prompt: string, stayInOtto = false): Promise<void> {
    const clean = prompt.trim();
    if (!clean) {
      return;
    }
    const detected = this.detectIntentFromPrompt(clean);
    const targetTab = stayInOtto || detected.isQuestion ? 'home' : detected.tab;
    const shortTitle = clean.length > 38 ? `${clean.slice(0, 38)}...` : clean;

    this.lastIntentExplanation = detected.explanation;

    if (stayInOtto || detected.isQuestion) {
      await this.startOttoThread(shortTitle, clean);
      return;
    }

    this.routedPrompt = clean;
    if (this.autoRouteIntent) {
      this.setActiveTab(targetTab);
    }
  }

  private handleBottomChatSubmit(): void {
    if (!this.bottomChatInput.trim()) {
      return;
    }
    const text = this.bottomChatInput;
    this.bottomChatInput = '';
    void this.handleIntentPrompt(text);
  }

  private handleNavChange(e: CustomEvent<{ tab: string }>): void {
    const tab = e.detail.tab;
    if (tab === 'help') {
      this.welcomeModalOpen = true;
      return;
    }
    this.setActiveTab(tab);
    if (tab === 'home') {
      this.activeThreadId = '';
      this.routedPrompt = '';
      this.railCollapsed = false;
    }
  }

  private handleThreadSelect(e: CustomEvent<{ thread: NavThreadItem }>): void {
    const thread = e.detail.thread;
    this.activeThreadId = thread.id;
    this.setActiveTab('home');
    this.routedPrompt = thread.prompt ?? '';
    this.lastIntentExplanation = `Opened conversation "${thread.title}"`;
  }

  private async requestThreadApi(
    action: string,
    url: string,
    init: RequestInit
  ): Promise<Response | null> {
    try {
      const res = await fetch(url, init);
      if (res.ok) {
        this.threadError = '';
        return res;
      }
      this.threadError = `Could not ${action}: HTTP ${res.status}`;
    } catch (err) {
      this.threadError = `Could not ${action}: ${err instanceof Error ? err.message : String(err)}`;
    }
    return null;
  }

  private async startOttoThread(title: string, firstMessage?: string): Promise<void> {
    const createRes = await this.requestThreadApi('create conversation', '/api/threads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, target_tab: 'home' }),
    });
    if (!createRes) {
      return;
    }
    const created = (await createRes.json()) as { id: string; title: string };
    if (firstMessage !== undefined) {
      const msgRes = await this.requestThreadApi(
        'send message',
        `/api/threads/${created.id}/messages`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: firstMessage, role: 'user' }),
        }
      );
      if (!msgRes) {
        await this.loadThreads();
        return;
      }
    }
    await this.loadThreads();
    this.activeThreadId = created.id;
    this.setActiveTab('home');
  }

  private async handleNewSession(): Promise<void> {
    this.routedPrompt = '';
    this.setActiveTab('home');
    this.railCollapsed = false;
    await this.startOttoThread('New Otto Conversation');
  }

  private async handleThreadArchive(
    e: CustomEvent<{ threadId: string; archived: boolean }>
  ): Promise<void> {
    const { threadId, archived } = e.detail;
    const res = await this.requestThreadApi(
      archived ? 'archive conversation' : 'unarchive conversation',
      `/api/threads/${threadId}`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archived }),
      }
    );
    if (!res) {
      return;
    }
    await this.loadThreads();
  }

  private async handleThreadDelete(e: CustomEvent<{ threadId: string }>): Promise<void> {
    const { threadId } = e.detail;
    const res = await this.requestThreadApi('delete conversation', `/api/threads/${threadId}`, {
      method: 'DELETE',
    });
    if (!res) {
      return;
    }
    if (this.activeThreadId === threadId) {
      this.activeThreadId = '';
      this.routedPrompt = '';
    }
    await this.loadThreads();
  }

  private handleOpenWalkthrough(e: CustomEvent<{ bundleId: string }>): void {
    this.selectedBundleId = e.detail.bundleId;
    this.presenterHudVisible = true;
  }

  private handlePaletteCommand(e: CustomEvent<{ command: string; title: string }>): void {
    const cmd = e.detail.command;
    switch (cmd) {
      case 'presenter-mode':
        this.presenterHudVisible = true;
        break;
      case 'open-studio':
        this.setActiveTab('fluent');
        break;
      case 'inspect-properties':
      case 'export-demo':
      case 'view-artifacts':
      case 'reset-demo':
        this.setActiveTab('artifacts');
        break;
      case 'open-admin':
        this.setActiveTab('admin');
        break;
      case 'open-synthesizer':
        this.setActiveTab('synthesizer');
        break;
      case 'open-capture':
        this.setActiveTab('capture');
        break;
      case 'open-otto':
        this.setActiveTab('home');
        break;
    }
  }

  private renderActiveView() {
    switch (this.activeTab) {
      case 'artifacts':
        return html`
          <now-demo-catalog
            @otto-prompt=${(e: CustomEvent<{ text: string }>) =>
              this.handleIntentPrompt(e.detail.text, true)}
            @demo-deploy=${(e: CustomEvent<{ bundleId: string }>) => {
              this.selectedBundleId = e.detail.bundleId;
            }}
          ></now-demo-catalog>
        `;
      case 'fluent':
        return html`<now-fluent-explorer .bundleId=${this.selectedBundleId}></now-fluent-explorer>`;
      case 'admin':
      case 'settings':
        return html`
          <now-workbench-settings
            @settings-updated=${(e: CustomEvent<{ prefs: WorkbenchPreferences }>) => {
              this.welcomeModalOpen = false;
              this.autoRouteIntent = e.detail.prefs.auto_route_intent;
            }}
          ></now-workbench-settings>
        `;
      case 'synthesizer':
        return html`
          <now-conversational-workspace
            .viewMode=${'synthesizer'}
            .incomingPrompt=${this.routedPrompt}
            @nav-change=${this.handleNavChange}
            @open-welcome=${() => {
              this.welcomeModalOpen = true;
            }}
            @open-walkthrough=${this.handleOpenWalkthrough}
            @open-otto=${this.handleOpenOtto}
          ></now-conversational-workspace>
        `;
      case 'capture':
        return html`
          <now-conversational-workspace
            .viewMode=${'capture'}
            .incomingPrompt=${this.routedPrompt}
            @nav-change=${this.handleNavChange}
            @open-welcome=${() => {
              this.welcomeModalOpen = true;
            }}
            @open-walkthrough=${this.handleOpenWalkthrough}
            @open-otto=${this.handleOpenOtto}
          ></now-conversational-workspace>
        `;
      case 'home':
      default:
        return html`
          <now-conversational-workspace
            .viewMode=${'home'}
            .activeThreadId=${this.activeThreadId}
            .incomingPrompt=${this.routedPrompt}
            @intent-submit=${(e: CustomEvent<{ prompt: string; stayInOtto?: boolean }>) =>
              this.handleIntentPrompt(e.detail.prompt, e.detail.stayInOtto ?? true)}
            @thread-created=${async (e: CustomEvent<{ threadId: string }>) => {
              await this.loadThreads();
              this.activeThreadId = e.detail.threadId;
            }}
            @threads-refresh=${async () => {
              await this.loadThreads();
            }}
            @new-session=${() => this.handleNewSession()}
            @thread-archive=${(e: CustomEvent<{ threadId: string; archived: boolean }>) =>
              this.handleThreadArchive(e)}
            @thread-delete=${(e: CustomEvent<{ threadId: string }>) =>
              this.handleThreadDelete(e)}
            @session-close=${() => {
              this.routedPrompt = '';
              this.activeThreadId = '';
            }}
            @nav-change=${this.handleNavChange}
            @open-welcome=${() => {
              this.welcomeModalOpen = true;
            }}
            @open-walkthrough=${this.handleOpenWalkthrough}
            @open-otto=${this.handleOpenOtto}
            @collapse-rail=${(e: CustomEvent<{ collapsed: boolean }>) => {
              this.railCollapsed = e.detail.collapsed;
            }}
          ></now-conversational-workspace>
        `;
    }
  }

  private handleToggleOtto(): void {
    this.setActiveTab('home');
  }

  private handleOpenOtto(): void {
    this.setActiveTab('home');
  }

  @state() private access: 'checking' | 'ok' | GateMode = 'checking';
  @state() private accessEmail = '';
  @state() private accessMessage = '';

  /** Decide between the app, the forced first-run setup dialog, and the no-access page. */
  private async checkAccess(): Promise<void> {
    try {
      const res = await fetch('/api/setup/status');
      const body = (await res.json().catch(() => ({}))) as {
        setup_required?: boolean;
        has_role?: boolean;
        email?: string;
        detail?: string;
      };
      if (!res.ok) {
        this.access = 'error';
        this.accessMessage = body.detail || `The workbench answered HTTP ${res.status}.`;
        return;
      }
      this.accessEmail = body.email ?? '';
      this.access = body.setup_required ? 'setup' : body.has_role ? 'ok' : 'denied';
    } catch (err) {
      this.access = 'error';
      this.accessMessage = `Could not reach the workbench: ${String(err)}`;
    }
  }

  render() {
    if (this.access === 'checking') return html``;
    if (this.access !== 'ok') {
      return html`<now-access-gate
        .mode=${this.access}
        .email=${this.accessEmail}
        .message=${this.accessMessage}
        @setup-complete=${() => window.location.reload()}
      ></now-access-gate>`;
    }
    return html`
      <now-nav-rail
        .activeTab=${this.activeTab}
        .activeThreadId=${this.activeThreadId}
        .threads=${this.recentThreads}
        .collapsed=${this.railCollapsed}
        @nav-change=${this.handleNavChange}
        @thread-select=${this.handleThreadSelect}
        @thread-archive=${this.handleThreadArchive}
        @thread-delete=${this.handleThreadDelete}
        @new-session=${this.handleNewSession}
        @toggle-otto=${this.handleToggleOtto}
      ></now-nav-rail>

      <main class="content-area">
        <now-impersonation-banner></now-impersonation-banner>
        ${this.threadError
          ? html`<div class="thread-error-banner" role="alert" data-testid="thread-error">
              ${this.threadError}
            </div>`
          : ''}
        <div class="active-view-stage">
          ${this.renderActiveView()}
        </div>

        ${this.activeTab !== 'home'
          ? html`
              <div class="bottom-chat-dock">
                <div class="bottom-prompt-box">
                  <input
                    type="text"
                    placeholder="Ask Otto to refine this workspace, synthesize a use case, or capture media"
                    .value=${this.bottomChatInput}
                    @input=${(e: Event) => {
                      this.bottomChatInput = (e.target as HTMLInputElement).value;
                    }}
                    @keydown=${(e: KeyboardEvent) => {
                      if (e.key === 'Enter') {
                        this.handleBottomChatSubmit();
                      }
                    }}
                  />
                  <div class="bottom-prompt-foot">
                    <button
                      class="bottom-send-btn"
                      @click=${this.handleBottomChatSubmit}
                      title="Send prompt to Now Workbench"
                      aria-label="Send prompt"
                      data-tooltip="Send"
                    >
                      ${sendIcon(16)}
                    </button>
                  </div>
                </div>
                <div class="intent-route-caption">${this.lastIntentExplanation}</div>
              </div>
            `
          : ''}
      </main>

      <now-welcome-modal
        .open=${this.welcomeModalOpen}
        @modal-close=${() => {
          this.welcomeModalOpen = false;
        }}
        @modal-navigate=${(e: CustomEvent<{ tab: string }>) => {
          this.welcomeModalOpen = false;
          this.setActiveTab(e.detail.tab);
        }}
        @show-welcome-change=${(e: CustomEvent<{ showOnStartup: boolean }>) => {
          if (!e.detail.showOnStartup) {
            this.welcomeModalOpen = false;
          }
        }}
      ></now-welcome-modal>

      <now-presenter-hud
        .bundleId=${this.selectedBundleId}
        .visible=${this.presenterHudVisible}
        @hud-close=${() => {
          this.presenterHudVisible = false;
        }}
      ></now-presenter-hud>

      <now-command-palette
        @command-selected=${this.handlePaletteCommand}
      ></now-command-palette>
    `;
  }
}
