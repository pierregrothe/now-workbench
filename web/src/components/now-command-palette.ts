import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'

export interface PaletteCommand {
  id: string
  title: string
  category: 'Demos' | 'Instances' | 'Templates' | 'Diagnostics' | 'Otto AI'
  icon: string
  description: string
  shortcut?: string
}

const DEFAULT_COMMANDS: PaletteCommand[] = [
  {
    id: 'presenter-mode',
    title: 'Launch Presenter Mode HUD',
    category: 'Demos',
    icon: '[HUD]',
    description: 'Open persona runbook guide, talking points, and Table API stage verification',
    shortcut: 'P',
  },
  {
    id: 'reset-demo',
    title: 'Reset & Teardown Demo',
    category: 'Demos',
    icon: '[RST]',
    description: '1-click rollback of Table API seed records and restoration of system properties',
    shortcut: 'R',
  },
  {
    id: 'inspect-properties',
    title: 'Inspect System Properties',
    category: 'Demos',
    icon: '[CFG]',
    description: 'View sys_properties configured in active bundle and snapshot status',
  },
  {
    id: 'export-demo',
    title: 'Export Demo Bundle Archive',
    category: 'Demos',
    icon: '[PKG]',
    description: 'Download self-contained .sn-demo.zip bundle package',
  },
  {
    id: 'open-studio',
    title: 'Open Fluent SDK Explorer',
    category: 'Demos',
    icon: '[SDK]',
    description: 'Inspect declared Table schemas and TypeScript definitions (*.now.ts)',
    shortcut: 'S',
  },
  {
    id: 'open-admin',
    title: 'Workbench Settings',
    category: 'Diagnostics',
    icon: '[SET]',
    description: 'Manage instances, TLS probe status, credentials, and theme',
    shortcut: 'D',
  },
  {
    id: 'open-synthesizer',
    title: 'Use-Case Synthesizer',
    category: 'Demos',
    icon: '[SYN]',
    description: 'Synthesize custom multi-table datasets, schemas, and SC narratives',
  },
  {
    id: 'open-capture',
    title: 'Media Capture Studio',
    category: 'Demos',
    icon: '[CAP]',
    description: 'Capture screenshot and walkthrough media from live instances',
  },
  {
    id: 'view-artifacts',
    title: 'Browse Artifact Catalog',
    category: 'Demos',
    icon: '[CAT]',
    description: 'Inspect installed Fluent demonstration bundles and manifests',
  },
]

/** Fired (bubbling, composed) by any control that opens the palette by tap or click. */
export const OPEN_PALETTE_EVENT = 'open-command-palette'

@customElement('now-command-palette')
export class NowCommandPalette extends LitElement {
  @property({ type: Boolean }) open = false
  @state() private query = ''
  @state() private selectedIndex = 0

  static styles = css`
    :host {
      display: contents;
    }

    .palette-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.45);
      backdrop-filter: blur(4px);
      z-index: 9999;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding-top: 15vh;
    }

    .palette-window {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 12px;
      box-shadow: 0 20px 40px -10px rgba(15, 23, 42, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
      width: 580px;
      max-width: 90vw;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      animation: slideDown 0.15s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes slideDown {
      from {
        opacity: 0;
        transform: translateY(-8px) scale(0.98);
      }
      to {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }

    .search-box {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
    }

    .search-icon {
      font-size: 16px;
      opacity: 0.6;
    }

    .search-input {
      flex: 1;
      border: none;
      outline: none;
      font-size: 15px;
      color: var(--now-text-primary, #0f172a);
      background: transparent;
      font-family: inherit;
    }

    .search-input::placeholder {
      color: var(--now-text-muted, #94a3b8);
    }

    .results-list {
      max-height: 380px;
      overflow-y: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .command-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border-radius: 8px;
      cursor: pointer;
      user-select: none;
      transition: background-color 0.1s ease;
    }

    .command-item.selected {
      background-color: var(--now-bg-surface-2, #f1f5f9);
    }

    .command-left {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .command-icon {
      font-size: 18px;
      width: 24px;
      text-align: center;
    }

    .command-info {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .command-title {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .command-desc {
      font-size: 11.5px;
      color: var(--now-text-secondary, #64748b);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .command-meta {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .category-badge {
      font-size: 10.5px;
      padding: 2px 7px;
      border-radius: 4px;
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      color: var(--now-text-secondary, #64748b);
      font-weight: 500;
    }

    .shortcut-key {
      font-size: 10px;
      padding: 2px 5px;
      background: var(--now-bg-surface-2, #e2e8f0);
      border-radius: 4px;
      font-weight: 600;
      color: var(--now-text-primary, #475569);
    }

    .empty-state {
      padding: 30px 20px;
      text-align: center;
      color: var(--now-text-muted, #94a3b8);
      font-size: 13px;
    }

    .palette-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 18px;
      background: var(--now-bg-surface-1, #f8fafc);
      border-top: 1px solid var(--now-border-subtle, #e2e8f0);
      font-size: 11.5px;
      color: var(--now-text-secondary, #64748b);
    }

    .kbd-tips {
      display: flex;
      gap: 12px;
    }

    kbd {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #cbd5e1);
      color: var(--now-text-primary);
      border-radius: 4px;
      padding: 1px 5px;
      font-size: 10.5px;
      box-shadow: 0 1px 1px rgba(0, 0, 0, 0.05);
    }

    /* Phones (ADR-030): near the top, full width, 16px search so iOS does not zoom. */
    @media (max-width: 768px), (max-height: 500px) {
      .palette-backdrop {
        padding: calc(8px + env(safe-area-inset-top, 0px)) 8px 8px;
      }

      .palette-window {
        width: 100%;
        max-width: none;
        max-height: 100%;
      }

      .search-input {
        font-size: 16px;
      }

      .results-list {
        max-height: none;
        flex: 1;
      }

      .command-item {
        min-height: 44px;
      }

      /* The bracket tags crowd the titles on a narrow screen; the category stays. */
      .search-icon,
      .command-icon {
        display: none;
      }
    }

    /* Touch screens have no arrow keys or Enter to explain. */
    @media (hover: none) {
      .kbd-tips,
      .shortcut-key {
        display: none;
      }
    }
  `

  connectedCallback() {
    super.connectedCallback()
    window.addEventListener('keydown', this.handleGlobalKeyDown)
    window.addEventListener(OPEN_PALETTE_EVENT, this.show)
  }

  disconnectedCallback() {
    window.removeEventListener('keydown', this.handleGlobalKeyDown)
    window.removeEventListener(OPEN_PALETTE_EVENT, this.show)
    super.disconnectedCallback()
  }

  private handleGlobalKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault()
      if (this.open) this.close()
      else this.show()
    } else if (e.key === 'Escape' && this.open) {
      this.close()
    }
  }

  /** Open with an empty search and the first command selected (Cmd+K, a tap, a click). */
  show = (): void => {
    this.open = true
    this.query = ''
    this.selectedIndex = 0
    this.focusInput()
  }

  private focusInput() {
    setTimeout(() => {
      const input = this.shadowRoot?.querySelector('.search-input') as HTMLInputElement | null
      input?.focus()
    }, 50)
  }

  private close() {
    this.open = false
    this.dispatchEvent(new CustomEvent('close-palette'))
  }

  private getFilteredCommands(): PaletteCommand[] {
    if (!this.query.trim()) return DEFAULT_COMMANDS
    const q = this.query.toLowerCase()
    return DEFAULT_COMMANDS.filter(
      (cmd) =>
        cmd.title.toLowerCase().includes(q) ||
        cmd.description.toLowerCase().includes(q) ||
        cmd.category.toLowerCase().includes(q)
    )
  }

  private handleKeyDown(e: KeyboardEvent) {
    const list = this.getFilteredCommands()
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      this.selectedIndex = (this.selectedIndex + 1) % (list.length || 1)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      this.selectedIndex = (this.selectedIndex - 1 + list.length) % (list.length || 1)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const selected = list[this.selectedIndex]
      if (selected) this.selectCommand(selected)
    }
  }

  private selectCommand(cmd: PaletteCommand) {
    this.dispatchEvent(
      new CustomEvent('command-selected', {
        detail: { command: cmd.id, title: cmd.title },
        bubbles: true,
        composed: true,
      })
    )
    this.close()
  }

  render() {
    if (!this.open) return html``

    const filtered = this.getFilteredCommands()

    return html`
      <div class="palette-backdrop" @click=${(e: Event) => {
        if (e.target === e.currentTarget) this.close()
      }}>
        <div class="palette-window" @keydown=${this.handleKeyDown}>
          <div class="search-box">
            <span class="search-icon">[FIND]</span>
            <input
              class="search-input"
              type="text"
              placeholder="Type a command or search (e.g. 'runbook', 'reset', 'doctor')..."
              .value=${this.query}
              @input=${(e: Event) => {
                this.query = (e.target as HTMLInputElement).value
                this.selectedIndex = 0
              }}
            />
          </div>

          <div class="results-list">
            ${filtered.length === 0
              ? html`<div class="empty-state">No matching workbench commands found.</div>`
              : filtered.map(
                  (cmd, idx) => html`
                    <div
                      class="command-item ${idx === this.selectedIndex ? 'selected' : ''}"
                      @click=${() => this.selectCommand(cmd)}
                      @mouseenter=${() => (this.selectedIndex = idx)}
                    >
                      <div class="command-left">
                        <span class="command-icon">${cmd.icon}</span>
                        <div class="command-info">
                          <span class="command-title">${cmd.title}</span>
                          <span class="command-desc">${cmd.description}</span>
                        </div>
                      </div>
                      <div class="command-meta">
                        <span class="category-badge">${cmd.category}</span>
                        ${cmd.shortcut ? html`<span class="shortcut-key">${cmd.shortcut}</span>` : ''}
                      </div>
                    </div>
                  `
                )}
          </div>

          <div class="palette-footer">
            <div class="kbd-tips">
              <span><kbd></kbd> <kbd></kbd> navigate</span>
              <span><kbd>Enter</kbd> select</span>
              <span><kbd>esc</kbd> close</span>
            </div>
            <span><strong>ServiceNow</strong> Command Palette</span>
          </div>
        </div>
      </div>
    `
  }
}
