import { LitElement, html, css } from 'lit'
import { customElement, property } from 'lit/decorators.js'

@customElement('now-console')
export class NowConsole extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 220px;
      background-color: #080b0e;
      border-top: 1px solid var(--now-border-subtle);
      font-family: var(--now-font-mono);
      font-size: 12px;
      position: relative;
    }

    .console-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 16px;
      background-color: var(--now-bg-surface-0);
      border-bottom: 1px solid var(--now-border-subtle);
      user-select: none;
    }

    .console-title {
      font-size: 11px;
      font-weight: 600;
      color: var(--now-text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .live-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: var(--now-status-online);
      box-shadow: 0 0 6px var(--now-status-online);
    }

    .console-actions {
      display: flex;
      gap: 12px;
    }

    .action-btn {
      position: relative;
      background: transparent;
      border: none;
      color: var(--now-text-muted);
      cursor: pointer;
      padding: 0;
      width: 24px;
      height: 24px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
    }

    .action-btn svg {
      width: 14px;
      height: 14px;
      fill: currentColor;
    }

    .action-btn:hover {
      color: var(--now-text-primary);
      background: rgba(255, 255, 255, 0.08);
    }

    .action-btn[data-tooltip]::after {
      content: attr(data-tooltip);
      position: absolute;
      bottom: calc(100% + 6px);
      right: 0;
      background: #032d42;
      color: #ffffff;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.12s ease, transform 0.12s ease;
      z-index: 1000;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .action-btn[data-tooltip]:hover::after {
      opacity: 1;
      transform: translateY(-2px);
    }

    .log-stream {
      flex: 1;
      padding: 10px 16px;
      overflow-y: auto;
      color: #94a3b8;
      white-space: pre-wrap;
      line-height: 1.5;
    }

    .log-line.error {
      color: var(--now-status-error);
    }

    .log-line.success {
      color: var(--now-status-online);
    }

    .log-line.info {
      color: var(--now-color-accent-teal);
    }
  `

  @property({ type: Array }) logs: string[] = []
  private ws: WebSocket | null = null

  connectedCallback() {
    super.connectedCallback()
    this.connectWs()
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  private connectWs() {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/logs`
      this.ws = new WebSocket(wsUrl)
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.line) {
            this.logs = [...this.logs, data.line]
          }
        } catch {
          this.logs = [...this.logs, event.data]
        }
      }
      this.ws.onerror = () => {
        // Fallback to parent logs property
      }
    } catch {
      // Offline fallback
    }
  }

  updated() {
    const el = this.shadowRoot?.querySelector('.log-stream')
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }

  private formatLine(line: string) {
    let cls = 'log-line'
    if (line.includes('error') || line.includes('FAIL') || line.includes('Error:')) {
      cls += ' error'
    } else if (line.includes('success') || line.includes('[OK]') || line.includes('completed') || line.includes(':done')) {
      cls += ' success'
    } else if (line.includes('[info]') || line.includes('[now-sdk]') || line.includes('[build:') || line.includes('[deploy:')) {
      cls += ' info'
    }
    return html`<div class="${cls}">${line}</div>`
  }

  render() {
    return html`
      <div class="console-header">
        <div class="console-title">
          <span class="live-dot"></span>
          now-sdk Live Output (WebSocket)
        </div>
        <div class="console-actions">
          <button class="action-btn" title="Clear Console Logs" data-tooltip="Clear Logs" @click=${() => this.dispatchEvent(new CustomEvent('clear-logs'))}>
            <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
          </button>
        </div>
      </div>
      <div class="log-stream">
        ${this.logs.length === 0
          ? html`<div style="color: var(--now-text-muted); font-style: italic;">Ready. Waiting for now-sdk build or deploy commands...</div>`
          : this.logs.map((line) => this.formatLine(line))}
      </div>
    `
  }
}
