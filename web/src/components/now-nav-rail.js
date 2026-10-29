var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
let NowNavRail = class NowNavRail extends LitElement {
    constructor() {
        super(...arguments);
        this.activeTab = 'demos';
    }
    static { this.styles = css `
    :host {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 56px;
      background-color: var(--now-bg-surface-0);
      border-right: 1px solid var(--now-border-subtle);
      padding: 12px 0;
      gap: 16px;
      user-select: none;
    }

    .brand-mark {
      width: 34px;
      height: 34px;
      border-radius: var(--now-radius-sm);
      background: linear-gradient(135deg, var(--now-color-accent-teal), #0284c7);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 16px;
      color: #0b1219;
      margin-bottom: 8px;
    }

    .nav-btn {
      width: 40px;
      height: 40px;
      border-radius: var(--now-radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      color: var(--now-text-secondary);
      cursor: pointer;
      transition: all 0.15s ease;
      position: relative;
    }

    .nav-btn:hover {
      color: var(--now-text-primary);
      background-color: var(--now-bg-surface-1);
    }

    .nav-btn.active {
      color: var(--now-color-accent-teal);
      background-color: var(--now-bg-surface-2);
    }

    .nav-btn.active::before {
      content: '';
      position: absolute;
      left: 0;
      top: 8px;
      bottom: 8px;
      width: 3px;
      border-radius: 0 2px 2px 0;
      background-color: var(--now-color-accent-teal);
    }

    .spacer {
      flex: 1;
    }

    .icon {
      width: 20px;
      height: 20px;
      fill: currentColor;
    }
  `; }
    selectTab(tab) {
        this.activeTab = tab;
        this.dispatchEvent(new CustomEvent('tab-change', { detail: { tab }, bubbles: true, composed: true }));
    }
    render() {
        return html `
      <div class="brand-mark" title="ServiceNow Fluent SDK">⚡</div>

      <button
        class="nav-btn ${this.activeTab === 'demos' ? 'active' : ''}"
        title="Demonstration Packages"
        @click=${() => this.selectTab('demos')}
      >
        <svg class="icon" viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>
      </button>

      <button
        class="nav-btn ${this.activeTab === 'fluent' ? 'active' : ''}"
        title="Fluent SDK Studio"
        @click=${() => this.selectTab('fluent')}
      >
        <svg class="icon" viewBox="0 0 24 24"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>
      </button>

      <button
        class="nav-btn ${this.activeTab === 'diagnostics' ? 'active' : ''}"
        title="Instance Health & Diagnostics"
        @click=${() => this.selectTab('diagnostics')}
      >
        <svg class="icon" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/></svg>
      </button>

      <div class="spacer"></div>

      <button
        class="nav-btn ${this.activeTab === 'settings' ? 'active' : ''}"
        title="Settings & Credentials"
        @click=${() => this.selectTab('settings')}
      >
        <svg class="icon" viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
      </button>
    `;
    }
};
__decorate([
    property({ type: String })
], NowNavRail.prototype, "activeTab", void 0);
NowNavRail = __decorate([
    customElement('now-nav-rail')
], NowNavRail);
export { NowNavRail };
