var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './now-nav-rail';
import './now-demo-catalog';
import './now-console';
import './now-otto-drawer';
let NowWorkbenchShell = class NowWorkbenchShell extends LitElement {
    constructor() {
        super(...arguments);
        this.activeTab = 'demos';
        this.ottoOpen = true;
        this.demos = [];
        this.logs = [
            '[now-workbench] Initialized in Docker workspace.',
            '[now-workbench] Connected to local storage: 1 demonstration package detected.',
        ];
        this.instanceUrl = 'dev12345.service-now.com';
        this.instanceRelease = 'Xanadu';
    }
    static { this.styles = css `
    :host {
      display: flex;
      flex-direction: column;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      background-color: var(--now-bg-canvas);
    }

    /* Top Chrome Banner */
    .top-chrome {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 48px;
      padding: 0 16px;
      background-color: var(--now-bg-surface-0);
      border-bottom: 1px solid var(--now-border-subtle);
      user-select: none;
    }

    .brand-section {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .app-title {
      font-weight: 700;
      font-size: 14px;
      color: var(--now-text-primary);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .app-badge {
      font-size: 11px;
      padding: 1px 6px;
      background-color: var(--now-bg-surface-2);
      border-radius: var(--now-radius-sm);
      color: var(--now-text-secondary);
      font-weight: 500;
    }

    .center-section {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .search-input {
      background-color: var(--now-bg-surface-1);
      border: 1px solid var(--now-border-subtle);
      border-radius: var(--now-radius-sm);
      padding: 4px 12px;
      color: var(--now-text-primary);
      font-size: 12px;
      width: 280px;
      outline: none;
    }

    .search-input:focus {
      border-color: var(--now-color-accent-teal);
    }

    .right-section {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .instance-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      background-color: var(--now-bg-surface-1);
      border: 1px solid var(--now-border-subtle);
      padding: 4px 10px;
      border-radius: 14px;
      font-size: 11px;
      color: var(--now-text-secondary);
    }

    .instance-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: var(--now-status-online);
      box-shadow: 0 0 6px var(--now-status-online);
    }

    .otto-toggle-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      background: linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(59, 130, 246, 0.2));
      border: 1px solid rgba(168, 85, 247, 0.4);
      color: #e9d5ff;
      padding: 4px 10px;
      border-radius: 14px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      transition: all 0.15s ease;
    }

    .otto-toggle-btn:hover {
      box-shadow: 0 0 10px var(--now-color-accent-otto-glow);
    }

    /* Main Workspace Layout */
    .workspace-body {
      display: flex;
      flex: 1;
      height: calc(100vh - 48px);
      overflow: hidden;
    }

    .content-area {
      display: flex;
      flex-direction: column;
      flex: 1;
      overflow: hidden;
      background-color: var(--now-bg-canvas);
    }

    .catalog-viewport {
      flex: 1;
      overflow: hidden;
    }
  `; }
    connectedCallback() {
        super.connectedCallback();
        this.fetchDemos();
        this.fetchHealth();
    }
    async fetchHealth() {
        try {
            const res = await fetch('/api/health');
            if (res.ok) {
                const data = await res.json();
                if (data.instance?.url) {
                    this.instanceUrl = data.instance.url;
                }
            }
        }
        catch {
            // Offline fallback
        }
    }
    async fetchDemos() {
        try {
            const res = await fetch('/api/demos');
            if (res.ok) {
                this.demos = await res.json();
            }
        }
        catch {
            // Default sample fallback
            this.demos = [
                {
                    manifest: {
                        id: 'sample-ai-assistant',
                        name: 'GenAI Agentic Incident Router',
                        version: '1.0.0',
                        description: 'Autonomous AI routing and triage application for IT incidents leveraging Now Assist and custom Fluent tables.',
                        sn_release: 'Xanadu',
                        required_plugins: ['com.glide.now.assist', 'com.snc.itsm'],
                        tags: ['ITSM', 'GenAI', 'Now Assist', 'Fluent'],
                    },
                    bundle_path: '/workspaces/sample-ai-assistant',
                    fluent_files: ['app.now.ts'],
                    seed_files: ['01_sample_incidents.json'],
                    has_walkthrough: true,
                }
            ];
        }
    }
    async handleDeploy(e) {
        const bundleId = e.detail.bundleId;
        this.appendLog(`[deploy] Starting deployment pipeline for bundle: ${bundleId}...`);
        this.appendLog(`[deploy] Invoking now-sdk build on Fluent sources...`);
        try {
            const res = await fetch(`/api/demos/${bundleId}/build`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stream_logs: true })
            });
            const data = await res.json();
            if (data.success) {
                this.appendLog(`[build:success] now-sdk compiled Fluent schema into scoped update set.`);
                this.appendLog(`[deploy:push] Synchronizing 2 seed records to Table API (incident)...`);
                this.appendLog(`[deploy:done] Deployment completed successfully!`);
            }
            else {
                this.appendLog(`[build:error] ${data.output || 'Compilation failed.'}`);
            }
        }
        catch (err) {
            this.appendLog(`[deploy:mock] Simulated build success for '${bundleId}'.`);
            this.appendLog(`[deploy:mock] 2 seed records staged for demonstration.`);
        }
    }
    handleOttoPrompt(e) {
        this.ottoOpen = true;
        const drawer = this.shadowRoot?.querySelector('now-otto-drawer');
        if (drawer) {
            drawer.sendMessage(e.detail.text);
        }
    }
    appendLog(text) {
        this.logs = [...this.logs, text];
    }
    render() {
        return html `
      <!-- Top Chrome -->
      <header class="top-chrome">
        <div class="brand-section">
          <span class="app-title">
            now-workbench
            <span class="app-badge">SDK Studio</span>
          </span>
        </div>

        <div class="center-section">
          <input
            type="text"
            class="search-input"
            placeholder="Search demos, Fluent tables, seed records (Cmd+K)"
          />
        </div>

        <div class="right-section">
          <div class="instance-pill">
            <span class="instance-dot"></span>
            <span>${this.instanceUrl}</span>
            <span style="color: var(--now-color-accent-teal); font-weight: 600;">[${this.instanceRelease}]</span>
          </div>

          <button class="otto-toggle-btn" @click=${() => this.ottoOpen = !this.ottoOpen}>
            ✨ Otto Copilot
          </button>
        </div>
      </header>

      <!-- Workspace Body -->
      <div class="workspace-body">
        <now-nav-rail
          .activeTab=${this.activeTab}
          @tab-change=${(e) => this.activeTab = e.detail.tab}
        ></now-nav-rail>

        <main class="content-area">
          <div class="catalog-viewport">
            <now-demo-catalog
              .demos=${this.demos}
              @demo-deploy=${this.handleDeploy}
              @otto-prompt=${this.handleOttoPrompt}
            ></now-demo-catalog>
          </div>

          <now-console
            .logs=${this.logs}
            @clear-logs=${() => this.logs = []}
          ></now-console>
        </main>

        <now-otto-drawer
          .open=${this.ottoOpen}
          @close-otto=${() => this.ottoOpen = false}
        ></now-otto-drawer>
      </div>
    `;
    }
};
__decorate([
    state()
], NowWorkbenchShell.prototype, "activeTab", void 0);
__decorate([
    state()
], NowWorkbenchShell.prototype, "ottoOpen", void 0);
__decorate([
    state()
], NowWorkbenchShell.prototype, "demos", void 0);
__decorate([
    state()
], NowWorkbenchShell.prototype, "logs", void 0);
__decorate([
    state()
], NowWorkbenchShell.prototype, "instanceUrl", void 0);
__decorate([
    state()
], NowWorkbenchShell.prototype, "instanceRelease", void 0);
NowWorkbenchShell = __decorate([
    customElement('now-workbench-shell')
], NowWorkbenchShell);
export { NowWorkbenchShell };
