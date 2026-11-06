import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { workbenchStore } from '../context/workbench-context.js';
import { libraryIcon } from '../icons.js';
import { renderAvatar, roleSummary } from '../profile/avatars.js';
import type { ProfileData } from '../profile/avatars.js';

export interface NavThreadItem {
  id: string;
  title: string;
  targetTab: string;
  archived?: boolean;
  messageCount?: number;
  maxMessages?: number;
  prompt?: string;
}

@customElement('now-nav-rail')
export class NowNavRail extends LitElement {
  static styles = css`
    :host {
      display: block;
      height: 100%;
      background-color: var(--otto-canvas, #efece7);
      border-right: 1px solid var(--now-border-subtle, #ececeb);
      user-select: none;
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: var(--now-text-primary, #16181d);
      flex-shrink: 0;
      transition: width 0.18s ease;
    }

    .rail-container {
      width: 248px;
      height: 100%;
      display: flex;
      flex-direction: column;
      padding: 12px 12px 18px 12px;
      box-sizing: border-box;
      overflow-y: auto;
      transition: width 0.18s ease;
    }

    .rail-container.collapsed {
      width: 64px;
      padding: 12px 8px;
      align-items: center;
    }

    .top-chrome {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      min-height: 28px;
      margin-bottom: 4px;
      width: 100%;
    }

    .rail-container.collapsed .top-chrome {
      justify-content: center;
    }

    .collapse-btn {
      position: relative;
      appearance: none;
      border: none;
      background: transparent;
      color: #4a4e58;
      width: 28px;
      height: 28px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }

    .collapse-btn:hover {
      background: var(--otto-canvas-active, #e3dfd8);
      color: #16181d;
    }

    .collapse-btn svg {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      stroke-width: 1.75;
      fill: none;
    }

    .brand-header {
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 6px 8px 18px 8px;
      cursor: pointer;
    }

    .rail-container.collapsed .brand-header {
      padding: 6px 0 18px 0;
      justify-content: center;
    }

    .sn-glyph {
      width: 22px;
      height: 22px;
      flex-shrink: 0;
    }

    .brand-title {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--now-text-primary, #0b0f19);
      line-height: 1.2;
      white-space: nowrap;
    }

    .primary-list {
      display: flex;
      flex-direction: column;
      gap: 2px;
      margin-bottom: 18px;
      width: 100%;
    }

    .nav-row {
      appearance: none;
      border: none;
      background: transparent;
      width: 100%;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 999px;
      font-size: 13.5px;
      font-weight: 400;
      color: var(--now-text-secondary, #2c2e33);
      cursor: pointer;
      text-align: left;
      transition: background-color 0.12s ease, color 0.12s ease;
      font-family: inherit;
    }

    .rail-container.collapsed .nav-row {
      justify-content: center;
      padding: 9px;
    }

    .nav-row:hover {
      background-color: var(--otto-canvas-active, #e3dfd8);
      color: var(--now-text-primary, #0b0f19);
    }

    .nav-row.active {
      background-color: var(--otto-canvas-active, #e3dfd8);
      color: var(--now-text-primary, #0b0f19);
      font-weight: 600;
    }

    .nav-row.active .nav-icon {
      color: var(--now-color-brand-green, #032d42);
    }

    .nav-icon {
      width: 17px;
      height: 17px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: currentColor;
    }

    .nav-icon svg {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .section-block {
      display: flex;
      flex-direction: column;
      margin-bottom: 18px;
      width: 100%;
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 4px 10px 6px 10px;
    }

    .section-label {
      font-size: 12px;
      font-weight: 500;
      color: #686b73;
      letter-spacing: -0.005em;
    }

    .compose-btn {
      position: relative;
      appearance: none;
      border: 1px solid #d4d5d2;
      background: #ffffff;
      color: #2c2e33;
      width: 24px;
      height: 24px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background 0.12s ease, border-color 0.12s ease;
    }

    .compose-btn:hover {
      background: #f3f3f1;
      border-color: #b8b9b4;
    }

    .compose-btn svg {
      width: 13px;
      height: 13px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .thread-title {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
    }

    .session-icon {
      width: 15px;
      height: 15px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--now-text-muted, #64748b);
    }

    .session-icon svg {
      width: 14px;
      height: 14px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .thread-row-wrap {
      display: flex;
      align-items: center;
      gap: 2px;
      width: 100%;
      border-radius: 10px;
      padding-right: 4px;
      transition: background-color 0.12s ease;
    }

    .thread-row-wrap:hover {
      background-color: var(--now-bg-surface-1, #f1f1ef);
    }

    .thread-row-wrap.active {
      background-color: var(--now-bg-surface-1, #ececea);
    }

    .thread-row-wrap .nav-row {
      flex: 1;
      min-width: 0;
      padding: 7px 8px;
      background: transparent !important;
    }

    .thread-count-badge {
      font-size: 10px;
      font-weight: 600;
      color: var(--now-text-muted, #64748b);
      background: var(--now-bg-surface-2, #e2e8f0);
      padding: 1px 5px;
      border-radius: 999px;
      flex-shrink: 0;
    }

    .thread-actions {
      display: flex;
      align-items: center;
      gap: 2px;
      flex-shrink: 0;
      opacity: 0.75;
      transition: opacity 0.12s ease;
    }

    .thread-row-wrap:hover .thread-actions {
      opacity: 1;
    }

    .thread-action-btn {
      appearance: none;
      border: none;
      background: transparent;
      color: var(--now-text-muted, #64748b);
      width: 22px;
      height: 22px;
      border-radius: 5px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      padding: 0;
      transition: all 0.12s ease;
    }

    .thread-action-btn:hover {
      background: rgba(15, 23, 42, 0.08);
      color: var(--now-text-primary, #0f172a);
    }

    .thread-action-btn.delete:hover {
      background: #fee2e2;
      color: #dc2626;
    }

    .thread-action-btn svg {
      width: 13px;
      height: 13px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .archived-toggle-btn {
      appearance: none;
      border: none;
      background: transparent;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-text-muted, #64748b);
      padding: 8px 10px 4px 10px;
      cursor: pointer;
      font-family: inherit;
    }

    .archived-toggle-btn:hover {
      color: var(--now-text-primary, #0f172a);
    }

    .spacer {
      flex: 1;
    }

    .bottom-utilities {
      padding-top: 8px;
      border-top: 1px solid #ececeb;
      display: flex;
      flex-direction: column;
      gap: 2px;
      width: 100%;
    }

    .user-profile-row {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid var(--now-border-subtle, #ececea);
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
    }

    .user-profile-row.collapsed {
      justify-content: center;
      padding-top: 8px;
    }

    .user-avatar-pill {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      font-size: 11px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .user-info-text {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .user-name {
      font-size: 12.5px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-role {
      font-size: 11px;
      color: var(--now-text-muted, #64748b);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-more-btn {
      appearance: none;
      border: none;
      background: transparent;
      color: var(--now-text-muted, #64748b);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 4px;
      border-radius: 4px;
    }

    .user-more-btn svg {
      width: 14px;
      height: 14px;
      fill: currentColor;
    }
  `;

  @property({ type: String }) activeTab = 'home';
  @property({ type: String }) activeThreadId = '';
  @property({ type: Array }) threads: NavThreadItem[] = [];
  @property({ type: Boolean }) collapsed = false;

  @state() private showArchived = false;
  @state() private profile: ProfileData | null = workbenchStore.state.profile;
  private unsubscribeProfile?: () => void;

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribeProfile = workbenchStore.subscribe((state) => {
      this.profile = state.profile;
    });
    void workbenchStore.loadProfile();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribeProfile?.();
  }

  private selectTab(tab: string): void {
    this.dispatchEvent(
      new CustomEvent('nav-change', {
        detail: { tab },
        bubbles: true,
        composed: true,
      })
    );
  }

  private selectThread(thread: NavThreadItem): void {
    this.dispatchEvent(
      new CustomEvent('thread-select', {
        detail: { thread },
        bubbles: true,
        composed: true,
      })
    );
  }

  private archiveThread(e: Event, thread: NavThreadItem): void {
    e.stopPropagation();
    this.dispatchEvent(
      new CustomEvent('thread-archive', {
        detail: { threadId: thread.id, archived: !thread.archived },
        bubbles: true,
        composed: true,
      })
    );
  }

  private deleteThread(e: Event, thread: NavThreadItem): void {
    e.stopPropagation();
    this.dispatchEvent(
      new CustomEvent('thread-delete', {
        detail: { threadId: thread.id },
        bubbles: true,
        composed: true,
      })
    );
  }

  private startNewSession(): void {
    this.dispatchEvent(
      new CustomEvent('new-session', {
        bubbles: true,
        composed: true,
      })
    );
  }

  private renderThreadItem(thread: NavThreadItem, isActive: boolean) {
    const countLabel =
      typeof thread.messageCount === 'number'
        ? `${thread.messageCount}/${thread.maxMessages ?? 20}`
        : '';
    return html`
      <div class="thread-row-wrap ${isActive ? 'active' : ''}">
        <button
          class="nav-row ${isActive ? 'active' : ''}"
          title="${thread.title}${countLabel ? ` (${countLabel} messages)` : ''}"
          @click=${() => this.selectThread(thread)}
        >
          <span class="session-icon">
            <svg viewBox="0 0 24 24">
              <path
                d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
              ></path>
            </svg>
          </span>
          <span class="thread-title">${thread.title}</span>
          ${countLabel ? html`<span class="thread-count-badge">${countLabel}</span>` : ''}
        </button>
        <div class="thread-actions">
          <button
            class="thread-action-btn"
            title=${thread.archived ? 'Unarchive conversation' : 'Archive conversation'}
            aria-label=${thread.archived ? 'Unarchive conversation' : 'Archive conversation'}
            @click=${(e: Event) => this.archiveThread(e, thread)}
          >
            <svg viewBox="0 0 24 24">
              <polyline points="21 8 21 21 3 21 3 8"></polyline>
              <rect x="1" y="3" width="22" height="5"></rect>
              <line x1="10" y1="12" x2="14" y2="12"></line>
            </svg>
          </button>
          <button
            class="thread-action-btn delete"
            title="Delete conversation"
            aria-label="Delete conversation"
            @click=${(e: Event) => this.deleteThread(e, thread)}
          >
            <svg viewBox="0 0 24 24">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
              <path d="M10 11v6"></path>
              <path d="M14 11v6"></path>
            </svg>
          </button>
        </div>
      </div>
    `;
  }

  render() {
    return html`
      <nav class="rail-container ${this.collapsed ? 'collapsed' : ''}" aria-label="Now Workbench Navigation">
        <div class="top-chrome">
          <button
            class="collapse-btn"
            title=${this.collapsed ? 'Expand navigation' : 'Collapse navigation'}
            data-tooltip=${this.collapsed ? 'Expand' : 'Collapse'}
            @click=${() => {
              this.collapsed = !this.collapsed;
            }}
          >
            <svg viewBox="0 0 24 24">
              <rect x="3" y="4" width="18" height="16" rx="2"></rect>
              <line x1="9" y1="4" x2="9" y2="20"></line>
              ${this.collapsed
                ? html`<polyline points="13 9 16 12 13 15"></polyline>`
                : html`<polyline points="15 9 12 12 15 15"></polyline>`}
            </svg>
          </button>
        </div>

        <div class="brand-header" @click=${() => this.selectTab('home')} title="Now Workbench Home">
          <svg class="sn-glyph" viewBox="0 0 32 32" fill="none">
            <path
              d="M16 3C8.82 3 3 8.82 3 16C3 20.88 5.69 25.13 9.68 27.35C10.95 25.43 13.31 24.15 16 24.15C18.69 24.15 21.05 25.43 22.32 27.35C26.31 25.13 29 20.88 29 16C29 8.82 23.18 3 16 3ZM16 21.2C12.58 21.2 9.8 18.42 9.8 15C9.8 11.58 12.58 8.8 16 8.8C19.42 8.8 22.2 11.58 22.2 15C22.2 18.42 19.42 21.2 16 21.2Z"
              fill="#62d84e"
            />
          </svg>
          ${!this.collapsed ? html`<span class="brand-title">Now Workbench</span>` : ''}
        </div>

        <div class="primary-list">
          <button
            class="nav-row ${this.activeTab === 'home' ? 'active' : ''}"
            title="Home (Conversational Hub)"
            @click=${() => this.selectTab('home')}
          >
            <span class="nav-icon">
              <svg viewBox="0 0 24 24">
                <path d="M3 10.5L12 3l9 7.5"></path>
                <path d="M5 9.5V19a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9.5"></path>
              </svg>
            </span>
            ${!this.collapsed ? html`<span>Home</span>` : ''}
          </button>

          <button
            class="nav-row ${this.activeTab === 'synthesizer' ? 'active' : ''}"
            title="Use-Case Synthesizer"
            @click=${() => this.selectTab('synthesizer')}
          >
            <span class="nav-icon">
              <svg viewBox="0 0 24 24">
                <path d="M12 2L14.5 8.5L21 11L14.5 13.5L12 20L9.5 13.5L3 11L9.5 8.5L12 2Z"></path>
              </svg>
            </span>
            ${!this.collapsed ? html`<span>Use-Case Synthesizer</span>` : ''}
          </button>

          <button
            class="nav-row ${this.activeTab === 'capture' ? 'active' : ''}"
            title="Media Capture"
            @click=${() => this.selectTab('capture')}
          >
            <span class="nav-icon">
              <svg viewBox="0 0 24 24">
                <rect x="3" y="5" width="18" height="14" rx="2"></rect>
                <circle cx="12" cy="12" r="3.2"></circle>
              </svg>
            </span>
            ${!this.collapsed ? html`<span>Media Capture</span>` : ''}
          </button>

          <button
            class="nav-row ${this.activeTab === 'artifacts' ? 'active' : ''}"
            title="Artifact Library"
            @click=${() => this.selectTab('artifacts')}
          >
            <span class="nav-icon">
              ${libraryIcon()}
            </span>
            ${!this.collapsed ? html`<span>Artifact library</span>` : ''}
          </button>

          <button
            class="nav-row ${this.activeTab === 'fluent' ? 'active' : ''}"
            title="Fluent SDK Explorer"
            @click=${() => this.selectTab('fluent')}
          >
            <span class="nav-icon">
              <svg viewBox="0 0 24 24">
                <polyline points="16 18 22 12 16 6"></polyline>
                <polyline points="8 6 2 12 8 18"></polyline>
              </svg>
            </span>
            ${!this.collapsed ? html`<span>Fluent SDK Explorer</span>` : ''}
          </button>
        </div>

        ${!this.collapsed
          ? (() => {
              const unarchived = this.threads.filter((t) => !t.archived);
              const archived = this.threads.filter((t) => t.archived);
              const activeThread = this.activeThreadId
                ? this.threads.find((t) => t.id === this.activeThreadId)
                : undefined;
              const pastThreads = unarchived.filter((t) => t.id !== activeThread?.id);
              return html`
                <div class="section-block">
                  <div class="section-header">
                    <span class="section-label">Recent</span>
                    <button
                      class="compose-btn"
                      title="New conversation"
                      aria-label="New conversation"
                      @click=${this.startNewSession}
                    >
                      <svg viewBox="0 0 24 24">
                        <path d="M12 20h9"></path>
                        <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"></path>
                      </svg>
                    </button>
                  </div>
                  ${activeThread ? this.renderThreadItem(activeThread, true) : ''}
                  ${pastThreads.map((thread) =>
                    this.renderThreadItem(thread, this.activeThreadId === thread.id)
                  )}
                  ${!activeThread && pastThreads.length === 0
                    ? html`<div style="font-size: 12px; color: var(--now-text-muted, #64748b); padding: 4px 10px;">No conversations yet.</div>`
                    : ''}
                  ${archived.length > 0
                    ? html`
                        <button
                          class="archived-toggle-btn"
                          @click=${() => {
                            this.showArchived = !this.showArchived;
                          }}
                        >
                          <span>Archived (${archived.length})</span>
                          <span>${this.showArchived ? 'v' : '>'}</span>
                        </button>
                        ${this.showArchived
                          ? archived.map((thread) =>
                              this.renderThreadItem(thread, this.activeThreadId === thread.id)
                            )
                          : ''}
                      `
                    : ''}
                </div>
              `;
            })()
          : html`
              <button
                class="nav-row"
                title="New Conversation"
                @click=${this.startNewSession}
              >
                <span class="nav-icon">
                  <svg viewBox="0 0 24 24">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                  </svg>
                </span>
              </button>
            `}

        <div class="spacer"></div>

        <div class="bottom-utilities">
          <button
            class="nav-row"
            title="Welcome to Now Workbench"
            @click=${() => this.selectTab('help')}
          >
            <span class="nav-icon">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9"></circle>
                <path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.5-2.5 2-2.5 3.5"></path>
                <circle cx="12" cy="16.5" r="0.8" fill="currentColor"></circle>
              </svg>
            </span>
            ${!this.collapsed ? html`<span>Welcome Guide</span>` : ''}
          </button>

          <button
            class="nav-row ${this.activeTab === 'admin' ? 'active' : ''}"
            title="Workbench Settings"
            @click=${() => this.selectTab('admin')}
          >
            <span class="nav-icon">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </span>
            ${!this.collapsed ? html`<span>Workbench Settings</span>` : ''}
          </button>

          <div class="user-profile-row ${this.collapsed ? 'collapsed' : ''}">
            <div class="user-avatar-pill" style="background:none;">${renderAvatar(this.profile, 28)}</div>
            ${!this.collapsed
              ? html`
                  <div class="user-info-text">
                    <span class="user-name">${this.profile?.display_name || this.profile?.email || 'Signing in...'}</span>
                    <span class="user-role">${roleSummary(this.profile)}</span>
                  </div>
                  <button class="user-more-btn" title="Account profile" aria-label="Account profile" @click=${() => this.dispatchEvent(new CustomEvent('nav-change', { detail: { tab: 'admin' }, bubbles: true, composed: true }))}>
                    <svg viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="1.5"></circle>
                      <circle cx="12" cy="5" r="1.5"></circle>
                      <circle cx="12" cy="19" r="1.5"></circle>
                    </svg>
                  </button>
                `
              : ''}
          </div>
        </div>
      </nav>
    `;
  }
}
