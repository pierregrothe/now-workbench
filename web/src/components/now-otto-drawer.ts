import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'

interface UITile {
  id: string
  type: string
  title: string
  props?: Record<string, any>
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  tiles?: UITile[]
}

@customElement('now-otto-drawer')
export class NowOttoDrawer extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      width: 380px;
      background-color: var(--now-bg-surface-0, #ffffff);
      border-left: 1px solid var(--now-border-subtle);
      height: 100%;
      box-shadow: -4px 0 24px rgba(15, 23, 42, 0.08);
      z-index: 50;
      transition: width 0.2s ease;
    }

    :host(:not([open])) {
      display: none !important;
      width: 0 !important;
      border: none !important;
      box-shadow: none !important;
    }

    .drawer-header {
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background-color: var(--now-bg-surface-0, #ffffff);
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
      background: linear-gradient(135deg, #9333ea, #3b82f6);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 10px rgba(147, 51, 234, 0.25);
      font-size: 13px;
      color: #ffffff;
    }

    .otto-title {
      font-weight: 700;
      font-size: 14px;
      color: var(--now-text-primary);
    }

    .otto-badge {
      font-size: 10.5px;
      font-weight: 600;
      background-color: #f3e8ff;
      color: #7e22ce;
      padding: 2px 7px;
      border-radius: 10px;
      border: 1px solid #e9d5ff;
    }

    .close-btn {
      position: relative;
      background: transparent;
      border: none;
      color: var(--now-text-muted);
      cursor: pointer;
      border-radius: 4px;
      padding: 0;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .close-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }

    .close-btn:hover {
      background-color: var(--now-bg-surface-1);
      color: var(--now-text-primary);
    }

    .chat-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background-color: var(--now-bg-canvas, #f8fafc);
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
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .message.user .bubble {
      background-color: var(--now-color-brand-green);
      color: #ffffff;
      border-bottom-right-radius: 2px;
      font-weight: 500;
    }

    .message.assistant .bubble {
      background-color: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary);
      border: 1px solid var(--now-border-subtle);
      border-bottom-left-radius: 2px;
      box-shadow: var(--now-shadow-sm);
    }

    .suggestions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 10px 16px;
      border-top: 1px solid var(--now-border-subtle);
      background-color: var(--now-bg-surface-0, #ffffff);
    }

    .suggestion-chip {
      background-color: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle);
      color: var(--now-text-secondary);
      font-size: 11.5px;
      font-weight: 500;
      padding: 5px 10px;
      border-radius: var(--now-radius-pill);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .suggestion-chip:hover {
      color: #7e22ce;
      border-color: #c084fc;
      background-color: #faf5ff;
    }

    .input-bar {
      padding: 12px 16px;
      display: flex;
      gap: 8px;
      background-color: var(--now-bg-surface-0, #ffffff);
      border-top: 1px solid var(--now-border-subtle);
    }

    .input-bar input {
      flex: 1;
      background-color: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-medium);
      border-radius: var(--now-radius-sm);
      padding: 8px 12px;
      color: var(--now-text-primary);
      font-size: 13px;
      outline: none;
      transition: border-color 0.15s ease;
    }

    .input-bar input:focus {
      border-color: var(--now-color-brand-green);
    }

    .send-btn {
      position: relative;
      background-color: var(--now-color-brand-green);
      color: white;
      border: none;
      border-radius: var(--now-radius-sm);
      width: 36px;
      height: 36px;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background-color 0.15s ease;
      flex-shrink: 0;
    }

    .send-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .send-btn:hover {
      background-color: var(--now-color-brand-green-hover);
    }

    .otto-tiles-container {
      margin-top: 10px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .drawer-media-tile {
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: var(--now-radius-sm, 6px);
      padding: 10px;
      overflow: hidden;
    }

    .drawer-media-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .drawer-media-title {
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .drawer-badge {
      font-size: 10px;
      font-weight: 700;
      background: var(--now-color-brand-green, #23a17e);
      color: white;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .drawer-media-label {
      font-size: 11px;
      color: var(--now-text-secondary, #64748b);
      margin-bottom: 6px;
    }

    .drawer-media-frame video,
    .drawer-media-frame img {
      width: 100%;
      max-height: 220px;
      border-radius: 4px;
      display: block;
      background: #000;
    }
  `

  @property({ type: Boolean }) open = true
  @state() private messages: Message[] = [
    {
      role: 'assistant',
      content: "Hello! I'm Otto, your ServiceNow AI assistant. How can I help with your Fluent tables, seed datasets, or demo bundles today?"
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
            if (last.content === 'Thinking and executing with Claude...') {
              last.content = data.text
            } else {
              last.content += data.text
            }
            this.requestUpdate()
          }
        } else if (data.type === 'tiles') {
          const last = this.messages[this.messages.length - 1]
          if (last && last.role === 'assistant') {
            last.tiles = data.tiles
            this.requestUpdate()
          }
        }
      }
    } catch {
      // Offline fallback
    }
  }

  public async sendMessage(text: string) {
    if (!text.trim()) return

    this.messages = [
      ...this.messages,
      { role: 'user', content: text },
      { role: 'assistant', content: 'Thinking and executing with Claude...' }
    ]
    this.inputValue = ''
    this.requestUpdate()

    let failure = ''
    try {
      const res = await fetch('/api/threads/thread-default/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'user', content: text })
      })
      if (res.ok) {
        const data = await res.json()
        const last = this.messages[this.messages.length - 1]
        if (last) {
          last.content = data.content || data.widget_data?.summary || 'Execution completed.'
          last.tiles = data.widget_data?.tiles || []
          this.requestUpdate()
        }
        return
      }
      failure = `HTTP ${res.status}`
    } catch (err) {
      failure = err instanceof Error ? err.message : String(err)
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        messages: this.messages.slice(0, -1),
        context: { activeWorkspace: 'sample-ai-assistant', release: 'Zurich' }
      }))
      return
    }

    const last = this.messages[this.messages.length - 1]
    if (last) {
      last.content = `Could not reach Otto: ${failure}`
      this.requestUpdate()
    }
  }

  private renderDrawerTile(tile: UITile) {
    const p = tile.props || {}
    const url = p.url || ''
    if (!url) {
      return html`
        <div class="drawer-media-tile">
          <div class="drawer-media-header">
            <span class="drawer-media-title">${tile.title || 'Result'}</span>
          </div>
          <div class="drawer-media-label">${p.body || tile.props?.summary || ''}</div>
        </div>
      `
    }
    const isVideo = p.media_type === 'video' || url.endsWith('.webm') || url.endsWith('.mp4')
    return html`
      <div class="drawer-media-tile">
        <div class="drawer-media-header">
          <span class="drawer-media-title">${tile.title || 'Demonstration Proof'}</span>
          <span class="drawer-badge">${isVideo ? 'VIDEO' : 'SCREENSHOT'}</span>
        </div>
        ${p.label ? html`<div class="drawer-media-label">${p.label}</div>` : ''}
        <div class="drawer-media-frame">
          ${isVideo
            ? html`<video src=${url} controls playsinline preload="metadata"></video>`
            : html`<img src=${url} alt=${tile.title || 'Proof Artifact'} />`}
        </div>
      </div>
    `
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
          <div class="otto-avatar">*</div>
        </div>
        <button class="close-btn" title="Close" data-tooltip="Close" @click=${() => this.dispatchEvent(new CustomEvent('close-otto'))}>
          <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>

      <div class="chat-body">
        ${this.messages.map((m) => html`
          <div class="message ${m.role}">
            <div class="bubble">${m.content}</div>
            ${m.tiles && m.tiles.length
              ? html`
                  <div class="otto-tiles-container">
                    ${m.tiles.map((t) => this.renderDrawerTile(t))}
                  </div>
                `
              : ''}
          </div>
        `)}
      </div>

      <div class="suggestions-row">
        <button class="suggestion-chip" @click=${() => this.sendMessage('Explain how Fluent SDK compiles Table schemas')}>
          [TIP] Fluent Table Schema
        </button>
        <button class="suggestion-chip" @click=${() => this.sendMessage('Check demo bundle compatibility with Xanadu & Zurich')}>
          [FIND] Check Compatibility
        </button>
        <button class="suggestion-chip" @click=${() => this.sendMessage('Generate 5 mock incident seed records in JSON')}>
           Generate Incident Seeds
        </button>
      </div>

      <div class="input-bar">
        <input
          type="text"
          placeholder="Ask Otto about Fluent or demos..."
          .value=${this.inputValue}
          @input=${(e: Event) => this.inputValue = (e.target as HTMLInputElement).value}
          @keydown=${this.handleKeyDown}
        />
        <button class="send-btn" title="Send message to Otto" data-tooltip="Send" @click=${() => this.sendMessage(this.inputValue)}>
          <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
    `
  }
}
