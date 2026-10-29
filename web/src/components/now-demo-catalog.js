var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
let NowDemoCatalog = class NowDemoCatalog extends LitElement {
    constructor() {
        super(...arguments);
        this.demos = [];
    }
    static { this.styles = css `
    :host {
      display: block;
      padding: 24px 32px;
      overflow-y: auto;
      height: 100%;
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .title-block h1 {
      font-size: 20px;
      font-weight: 600;
      color: var(--now-text-primary);
    }

    .title-block p {
      font-size: 13px;
      color: var(--now-text-secondary);
      margin-top: 4px;
    }

    .btn-primary {
      background: linear-gradient(135deg, var(--now-color-accent-teal), #0284c7);
      color: #0c1218;
      font-weight: 600;
      font-size: 13px;
      padding: 8px 16px;
      border-radius: var(--now-radius-sm);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: opacity 0.15s ease;
    }

    .btn-primary:hover {
      opacity: 0.9;
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 20px;
    }

    .demo-card {
      background-color: var(--now-bg-surface-1);
      border: 1px solid var(--now-border-subtle);
      border-radius: var(--now-radius-md);
      padding: 20px;
      display: flex;
      flex-direction: column;
      box-shadow: var(--now-shadow-card);
      transition: transform 0.15s ease, border-color 0.15s ease;
      position: relative;
    }

    .demo-card:hover {
      border-color: var(--now-border-highlight);
      transform: translateY(-2px);
    }

    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }

    .demo-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--now-text-primary);
    }

    .release-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 12px;
      background-color: rgba(43, 210, 181, 0.15);
      color: var(--now-color-accent-teal);
      border: 1px solid rgba(43, 210, 181, 0.3);
    }

    .demo-desc {
      font-size: 13px;
      color: var(--now-text-secondary);
      flex: 1;
      margin-bottom: 16px;
      line-height: 1.45;
    }

    .metadata-bar {
      display: flex;
      gap: 16px;
      padding: 10px 0;
      border-top: 1px solid var(--now-border-subtle);
      border-bottom: 1px solid var(--now-border-subtle);
      margin-bottom: 16px;
      font-size: 12px;
      color: var(--now-text-muted);
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .meta-val {
      color: var(--now-text-primary);
      font-weight: 500;
    }

    .tags-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }

    .tag-pill {
      font-size: 11px;
      background-color: var(--now-bg-surface-2);
      color: var(--now-text-secondary);
      padding: 2px 8px;
      border-radius: var(--now-radius-sm);
    }

    .card-actions {
      display: flex;
      gap: 8px;
    }

    .btn-secondary {
      background-color: var(--now-bg-surface-2);
      border: 1px solid var(--now-border-medium);
      color: var(--now-text-primary);
      padding: 6px 12px;
      border-radius: var(--now-radius-sm);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background-color 0.15s ease;
      flex: 1;
      justify-content: center;
    }

    .btn-secondary:hover {
      background-color: var(--now-bg-surface-elevated);
    }

    .btn-otto {
      background-color: rgba(168, 85, 247, 0.15);
      border: 1px solid rgba(168, 85, 247, 0.4);
      color: #d8b4fe;
      padding: 6px 10px;
      border-radius: var(--now-radius-sm);
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .btn-otto:hover {
      background-color: rgba(168, 85, 247, 0.25);
    }
  `; }
    handleDeploy(demo) {
        this.dispatchEvent(new CustomEvent('demo-deploy', {
            detail: { bundleId: demo.manifest.id },
            bubbles: true,
            composed: true,
        }));
    }
    handleExport(demo) {
        window.location.href = `/api/demos/${demo.manifest.id}/export`;
    }
    askOtto(demo) {
        this.dispatchEvent(new CustomEvent('otto-prompt', {
            detail: {
                text: `Tell me about the '${demo.manifest.name}' demo package and summarize its walkthrough script.`,
                context: { bundleId: demo.manifest.id, release: demo.manifest.sn_release }
            },
            bubbles: true,
            composed: true,
        }));
    }
    render() {
        return html `
      <div class="header-row">
        <div class="title-block">
          <h1>Demonstration Packages</h1>
          <p>Deploy, inspect, and export portable ServiceNow SDK application bundles</p>
        </div>
        <button class="btn-primary" @click=${() => alert('Import bundle: Drag and drop a .sn-demo.zip archive or select a file.')}>
          + Import Package
        </button>
      </div>

      <div class="cards-grid">
        ${this.demos.map((d) => html `
          <div class="demo-card">
            <div class="card-top">
              <span class="demo-title">${d.manifest.name}</span>
              <span class="release-badge">${d.manifest.sn_release}</span>
            </div>

            <p class="demo-desc">${d.manifest.description || 'No description provided.'}</p>

            <div class="metadata-bar">
              <div class="meta-item">
                <span>Fluent:</span>
                <span class="meta-val">${d.fluent_files.length}</span>
              </div>
              <div class="meta-item">
                <span>Seed Data:</span>
                <span class="meta-val">${d.seed_files.length}</span>
              </div>
              <div class="meta-item">
                <span>Guide:</span>
                <span class="meta-val">${d.has_walkthrough ? 'Yes' : 'No'}</span>
              </div>
            </div>

            <div class="tags-row">
              ${d.manifest.tags.map((t) => html `<span class="tag-pill">${t}</span>`)}
            </div>

            <div class="card-actions">
              <button class="btn-secondary" @click=${() => this.handleDeploy(d)}>
                🚀 Deploy
              </button>
              <button class="btn-secondary" @click=${() => this.handleExport(d)}>
                📦 Export
              </button>
              <button class="btn-otto" title="Ask Otto about this demo" @click=${() => this.askOtto(d)}>
                ✨ Otto
              </button>
            </div>
          </div>
        `)}
      </div>
    `;
    }
};
__decorate([
    property({ type: Array })
], NowDemoCatalog.prototype, "demos", void 0);
NowDemoCatalog = __decorate([
    customElement('now-demo-catalog')
], NowDemoCatalog);
export { NowDemoCatalog };
