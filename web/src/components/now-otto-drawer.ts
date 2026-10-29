import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

@customElement('now-otto-drawer')
export class NowOttoDrawer extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      width: 380px;
      background-color: var(--now-bg-surface-0);
      border-left: 1px solid var(--now-border-subtle);
      height: 100%;
      box-shadow: -4px 0 24px rgba(0, 0, 0, 0.4);
      z-index: 50;
      transition: width 0.2s ease;
    }

    .drawer-header {
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: linear-gradient(180deg, rgba(168, 85, 247, 0.08) 0%, transparent 100%);
      border-bottom: 1px solid var(--now-border-subtle);
    }

    .otto-brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .otto-avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: linear-gradient(135deg, #a855f7, #3b82f6);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 10px var(--now-color-accent-otto-glow);
      font-size: 14px;
    }

    .otto-title {
      font-weight: 600;
      font-size: 14px;
      color: var(--now-text-primary);
    }

    .otto-badge {
      font-size: 10px;
      font-weight: 600;
      background-color: rgba(168, 85, 247, 0.2);
      color: #c084fc;
      padding: 1px 6px;
      border-radius: 8px;
      border: 1px solid rgba(168, 85, 247, 0.4);
    }

    .close-btn {
      background: transparent;
      border: none;
      color: var(--now-text-secondary);
      cursor: pointer;
      font-size: 18px;
    }

    .close-btn:hover {
      color: var(--now-text-primary);
    }

    .chat-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .message {
      display: flex;
      flex-direction: column;
      gap: 4px;
      max-width: 90%;
    }

    .message.user {
      align-self: flex-end;
    }

    .message.assistant {
      align-self: flex-start;
    }

    .bubble {
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .message.user .bubble {
      background-color: var(--now-color-accent-teal);
      color: #0c1218;
      border-bottom-right-radius: 2px;
      font-weight: 500;
    }

    .message.assistant .bubble {
      background-color: var(--now-bg-surface-2);
      color: var(--now-text-primary);
      border: 1px solid var(--now-border-subtle);
      border-bottom-left-radius: 2px;
    }

    .suggestions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 8px 16px;
      border-top: 1px solid var(--now-border-subtle);
    }

    .suggestion-chip {
      background-color: var(--now-bg-surface-1);
      border: 1px solid var(--now-border-medium);
      color: var(--now-text-secondary);
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .suggestion-chip:hover {
      color: var(--now-text-primary);
      border-color: #a855f7;
      background-color: rgba(168, 85, 247, 0.1);
    }

    .input-bar {
      padding: 12px 16px;
      display: flex;
      gap: 8px;
      background-color: var(--now-bg-surface-0);
      border-top: 1px solid var(--now-border-subtle);
    }

    .input-bar input {
      flex: 1;
      background-color: var(--now-bg-surface-1);
      border: 1px solid var(--now-border-medium);
      border-radius: var(--now-radius-sm);
      padding: 8px 12px;
      color: var(--now-text-primary);
      font-size: 13px;
      outline: none;
    }

    .input-bar input:focus {
      border-color: #a855f7;
    }

    .send-btn {
      background: linear-gradient(135deg, #a855f7, #3b82f6);
      color: white;
      border: none;
      border-radius: var(--now-radius-sm);
      padding: 0 14px;
      font-weight: 600;
      cursor: pointer;
    }
  `

  @property({ type: Boolean }) open = true
  @state() private messages: Message[] = [
    {
      role: 'assistant',
      content: "Hi Pierre! I'm Otto, your ServiceNow AI copilot. I can help navigate demos, diagnose now-sdk build logs, and synthesize mock data."
    }
  ]
  @state() private inputValue = ''
  private ws: WebSocket | null = null

  connectedCallback() {
    super.connectedCallback()
    this.initWebSocket()
  }

  disconnectedCallback() {
    super.disconnectedCallback()
    this.ws?.close()
  }

  private initWebSocket() {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${proto}//${window.location.host}/ws/otto`
    try {
      this.ws = new WebSocket(wsUrl)
      this.ws.onmessage = (evt) => {
        const data = JSON.parse(evt.data)
        if (data.type === 'chunk') {
          const last = this.messages[this.messages.length - 1]
          if (last && last.role === 'assistant') {
            last.content += data.text
            this.requestUpdate()
          }
        }
      }
    } catch {
      // WS fallback handled gracefully
    }
  }

  public sendMessage(text: string) {
    if (!text.trim()) return

    this.messages = [
      ...this.messages,
      { role: 'user', content: text },
      { role: 'assistant', content: '' }
    ]
    this.inputValue = ''

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        messages: this.messages.slice(0, -1),
        context: { activeWorkspace: 'sample-ai-assistant', release: 'Xanadu' }
      }))
    } else {
      // Offline fallback
      setTimeout(() => {
        const last = this.messages[this.messages.length - 1]
        last.content = `I received your request: "${text}". Connect the backend server and configure WORKBENCH_ANTHROPIC_API_KEY for real-time Claude streaming.`
        this.requestUpdate()
      }, 400)
    }
  }

  private handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      this.sendMessage(this.inputValue)
    }
  }

  render() {
    if (!this.open) return html``

    return html`
      <div class="drawer-header">
        <div class="otto-brand">
          <div class="otto-avatar">✨</div>
          <span class="otto-title">Otto</span>
          <span class="otto-badge">Now Assist</span>
        </div>
        <button class="close-btn" @click=${() => this.dispatchEvent(new CustomEvent('close-otto'))}>×</button>
      </div>

      <div class="chat-body">
        ${this.messages.map((m) => html`
          <div class="message ${m.role}">
            <div class="bubble">${m.content}</div>
          </div>
        `)}
      </div>

      <div class="suggestions-row">
        <button class="suggestion-chip" @click=${() => this.sendMessage('Explain how Fluent SDK compiles Table schemas')}>
          💡 Fluent SDK Schema
        </button>
        <button class="suggestion-chip" @click=${() => this.sendMessage('Check demo bundle compatibility with Xanadu release')}>
          🔍 Check Xanadu Compatibility
        </button>
        <button class="suggestion-chip" @click=${() => this.sendMessage('Generate 5 mock incident seed records in JSON')}>
          🧪 Generate Seed Data
        </button>
      </div>

      <div class="input-bar">
        <input
          type="text"
          placeholder="Ask Otto anything about this demo..."
          .value=${this.inputValue}
          @input=${(e: Event) => this.inputValue = (e.target as HTMLInputElement).value}
          @keydown=${this.handleKeyDown}
        />
        <button class="send-btn" @click=${() => this.sendMessage(this.inputValue)}>Send</button>
      </div>
    `
  }
}
