// web/src/views/now-item-panel.ts
// Right-hand detail panel shown beside the conversation when a tile is opened.
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { PanelItem } from './panel-items.js';

@customElement('now-item-panel')
export class NowItemPanel extends LitElement {
  @property({ attribute: false }) item: PanelItem | null = null;

  static styles = css`
    :host {
      display: block;
      width: 340px;
      flex: none;
    }
    aside {
      margin: 24px 24px 24px 0;
      background: #ffffff;
      border-radius: 16px;
      padding: 18px 20px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
      font-family: inherit;
    }
    header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
    }
    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
    .sub {
      font-size: 12px;
      color: #6b7280;
      word-break: break-all;
      margin-top: 2px;
    }
    .close {
      border: none;
      background: transparent;
      font-size: 18px;
      line-height: 1;
      cursor: pointer;
      color: #4b5563;
    }
    dl {
      margin: 16px 0;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 8px 14px;
      font-size: 13px;
    }
    dt {
      color: #6b7280;
    }
    dd {
      margin: 0;
      font-weight: 500;
      word-break: break-word;
    }
    .go {
      width: 100%;
      border: none;
      border-radius: 999px;
      padding: 9px 14px;
      font: inherit;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      background: #1a4d63;
      color: #ffffff;
    }
  `;

  private emit(name: string, detail?: unknown): void {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  render() {
    const item = this.item;
    if (!item) return html``;
    return html`
      <aside aria-label="Details">
        <header>
          <div>
            <h3>${item.title}</h3>
            ${item.subtitle ? html`<div class="sub">${item.subtitle}</div>` : ''}
          </div>
          <button class="close" aria-label="Close details" @click=${() => this.emit('panel-close')}>&times;</button>
        </header>
        <dl>${item.rows.map((r) => html`<dt>${r.label}</dt><dd>${r.value}</dd>`)}</dl>
        ${item.action
          ? html`<button class="go" @click=${() => this.emit('panel-action', item.action?.tab)}>${item.action.label}</button>`
          : ''}
      </aside>
    `;
  }
}
