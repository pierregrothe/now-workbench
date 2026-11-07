import { sendIcon } from '../icons.js';
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import '../views/now-access-gate.js';
import type { GateMode } from '../views/now-access-gate.js';
import './now-nav-rail.js';
import type { NavThreadItem } from './now-nav-rail.js';
import './now-conversational-workspace.js';
import './now-demo-catalog.js';
import './now-fluent-explorer.js';
import './now-workbench-settings.js';
import type { WorkbenchPreferences } from './settings-model.js';
import './now-presenter-hud.js';
import './now-welcome-modal.js';
import '../views/now-impersonation.js';
import './now-command-palette.js';
import { smartTooltip } from '../utils/tooltip.js';
import { workbenchStore } from '../context/workbench-context.js';
import { workbenchShellStyles } from './now-workbench-shell-styles.js';
import { ThreadListController } from '../controllers/thread-list-controller.js';
import { detectIntent } from '../utils/intent-router.js';
import '../views/now-actions-view.js';

const VALID_SHELL_TABS = new Set([
  'home',
  'artifacts',
  'synthesizer',
  'capture',
  'fluent',
  'admin',
  'actions',
]);

/** Split '#tab/sub' into its tab and its sub-location (a Settings section, an action). */
function parseHash(): [string, string] {
  const [tab = '', sub = ''] = window.location.hash.replace(/^#\/?/, '').trim().split('/');
  return [tab, sub];
}

function resolveInitialTab(): string {
  if (typeof window !== 'undefined') {
    const [rawHash] = parseHash();
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
  static styles = workbenchShellStyles;

  @state() private activeTab = resolveInitialTab();
  /** Where inside the tab: a Settings section or an action ('#admin/groups', '#actions/x'). */
  @state() private activeSub = typeof window !== 'undefined' ? parseHash()[1] : '';
  @state() private activeThreadId = '';
  @state() private selectedBundleId = 'sample-ai-assistant';
  @state() private welcomeModalOpen =
    typeof localStorage !== 'undefined'
      ? localStorage.getItem('now-workbench-show-welcome') !== 'false'
      : true;
  @state() private autoRouteIntent = true;
  @state() private railCollapsed = false;

  private setActiveTab(tab: string, sub = ''): void {
    const target = VALID_SHELL_TABS.has(tab) ? tab : 'home';
    this.activeTab = target;
    this.activeSub = sub;
    workbenchStore.setState({ activeTab: target });
    if (typeof window !== 'undefined') {
      const hash = sub ? `#${target}/${sub}` : `#${target}`;
      if (window.location.hash !== hash) {
        window.location.hash = hash;
      }
      try {
        localStorage.setItem('now-workbench-active-tab', target);
      } catch {}
    }
  }

  private handleWindowHashChange = (): void => {
    const [rawHash, sub] = parseHash();
    this.activeSub = sub;
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
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (typeof window !== 'undefined') {
      window.removeEventListener('hashchange', this.handleWindowHashChange);
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

  private readonly threads = new ThreadListController(this);

  private async handleIntentPrompt(prompt: string, stayInOtto = false): Promise<void> {
    const clean = prompt.trim();
    if (!clean) {
      return;
    }
    const detected = detectIntent(clean);
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

  private handleNavChange(
    e: CustomEvent<{ tab: string; section?: string; action?: string; args?: Record<string, unknown> }>
  ): void {
    const { tab, section, action, args } = e.detail;
    if (tab === 'help' || tab === 'welcome') {
      this.welcomeModalOpen = true;
      return;
    }
    if (action) {
      workbenchStore.setState({ pendingAction: { name: action, args: args ?? {} } });
    }
    this.setActiveTab(tab, section ?? action ?? '');
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

  private async startOttoThread(title: string, firstMessage?: string): Promise<void> {
    const id = await this.threads.create(title, firstMessage);
    if (!id) return;
    this.activeThreadId = id;
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
    await this.threads.setArchived(e.detail.threadId, e.detail.archived);
  }

  private async handleThreadDelete(e: CustomEvent<{ threadId: string }>): Promise<void> {
    const { threadId } = e.detail;
    if (!(await this.threads.remove(threadId))) return;
    if (this.activeThreadId === threadId) {
      this.activeThreadId = '';
      this.routedPrompt = '';
    }
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
      case 'actions':
        return html`<now-actions-view .actionName=${this.activeSub}></now-actions-view>`;
      case 'admin':
      case 'settings':
        return html`
          <now-workbench-settings
            .section=${this.activeSub}
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
              await this.threads.load();
              this.activeThreadId = e.detail.threadId;
            }}
            @threads-refresh=${async () => {
              await this.threads.load();
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
        .threads=${this.threads.items}
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
        ${this.threads.error
          ? html`<div class="thread-error-banner" role="alert" data-testid="thread-error">
              ${this.threads.error}
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
