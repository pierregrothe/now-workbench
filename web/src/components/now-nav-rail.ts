import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { workbenchStore } from '../context/workbench-context.js';
import { libraryIcon, menuToggleIcon } from '../icons.js';
import { renderAvatar, roleSummary } from '../profile/avatars.js';
import { StoreController } from '../controllers/store-controller.js';
import { navRailStyles } from './now-nav-rail-styles.js';

export interface NavThreadItem {
  id: string;
  title: string;
  targetTab: string;
  archived?: boolean;
  tokensUsed?: number;
  maxTokens?: number;
  prompt?: string;
}

/** Short token count for the sidebar badge (1.2k, 2M). */
function compactTokens(n: number): string {
  if (n >= 1_000_000) return `${+(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${+(n / 1_000).toFixed(1)}k`;
  return String(n);
}

const SIDEBAR_WIDTH_KEY = 'now-workbench-sidebar-width';
const SIDEBAR_MIN = 200;
const SIDEBAR_MAX = 420;
const SIDEBAR_DEFAULT = 248;

function readSidebarWidth(): number {
  const stored = Number(localStorage.getItem(SIDEBAR_WIDTH_KEY));
  return stored >= SIDEBAR_MIN && stored <= SIDEBAR_MAX ? stored : SIDEBAR_DEFAULT;
}

@customElement('now-nav-rail')
export class NowNavRail extends LitElement {
  static styles = navRailStyles;

  @property({ type: String }) activeTab = 'home';
  @property({ type: String }) activeThreadId = '';
  @property({ type: Array }) threads: NavThreadItem[] = [];
  @property({ type: Boolean }) collapsed = false;

  /** Expanded width in pixels, chosen by dragging the edge (kept across visits). */
  @state() private width = readSidebarWidth();
  @state() private resizing = false;

  @state() private showArchived = false;
  private readonly store = new StoreController(this);

  connectedCallback(): void {
    super.connectedCallback();
    void workbenchStore.loadProfile();
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
      typeof thread.tokensUsed === 'number'
        ? `${compactTokens(thread.tokensUsed)}/${compactTokens(thread.maxTokens ?? 2000000)}`
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

  private setWidth(px: number): void {
    this.width = Math.round(Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, px)));
    localStorage.setItem(SIDEBAR_WIDTH_KEY, String(this.width));
  }

  private startResize = (e: PointerEvent): void => {
    const handle = e.currentTarget as HTMLElement;
    const startX = e.clientX;
    const startWidth = this.width;
    handle.setPointerCapture(e.pointerId);
    this.resizing = true;
    const move = (ev: PointerEvent) => this.setWidth(startWidth + ev.clientX - startX);
    const end = () => {
      this.resizing = false;
      handle.removeEventListener('pointermove', move);
      handle.removeEventListener('pointerup', end);
      handle.removeEventListener('pointercancel', end);
    };
    handle.addEventListener('pointermove', move);
    handle.addEventListener('pointerup', end);
    handle.addEventListener('pointercancel', end);
  };

  private keyResize = (e: KeyboardEvent): void => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      this.setWidth(this.width + (e.key === 'ArrowRight' ? 16 : -16));
    }
  };

  render() {
    return html`
      <nav
        class="rail-container ${this.collapsed ? 'collapsed' : ''} ${this.resizing ? 'resizing' : ''}"
        style=${this.collapsed ? '' : `width: ${this.width}px`}
        aria-label="Now Workbench Navigation"
      >
        <div class="top-chrome">
          <button
            class="collapse-btn"
            title=${this.collapsed ? 'Expand navigation' : 'Collapse navigation'}
            aria-label=${this.collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            data-tooltip=${this.collapsed ? 'Expand' : 'Collapse'}
            @click=${() => {
              this.collapsed = !this.collapsed;
            }}
          >
            ${menuToggleIcon(this.collapsed)}
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

          <button
            class="nav-row ${this.activeTab === 'actions' ? 'active' : ''}"
            title="Actions: everything the workbench can do"
            @click=${() => this.selectTab('actions')}
          >
            <span class="nav-icon">
              <svg viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
            </span>
            ${!this.collapsed ? html`<span>Actions</span>` : ''}
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
            <div class="user-avatar-pill" style="background:none;">${renderAvatar(this.store.state.profile, 28)}</div>
            ${!this.collapsed
              ? html`
                  <div class="user-info-text">
                    <span class="user-name">${this.store.state.profile?.display_name || this.store.state.profile?.email || 'Signing in...'}</span>
                    <span class="user-role">${roleSummary(this.store.state.profile)}</span>
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
      ${this.collapsed
        ? ''
        : html`<div
            class="resize-handle ${this.resizing ? 'active' : ''}"
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize sidebar"
            aria-valuemin=${SIDEBAR_MIN}
            aria-valuemax=${SIDEBAR_MAX}
            aria-valuenow=${this.width}
            tabindex="0"
            @pointerdown=${this.startResize}
            @keydown=${this.keyResize}
            @dblclick=${() => this.setWidth(SIDEBAR_DEFAULT)}
          ></div>`}
    `;
  }
}
