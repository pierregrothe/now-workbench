import { LitElement, html } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import '../views/now-share-dialog.js'
import { demoCatalogStyles } from './now-demo-catalog-styles.js'
import type { DemoBundle } from './demo-catalog-model.js'
import './now-clone-dialog.js'
import './now-deploy-dialog.js'

@customElement('now-demo-catalog')
export class NowDemoCatalog extends LitElement {
  static styles = demoCatalogStyles

  @property({ type: Array }) demos: DemoBundle[] = []
  @state() private cloningBundle: DemoBundle | null = null

  // Deployment state
  @state() private deployingBundle: DemoBundle | null = null
  @state() private catalogNotification = ''
  @state() private viewingMediaBundle: DemoBundle | null = null
  @state() private sharingBundle: DemoBundle | null = null

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
      if (!res.ok) {
        this.catalogNotification = `Could not load demo bundles (HTTP ${res.status}).`
        return
      }
      this.demos = await res.json()
    } catch (e) {
      // An unreachable backend is reported, never shown as an empty catalog (ADR-013).
      this.catalogNotification = `Could not load demo bundles: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  private startClone(demo: DemoBundle) {
    this.cloningBundle = demo
  }

  private readonly onCloned = async (): Promise<void> => {
    this.cloningBundle = null
    await this.loadDemos()
    this.dispatchEvent(new CustomEvent('demos-changed', { bubbles: true, composed: true }))
  }

  private startDeploy(demo: DemoBundle) {
    this.deployingBundle = demo
  }

  private handleDeploy(demo: DemoBundle) {
    this.startDeploy(demo)
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

            <div class="ownership-row">
              ${d.access === 'shared'
                ? html`<span class="own-chip shared">Shared by ${d.owner_email} &middot; v${d.version}</span>`
                : html`<span class="own-chip">Yours &middot; v${d.version ?? 0}</span>`}
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
              ${d.access === 'shared'
                ? ''
                : html`
                    <button class="btn-secondary icon-btn" title="Versions and sharing" aria-label="Share ${d.manifest.name}" data-tooltip="Share" @click=${() => (this.sharingBundle = d)}>
                      <svg viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z"/></svg>
                    </button>
                    <button class="btn-secondary icon-btn btn-danger" title="Delete Demonstration Artifact" data-tooltip="Delete" @click=${() => this.handleDeleteBundle(d)}>
                      <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    </button>
                  `}
            </div>
          </div>
        `)}
      </div>

      ${this.sharingBundle
        ? html`<now-share-dialog
            .artifactId=${this.sharingBundle.manifest.id}
            .artifactName=${this.sharingBundle.manifest.name}
            @close=${() => (this.sharingBundle = null)}
            @sharing-changed=${() => void this.loadDemos()}
          ></now-share-dialog>`
        : ''}

      ${this.cloningBundle
        ? html`<now-clone-dialog
            .bundle=${this.cloningBundle}
            @close=${() => (this.cloningBundle = null)}
            @cloned=${this.onCloned}
          ></now-clone-dialog>`
        : ''}

      ${this.deployingBundle
        ? html`<now-deploy-dialog
            .bundle=${this.deployingBundle}
            @close=${() => (this.deployingBundle = null)}
          ></now-deploy-dialog>`
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
