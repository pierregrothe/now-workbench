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
      background: transparent;
      border: none;
      color: var(--now-text-muted);
      cursor: pointer;
      font-size: 11px;
    }

    .action-btn:hover {
      color: var(--now-text-primary);
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

  updated() {
    const el = this.shadowRoot?.querySelector('.log-stream')
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }

  render() {
    return html`
      <div class="console-header">
        <div class="console-title">
          <span class="live-dot"></span>
          now-sdk Live Output
        </div>
        <div class="console-actions">
          <button class="action-btn" @click=${() => this.dispatchEvent(new CustomEvent('clear-logs'))}>
            Clear
          </button>
        </div>
      </div>
      <div class="log-stream">
        ${this.logs.length === 0
          ? html`<div style="color: var(--now-text-muted); font-style: italic;">Ready. Waiting for now-sdk build or deploy commands...</div>`
          : this.logs.map((line) => html`<div>${line}</div>`)}
      </div>
    `
  }
}
