import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'

export interface DemoBundle {
  manifest: {
    id: string
    name: string
    version: string
    description: string
    sn_release: string
    min_release?: string
    required_plugins: string[]
    tags: string[]
    author?: string
    created_at?: string
    personas?: Array<{ name: string; role: string; email: string }>
  }
  bundle_path: string
  fluent_files: string[]
  seed_files: string[]
  has_walkthrough: boolean
  media_captures?: Array<{
    id: string
    bundle_id: string
    instance_url: string
    target_path: string
    media_type: 'screenshot' | 'video'
    label: string
    filename: string
    url: string
    engine: string
    created_at?: string
  }>
}

interface CatalogInstance {
  id: string
  name: string
  release: string
  is_default: boolean
}

@customElement('now-demo-catalog')
export class NowDemoCatalog extends LitElement {
  static styles = css`
    :host {
      display: block;
      padding: 24px 32px;
      overflow-y: auto;
      height: 100%;
      background-color: var(--now-bg-canvas);
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .title-block h1 {
      font-size: 20px;
      font-weight: 700;
      color: var(--now-text-primary);
    }

    .title-block p {
      font-size: 13px;
      color: var(--now-text-secondary);
      margin-top: 4px;
    }

    .btn-primary {
      background-color: var(--now-color-brand-green);
      color: #ffffff;
      font-weight: 600;
      font-size: 13px;
      padding: 8px 16px;
      border-radius: var(--now-radius-sm);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover {
      background-color: var(--now-color-brand-green-hover);
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 20px;
    }

    .demo-card {
      background-color: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle);
      border-radius: var(--now-radius-md);
      padding: 20px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.05);
      transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
      position: relative;
    }

    .demo-card:hover {
      border-color: var(--now-color-brand-green);
      box-shadow: 0 8px 16px -2px rgba(15, 23, 42, 0.08);
      transform: translateY(-2px);
    }

    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 10px;
    }

    .demo-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary);
    }

    .release-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: var(--now-radius-pill);
      background-color: #f0fdf4;
      color: #16a34a;
      border: 1px solid #bbf7d0;
    }

    .demo-desc {
      font-size: 13px;
      color: var(--now-text-secondary);
      flex: 1;
      margin-bottom: 16px;
      line-height: 1.5;
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
      font-weight: 600;
    }

    .tags-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }

    .tag-pill {
      font-size: 11px;
      font-weight: 500;
      background-color: var(--now-bg-surface-1);
      color: var(--now-text-secondary);
      padding: 2px 8px;
      border-radius: var(--now-radius-pill);
      border: 1px solid var(--now-border-subtle);
    }

    .card-actions {
      display: flex;
      gap: 8px;
    }

    .btn-secondary {
      background-color: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-medium);
      color: var(--now-text-primary);
      padding: 6px 12px;
      border-radius: var(--now-radius-sm);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background-color 0.15s ease;
      flex: 1;
      justify-content: center;
    }

    .btn-secondary:hover {
      background-color: var(--now-bg-surface-1);
    }

    .btn-danger {
      color: #dc2626 !important;
      border-color: #fecaca !important;
    }

    .btn-danger:hover {
      background-color: #fef2f2 !important;
      border-color: #dc2626 !important;
    }

    .btn-otto {
      background-color: #faf5ff;
      border: 1px solid #e9d5ff;
      color: #7e22ce;
      padding: 6px 12px;
      border-radius: var(--now-radius-sm);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: background-color 0.15s ease;
    }

    .btn-otto:hover {
      background-color: #f3e8ff;
    }

    .icon-btn {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      width: 36px;
      height: 36px;
      border-radius: var(--now-radius-sm, 6px);
      flex: 0 0 36px;
    }

    .icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.5);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .modal-card {
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: var(--now-radius-md, 8px);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      width: 480px;
      max-width: 90vw;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .modal-header h2 {
      font-size: 17px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      margin: 0;
    }

    .modal-body {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .modal-input-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .modal-input-field label {
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-primary, #334155);
    }

    .modal-input-field input {
      font-size: 13px;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid var(--now-border-medium, #cbd5e1);
      background: var(--now-bg-surface-1, #fafaf9);
      color: var(--now-text-primary, #111827);
      outline: none;
    }

    .modal-input-field input:focus {
      border-color: var(--now-color-brand-green, #23a17e);
    }

    .modal-error {
      font-size: 12px;
      color: #dc2626;
      background: #fef2f2;
      border: 1px solid #fecaca;
      padding: 6px 10px;
      border-radius: 6px;
    }

    .modal-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 8px;
    }

    .card-date-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      color: var(--now-text-secondary, #64748b);
      margin-bottom: 8px;
    }

    .media-proofs-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: var(--now-radius-sm, 6px);
      margin-bottom: 14px;
      font-size: 11.5px;
    }

    .media-proofs-summary {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--now-text-secondary, #475569);
    }

    .btn-proofs {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1d4ed8;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
    }

    .btn-proofs:hover {
      background: #dbeafe;
    }

    .proof-item {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 8px;
      background: var(--now-bg-surface-1, #f8fafc);
    }

    .proof-media-wrapper {
      max-height: 220px;
      border-radius: 6px;
      overflow: hidden;
      background: #032d42;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .proof-media-wrapper img,
    .proof-media-wrapper video {
      max-width: 100%;
      max-height: 220px;
      object-fit: contain;
    }
  `

  @property({ type: Array }) demos: DemoBundle[] = []
  @state() private cloningBundle: DemoBundle | null = null
  @state() private cloneName = ''
  @state() private cloneSlug = ''
  @state() private cloneError = ''
  @state() private isCloning = false

  // Deployment state
  @state() private deployingBundle: DemoBundle | null = null
  @state() private deployInstances: CatalogInstance[] = []
  @state() private selectedDeployInstanceId = ''
  @state() private isDeploying = false
  @state() private deployError = ''
  @state() private deploySuccess = ''
  @state() private lastOperationId = ''
  @state() private catalogNotification = ''
  @state() private viewingMediaBundle: DemoBundle | null = null

  private formatBundleDate(isoString?: string): string {
    if (!isoString) return 'Active Package';
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  }

  connectedCallback(): void {
    super.connectedCallback()
    if (!this.demos || this.demos.length === 0) {
      void this.loadDemos()
    }
  }

  private async loadDemos(): Promise<void> {
    try {
      const res = await fetch('/api/demos')
      if (res.ok) {
        this.demos = await res.json()
      }
    } catch {
      // Offline fallback
    }
  }

  private startClone(demo: DemoBundle) {
    this.cloningBundle = demo
    this.cloneName = `${demo.manifest.name} (Custom)`
    this.cloneSlug = `${demo.manifest.id}-clone`
    this.cloneError = ''
  }

  private closeCloneModal() {
    this.cloningBundle = null
    this.cloneError = ''
    this.isCloning = false
  }

  private async submitClone() {
    if (!this.cloningBundle) return
    const slug = this.cloneSlug.trim().toLowerCase()
    if (!slug) {
      this.cloneError = 'Please provide a unique target bundle slug.'
      return
    }
    this.isCloning = true
    this.cloneError = ''
    try {
      const res = await fetch(`/api/demos/${this.cloningBundle.manifest.id}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_bundle_id: slug,
          target_name: this.cloneName.trim() || undefined,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        this.cloneError = err.detail || 'Failed to clone demonstration bundle.'
        this.isCloning = false
        return
      }
      this.closeCloneModal()
      await this.loadDemos()
      this.dispatchEvent(new CustomEvent('demos-changed', { bubbles: true, composed: true }))
    } catch (e) {
      this.cloneError = `Network error: ${e}`
      this.isCloning = false
    }
  }

  private async loadInstancesForDeploy(): Promise<void> {
    try {
      const res = await fetch('/api/instances')
      if (res.ok) {
        const list = (await res.json()) as CatalogInstance[]
        if (list && list.length > 0) {
          this.deployInstances = list
          if (!this.selectedDeployInstanceId) {
            const def = list.find((i) => i.is_default) ?? list[0]
            this.selectedDeployInstanceId = def.id
          }
          return
        }
      }
    } catch {
      // Offline fallback
    }
    this.deployInstances = [
      {
        id: 'demo-trial-main',
        name: 'Alec Demo Trial (Primary)',
        release: 'Zurich',
        is_default: true,
      },
    ]
    this.selectedDeployInstanceId = 'demo-trial-main'
  }

  private async startDeploy(demo: DemoBundle) {
    this.deployingBundle = demo
    this.deployError = ''
    this.deploySuccess = ''
    this.lastOperationId = ''
    await this.loadInstancesForDeploy()
  }

  private closeDeployModal() {
    this.deployingBundle = null
    this.deployError = ''
    this.deploySuccess = ''
    this.isDeploying = false
  }

  private async submitDeploy() {
    if (!this.deployingBundle) return
    this.isDeploying = true
    this.deployError = ''
    this.deploySuccess = ''
    try {
      const res = await fetch(`/api/demos/${this.deployingBundle.manifest.id}/seed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instance_id: this.selectedDeployInstanceId || undefined,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        this.deployError = err.detail || 'Failed to deploy demonstration.'
        this.isDeploying = false
        return
      }
      const data = await res.json()
      const targetInst = this.deployInstances.find((i) => i.id === this.selectedDeployInstanceId)
      const count = data.created_records ? data.created_records.length : 0
      this.lastOperationId = data.id || ''
      this.deploySuccess = `Successfully seeded ${count} records into ${targetInst?.name || 'target instance'}!`
      this.isDeploying = false
      this.dispatchEvent(new CustomEvent('demo-deploy', {
        detail: { bundleId: this.deployingBundle.manifest.id, instanceId: this.selectedDeployInstanceId },
        bubbles: true,
        composed: true,
      }))
    } catch (e) {
      this.deployError = `Deployment error: ${e}`
      this.isDeploying = false
    }
  }

  private async rollbackDeploy() {
    if (!this.lastOperationId) return
    this.isDeploying = true
    try {
      const res = await fetch(`/api/demos/seed/${this.lastOperationId}/rollback`, {
        method: 'POST',
      })
      if (res.ok) {
        const data = await res.json()
        this.deploySuccess = `Rolled back successfully (${data.deleted_count} records removed).`
        this.lastOperationId = ''
      } else {
        const err = await res.json()
        this.deployError = err.detail || 'Rollback failed.'
      }
    } catch (e) {
      this.deployError = `Rollback error: ${e}`
    } finally {
      this.isDeploying = false
    }
  }

  private handleDeploy(demo: DemoBundle) {
    void this.startDeploy(demo)
  }

  private handleExport(demo: DemoBundle) {
    window.location.href = `/api/demos/${demo.manifest.id}/export`
  }

  private askOtto(demo: DemoBundle) {
    this.dispatchEvent(new CustomEvent('otto-prompt', {
      detail: {
        text: `Tell me about the '${demo.manifest.name}' demo package and summarize its walkthrough script.`,
        context: { bundleId: demo.manifest.id, release: demo.manifest.sn_release }
      },
      bubbles: true,
      composed: true,
    }))
  }

  private async handleDeleteBundle(demo: DemoBundle): Promise<void> {
    const confirmed = window.confirm(
      `Are you sure you want to delete demonstration artifact "${demo.manifest.name}" (${demo.manifest.id})?\n\nThis will permanently delete the artifact from your bundles library.`
    );
    if (!confirmed) {
      return;
    }

    try {
      const res = await fetch(`/api/demos/${demo.manifest.id}`, { method: 'DELETE' });
      if (res.ok) {
        this.demos = this.demos.filter((d) => d.manifest.id !== demo.manifest.id);
        this.catalogNotification = `Artifact "${demo.manifest.name}" was successfully deleted.`;
      } else {
        const err = await res.json();
        this.catalogNotification = `Failed to delete artifact: ${err.detail || res.statusText}`;
      }
    } catch (e: any) {
      this.catalogNotification = `Error deleting artifact: ${e?.message || e}`;
    }
  }

  private async handleDeleteProof(bundle: DemoBundle, filename: string): Promise<void> {
    if (!window.confirm(`Delete capture proof '${filename}'?`)) return;
    try {
      const res = await fetch(
        `/api/demos/${encodeURIComponent(bundle.manifest.id)}/captures/${encodeURIComponent(filename)}`,
        { method: 'DELETE' }
      );
      if (res.ok) {
        if (bundle.media_captures) {
          bundle.media_captures = bundle.media_captures.filter((c) => c.filename !== filename);
        }
        await this.loadDemos();
        this.requestUpdate();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Failed to delete capture proof.');
      }
    } catch (e: any) {
      alert(`Error deleting capture: ${e.message}`);
    }
  }

  private async handleClearAllProofs(bundle: DemoBundle): Promise<void> {
    const count = bundle.media_captures?.length || 0;
    if (
      !window.confirm(
        `Delete all ${count} captured media proofs for '${bundle.manifest.name}'? This cannot be undone.`
      )
    )
      return;
    try {
      const res = await fetch(
        `/api/demos/${encodeURIComponent(bundle.manifest.id)}/captures`,
        { method: 'DELETE' }
      );
      if (res.ok) {
        bundle.media_captures = [];
        await this.loadDemos();
        this.requestUpdate();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || 'Failed to clear media proofs.');
      }
    } catch (e: any) {
      alert(`Error clearing captures: ${e.message}`);
    }
  }

  render() {
    return html`
      <div class="header-row">
        <div class="title-block">
          <h1>Demonstration Packages</h1>
          <p>Deploy, inspect, and export portable ServiceNow SDK application bundles</p>
        </div>
        <button
          class="btn-primary icon-btn"
          title="Import Package Archive (.sn-demo.zip)"
          data-tooltip="Import Package"
          @click=${() => {
            this.catalogNotification =
              'Import Demo: Place your self-contained .sn-demo.zip archive into the bundles/ directory, or synthesize new bundles directly via the Synthesizer tab.';
          }}
        >
          <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>
        </button>
      </div>

      ${this.catalogNotification
        ? html`
            <div
              style="background: var(--now-bg-surface-1, #f1f5f9); border: 1px solid var(--now-border-subtle, #cbd5e1); border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; font-size: 13px; display: flex; justify-content: space-between; align-items: center;"
            >
              <span>${this.catalogNotification}</span>
              <button
                style="background: none; border: none; cursor: pointer; font-weight: 700; color: var(--now-text-secondary, #64748b); font-size: 14px;"
                @click=${() => {
                  this.catalogNotification = '';
                }}
              >
                [X]
              </button>
            </div>
          `
        : ''}

      <div class="cards-grid">
        ${this.demos.map((d) => html`
          <div class="demo-card">
            <div class="card-top">
              <span class="demo-title">${d.manifest.name}</span>
              <span class="release-badge" title="Minimum required ServiceNow platform version">Min: ${d.manifest.min_release || d.manifest.sn_release}</span>
            </div>

            <div class="card-date-badge">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              <span>Created: ${this.formatBundleDate(d.manifest.created_at)}</span>
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
              ${d.manifest.tags.map((t) => html`<span class="tag-pill">${t}</span>`)}
            </div>

            <div class="media-proofs-bar">
              <div class="media-proofs-summary">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                  <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8 12.5v-9l6 4.5-6 4.5z"/>
                </svg>
                <span>
                  ${d.media_captures && d.media_captures.length > 0
                    ? `${d.media_captures.length} Media Artifact(s) (${d.media_captures.filter((c) => c.media_type === 'video').length} video, ${d.media_captures.filter((c) => c.media_type === 'screenshot').length} screenshot)`
                    : '0 media proofs recorded'}
                </span>
              </div>
              ${d.media_captures && d.media_captures.length > 0
                ? html`
                    <button
                      class="btn-proofs"
                      @click=${() => {
                        this.viewingMediaBundle = d;
                      }}
                      title="Inspect screenshots and video proofs"
                    >
                      View Proofs (${d.media_captures.length})
                    </button>
                  `
                : ''}
            </div>

            <div class="card-actions">
              <button class="btn-secondary icon-btn" title="Deploy & Seed Demonstration" data-tooltip="Deploy" @click=${() => this.handleDeploy(d)}>
                <svg viewBox="0 0 24 24"><path d="M12 2.5s-4.5 4.5-4.5 10c0 2.21 1.79 4 4 4s4-1.79 4-4c0-5.5-4.5-10-4.5-10zm0 11.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm-5.5-1.5c0-1.87.67-3.6 1.8-5-1.4.9-2.5 2.3-2.9 4 .4.4.8.7 1.1 1zm11 0c.3-.3.7-.6 1.1-1-.4-1.7-1.5-3.1-2.9-4 1.13 1.4 1.8 3.13 1.8 5zM7.5 19l-1.5 2.5h12L16.5 19z"/></svg>
              </button>
              <button class="btn-secondary icon-btn" title="Clone Demonstration Bundle" data-tooltip="Clone" @click=${() => this.startClone(d)}>
                <svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
              </button>
              <button class="btn-secondary icon-btn" title="Export Demonstration Package (.sn-demo.zip)" data-tooltip="Export" @click=${() => this.handleExport(d)}>
                <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>
              </button>
              <button class="btn-otto icon-btn" title="Ask Otto Copilot about this demo" data-tooltip="Otto AI" @click=${() => this.askOtto(d)}>
                <svg viewBox="0 0 24 24"><path d="M19 9l1.25-2.75L23 5l-2.75-1.25L19 1l-1.25 2.75L15 5l2.75 1.25L19 9zm-7.5.5L9 4 6.5 9.5 1 12l5.5 2.5L9 20l2.5-5.5L17 12l-5.5-2.5zM19 15l-1.25 2.75L15 19l2.75 1.25L19 23l1.25-2.75L23 19l-2.75-1.25L19 15z"/></svg>
              </button>
              <button class="btn-secondary icon-btn btn-danger" title="Delete Demonstration Artifact" data-tooltip="Delete" @click=${() => this.handleDeleteBundle(d)}>
                <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
              </button>
            </div>
          </div>
        `)}
      </div>

      ${this.cloningBundle
        ? html`
            <div class="modal-overlay" @click=${(e: Event) => {
              if (e.target === e.currentTarget) this.closeCloneModal();
            }}>
              <div class="modal-card">
                <div class="modal-header">
                  <h2>Clone Demonstration Bundle</h2>
                  <button class="btn-secondary icon-btn" style="flex: 0 0 32px; width: 32px; height: 32px;" title="Close" data-tooltip="Close" @click=${this.closeCloneModal}>
                    <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                  </button>
                </div>
                <div class="modal-body">
                  <p style="font-size: 13px; color: var(--now-text-secondary); margin: 0;">
                    Duplicate baseline <strong>${this.cloningBundle.manifest.name}</strong> to create an isolated customer demo package without modifying baseline reference content.
                  </p>

                  <div class="modal-input-field">
                    <label>Target Demonstration Name</label>
                    <input
                      type="text"
                      .value=${this.cloneName}
                      @input=${(e: Event) => {
                        this.cloneName = (e.target as HTMLInputElement).value;
                      }}
                      placeholder="e.g. Novartis BioHealth Custom Demo"
                    />
                  </div>

                  <div class="modal-input-field">
                    <label>Unique Target Slug (Folder ID)</label>
                    <input
                      type="text"
                      .value=${this.cloneSlug}
                      @input=${(e: Event) => {
                        this.cloneSlug = (e.target as HTMLInputElement).value;
                      }}
                      placeholder="e.g. novartis-biohealth-demo"
                    />
                  </div>

                  ${this.cloneError ? html`<div class="modal-error">${this.cloneError}</div>` : ''}
                </div>

                <div class="modal-footer">
                  <button class="btn-secondary icon-btn" ?disabled=${this.isCloning} title="Cancel" data-tooltip="Cancel" @click=${this.closeCloneModal}>
                    <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                  </button>
                  <button class="btn-primary icon-btn" ?disabled=${this.isCloning} title="Create Cloned Demo" data-tooltip="Create Clone" @click=${this.submitClone}>
                    <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                  </button>
                </div>
              </div>
            </div>
          `
        : ''}

      ${this.deployingBundle
        ? html`
            <div class="modal-overlay" @click=${(e: Event) => {
              if (e.target === e.currentTarget) this.closeDeployModal();
            }}>
              <div class="modal-card">
                <div class="modal-header">
                  <h2>Deploy & Seed Demonstration</h2>
                  <button class="btn-secondary icon-btn" style="flex: 0 0 32px; width: 32px; height: 32px;" title="Close" data-tooltip="Close" @click=${this.closeDeployModal}>
                    <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                  </button>
                </div>
                <div class="modal-body">
                  <p style="font-size: 13px; color: var(--now-text-secondary); margin: 0;">
                    Deploy Fluent metadata and transactionally seed records from <strong>${this.deployingBundle.manifest.name}</strong> into your ServiceNow environment.
                  </p>

                  <div class="modal-input-field">
                    <label>Target ServiceNow Instance</label>
                    <select
                      style="font-size: 13px; padding: 8px 12px; border-radius: 6px; border: 1px solid var(--now-border-medium, #cbd5e1); outline: none;"
                      .value=${this.selectedDeployInstanceId}
                      @change=${(e: Event) => {
                        this.selectedDeployInstanceId = (e.target as HTMLSelectElement).value;
                      }}
                    >
                      ${this.deployInstances.map(
                        (inst) => html`
                          <option value=${inst.id} ?selected=${inst.id === this.selectedDeployInstanceId}>
                            ${inst.name} (${inst.release})
                          </option>
                        `
                      )}
                    </select>
                  </div>

                  ${this.deploySuccess
                    ? html`
                        <div style="font-size: 13px; color: #166534; background: #f0fdf4; border: 1px solid #bbf7d0; padding: 10px 12px; border-radius: 6px;">
                          ${this.deploySuccess}
                        </div>
                      `
                    : ''}
                  ${this.deployError ? html`<div class="modal-error">${this.deployError}</div>` : ''}
                </div>

                <div class="modal-footer">
                  ${this.lastOperationId
                    ? html`
                        <button class="btn-secondary icon-btn" ?disabled=${this.isDeploying} title="Rollback Seeded Records" data-tooltip="Rollback" @click=${this.rollbackDeploy} style="color: #b91c1c;">
                          <svg viewBox="0 0 24 24"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C20.93 11.13 17.07 8 12.5 8z"/></svg>
                        </button>
                      `
                    : ''}
                  <button class="btn-secondary icon-btn" ?disabled=${this.isDeploying} title="Close" data-tooltip="Close" @click=${this.closeDeployModal}>
                    <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                  </button>
                  ${!this.deploySuccess
                    ? html`
                        <button class="btn-primary icon-btn" ?disabled=${this.isDeploying} title="Deploy Demo Now" data-tooltip="Deploy Now" @click=${this.submitDeploy}>
                          <svg viewBox="0 0 24 24"><path d="M12 2.5s-4.5 4.5-4.5 10c0 2.21 1.79 4 4 4s4-1.79 4-4c0-5.5-4.5-10-4.5-10zm0 11.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm-5.5-1.5c0-1.87.67-3.6 1.8-5-1.4.9-2.5 2.3-2.9 4 .4.4.8.7 1.1 1zm11 0c.3-.3.7-.6 1.1-1-.4-1.7-1.5-3.1-2.9-4 1.13 1.4 1.8 3.13 1.8 5zM7.5 19l-1.5 2.5h12L16.5 19z"/></svg>
                        </button>
                      `
                    : ''}
                </div>
              </div>
            </div>
          `
        : ''}

      ${this.viewingMediaBundle
        ? html`
            <div
              class="modal-overlay"
              @click=${(e: Event) => {
                if (e.target === e.currentTarget) this.viewingMediaBundle = null;
              }}
            >
              <div class="modal-card" style="width: 800px; max-width: 95vw; max-height: 85vh; overflow-y: auto;">
                <div class="modal-header">
                  <div>
                    <h2 style="margin: 0; font-size: 16px;">
                      Media Proofs: ${this.viewingMediaBundle.manifest.name}
                    </h2>
                    <div style="font-size: 12px; color: var(--now-text-secondary, #64748b); margin-top: 4px;">
                      Package created: ${this.formatBundleDate(this.viewingMediaBundle.manifest.created_at)} | Min Platform: ${this.viewingMediaBundle.manifest.min_release || this.viewingMediaBundle.manifest.sn_release}
                    </div>
                  </div>
                  <div style="display: flex; gap: 8px; align-items: center;">
                    ${this.viewingMediaBundle.media_captures && this.viewingMediaBundle.media_captures.length > 0
                      ? html`
                          <button
                            class="btn-secondary"
                            style="color: #dc2626; border-color: #fca5a5; font-size: 12px; padding: 4px 10px; font-weight: 600;"
                            @click=${() => this.handleClearAllProofs(this.viewingMediaBundle!)}
                            title="Delete all captured media for this bundle"
                          >
                            Clear All (${this.viewingMediaBundle.media_captures.length})
                          </button>
                        `
                      : ''}
                    <button
                      class="btn-secondary icon-btn"
                      style="flex: 0 0 32px; width: 32px; height: 32px;"
                      title="Close"
                      @click=${() => {
                        this.viewingMediaBundle = null;
                      }}
                    >
                      <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                    </button>
                  </div>
                </div>

                <div class="modal-body" style="display: flex; flex-direction: column; gap: 14px; padding: 10px 0;">
                  ${this.viewingMediaBundle.media_captures && this.viewingMediaBundle.media_captures.length > 0
                    ? this.viewingMediaBundle.media_captures.map(
                        (cap) => html`
                          <div class="proof-item">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                              <div style="font-weight: 600; font-size: 13px;">
                                ${cap.label || cap.filename}
                              </div>
                              <span style="font-size: 11px; font-weight: 700; color: #16a34a; background: #f0fdf4; border: 1px solid #bbf7d0; padding: 1px 6px; border-radius: 999px;">
                                ${cap.media_type.toUpperCase()}
                              </span>
                            </div>

                            <div class="proof-media-wrapper">
                              ${cap.media_type === 'video'
                                ? html`<video src=${cap.url} controls muted playsinline></video>`
                                : html`<img src=${cap.url} alt=${cap.label || cap.filename} />`}
                            </div>

                            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--now-text-secondary, #64748b);">
                              <div style="display: flex; align-items: center; gap: 4px;">
                                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                                  <line x1="16" y1="2" x2="16" y2="6" />
                                  <line x1="8" y1="2" x2="8" y2="6" />
                                  <line x1="3" y1="10" x2="21" y2="10" />
                                </svg>
                                <span>Recorded: ${this.formatBundleDate(cap.created_at)}</span>
                              </div>
                              <div style="display: flex; gap: 8px; align-items: center;">
                                <a
                                  href=${cap.url}
                                  target="_blank"
                                  rel="noopener"
                                  style="color: #2563eb; font-weight: 600; text-decoration: none;"
                                >
                                  Open in Tab
                                </a>
                                <a
                                  href=${cap.url}
                                  download=${cap.filename}
                                  style="color: #16a34a; font-weight: 600; text-decoration: none;"
                                >
                                  Download
                                </a>
                                <button
                                  class="btn-secondary"
                                  style="color: #dc2626; border-color: #fca5a5; font-size: 11px; padding: 2px 8px; font-weight: 600; cursor: pointer;"
                                  @click=${() => this.handleDeleteProof(this.viewingMediaBundle!, cap.filename)}
                                  title="Delete this capture proof"
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          </div>
                        `
                      )
                    : html`<p style="font-size: 13px; color: var(--now-text-muted);">No media proofs recorded.</p>`}
                </div>

                <div class="modal-footer">
                  <button
                    class="btn-secondary"
                    @click=${() => {
                      this.viewingMediaBundle = null;
                    }}
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          `
        : ''}
    `
  }
}
