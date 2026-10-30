import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './now-nav-rail.js';
import type { NavThreadItem } from './now-nav-rail.js';
import './now-conversational-workspace.js';
import './now-demo-catalog.js';
import './now-fluent-explorer.js';
import './now-workbench-settings.js';
import type { WorkbenchPreferences } from './now-workbench-settings.js';
import { applyTheme, getStoredTheme } from '../utils/theme.js';
import './now-presenter-hud.js';
import './now-welcome-modal.js';
import './now-command-palette.js';
import { smartTooltip } from '../utils/tooltip.js';

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

    .active-view-stage {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    /* Docked Bottom Chat Bar (shown whenever activeTab !== 'home') */
    .bottom-chat-dock {
      flex-shrink: 0;
      padding: 12px 36px 18px 36px;
      background: var(--now-bg-surface-0, #ffffff);
      border-top: 1px solid var(--now-border-subtle, #ececeb);
      box-shadow: 0 -6px 24px rgba(0, 0, 0, 0.03);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      z-index: 20;
    }

    .intent-route-banner {
      width: 100%;
      max-width: 1020px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: var(--now-text-secondary, #374151);
      background: var(--now-bg-surface-1, #f4faf3);
      border: 1px solid var(--now-border-subtle, #d5ecd0);
      padding: 6px 14px;
      border-radius: 999px;
      box-sizing: border-box;
    }

    .intent-route-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 700;
      color: var(--now-color-brand-green, #032d42);
    }

    .intent-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #62d84e;
    }

    .bottom-prompt-box {
      width: 100%;
      max-width: 1020px;
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--now-bg-surface-1, #f7f7f5);
      border: 1.5px solid var(--now-border-medium, #d8dad4);
      border-radius: 999px;
      padding: 6px 8px 6px 20px;
      box-sizing: border-box;
      transition: border-color 0.14s ease, background 0.14s ease;
    }

    .bottom-prompt-box:focus-within {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-border-highlight, #032d42);
    }

    .bottom-prompt-box input {
      flex: 1;
      border: none;
      background: transparent;
      font-family: inherit;
      font-size: 14px;
      color: var(--now-text-primary, #16181d);
      outline: none;
    }

    .bottom-send-btn {
      position: relative;
      appearance: none;
      border: 1px solid var(--now-color-brand-green, #62d84e);
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
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
          message_count?: number;
          max_messages?: number;
        }>;
        this.recentThreads = list.map((t) => ({
          id: t.id,
          title: t.title,
          targetTab: t.target_tab || 'home',
          archived: Boolean(t.archived),
          messageCount: t.message_count ?? 0,
          maxMessages: t.max_messages ?? 20,
        }));
      }
    } catch {
      // Offline preview keeps existing threads
    }
  }

  private async loadInitialPreferences(): Promise<void> {
    applyTheme(getStoredTheme());
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
        if (prefs.theme_mode) {
          applyTheme(prefs.theme_mode);
        }
      }
    } catch {
      // Offline preview keeps stored theme
    }
  }
  @state() private presenterHudVisible = false;
  @state() private bottomChatInput = '';
  @state() private routedPrompt = '';
  @state() private lastIntentExplanation =
    'AI Intent Router active. Describe an action below to switch menus or update the current workspace.';

  @state() private recentThreads: NavThreadItem[] = [];

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
      try {
        const createRes = await fetch('/api/threads', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: shortTitle, target_tab: 'home' }),
        });
        if (createRes.ok) {
          const created = (await createRes.json()) as { id: string; title: string };
          await fetch(`/api/threads/${created.id}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: clean, role: 'user' }),
          });
          await this.loadThreads();
          this.activeThreadId = created.id;
          this.setActiveTab('home');
          return;
        }
      } catch {
        // Offline preview fallback
      }
      const fallbackId = `thread-${Date.now()}`;
      this.recentThreads = [
        {
          id: fallbackId,
          title: shortTitle,
          targetTab: 'home',
          archived: false,
          messageCount: 2,
          maxMessages: 20,
          prompt: clean,
        },
        ...this.recentThreads,
      ];
      this.activeThreadId = fallbackId;
      this.routedPrompt = clean;
      this.setActiveTab('home');
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

  private async handleNewSession(): Promise<void> {
    this.routedPrompt = '';
    this.setActiveTab('home');
    this.railCollapsed = false;
    try {
      const res = await fetch('/api/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'New Otto Conversation',
          target_tab: 'home',
        }),
      });
      if (res.ok) {
        const created = (await res.json()) as { id: string; title: string };
        await this.loadThreads();
        this.activeThreadId = created.id;
        return;
      }
    } catch {
      // Offline preview fallback
    }
    const fallbackId = `thread-${Date.now()}`;
    this.recentThreads = [
      {
        id: fallbackId,
        title: 'New Otto Conversation',
        targetTab: 'home',
        archived: false,
        messageCount: 0,
        maxMessages: 20,
      },
      ...this.recentThreads,
    ];
    this.activeThreadId = fallbackId;
  }

  private async handleThreadArchive(
    e: CustomEvent<{ threadId: string; archived: boolean }>
  ): Promise<void> {
    const { threadId, archived } = e.detail;
    try {
      await fetch(`/api/threads/${threadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archived }),
      });
    } catch {
      // Offline preview fallback
    }
    this.recentThreads = this.recentThreads.map((t) =>
      t.id === threadId ? { ...t, archived } : t
    );
    await this.loadThreads();
  }

  private async handleThreadDelete(e: CustomEvent<{ threadId: string }>): Promise<void> {
    const { threadId } = e.detail;
    try {
      await fetch(`/api/threads/${threadId}`, {
        method: 'DELETE',
      });
    } catch {
      // Offline preview fallback
    }
    this.recentThreads = this.recentThreads.filter((t) => t.id !== threadId);
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

  render() {
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
        <div class="active-view-stage">
          ${this.renderActiveView()}
        </div>

        ${this.activeTab !== 'home'
          ? html`
              <div class="bottom-chat-dock">
                <div class="intent-route-banner">
                  <span class="intent-route-badge">
                    <span class="intent-dot"></span>
                    <span>Now Workbench AI</span>
                  </span>
                  <span>${this.lastIntentExplanation}</span>
                </div>
                <div class="bottom-prompt-box">
                  <input
                    type="text"
                    placeholder="Ask Now Workbench to refine this workspace, synthesize another use case, or capture screenshots/videos..."
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
                  <button
                    class="bottom-send-btn"
                    @click=${this.handleBottomChatSubmit}
                    title="Send prompt to Now Workbench"
                    aria-label="Send prompt"
                    data-tooltip="Send"
                  >
                    <svg viewBox="0 0 24 24">
                      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                    </svg>
                  </button>
                </div>
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
