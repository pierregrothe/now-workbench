import { LitElement, html } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import { fluentExplorerStyles } from './now-fluent-explorer-styles.js'

export interface FluentColumn {
  name: string
  label: string
  column_type: string
  reference?: string | null
  mandatory: boolean
  max_length?: number | null
}

export interface FluentTable {
  name: string
  label: string
  columns: FluentColumn[]
  raw_source: string
}

@customElement('now-fluent-explorer')
export class NowFluentExplorer extends LitElement {
  @property({ type: String }) bundleId = 'sample-ai-assistant'
  @state() private availableBundles: Array<{ id: string; name: string }> = []
  @state() private tables: FluentTable[] = []
  @state() private selectedTableIndex = 0
  @state() private loading = true
  @state() private error = ''
  @state() private showDiff = false
  @state() private diffResult: any = null
  @state() private diffError = ''
  @state() private copySuccess = false

  static styles = fluentExplorerStyles

  connectedCallback() {
    super.connectedCallback()
    void this.loadAvailableBundles()
    void this.fetchSchemas()
  }

  private async loadAvailableBundles() {
    try {
      const resp = await fetch('/api/demos')
      if (resp.ok) {
        const list = (await resp.json()) as Array<{ manifest: { id: string; name: string } }>
        if (Array.isArray(list) && list.length > 0) {
          this.availableBundles = list.map((b) => ({
            id: b.manifest.id,
            name: b.manifest.name,
          }))
          if (!this.availableBundles.some((b) => b.id === this.bundleId)) {
            this.bundleId = this.availableBundles[0].id
          }
        }
      }
    } catch {
      // Offline fallback
    }
  }

  private handleBundleChange(e: Event) {
    const select = e.target as HTMLSelectElement
    this.bundleId = select.value
    this.selectedTableIndex = 0
    this.showDiff = false
    void this.fetchSchemas()
  }

  private async fetchSchemas() {
    this.loading = true
    this.error = ''
    try {
      const resp = await fetch(`/api/demos/${this.bundleId}/fluent`)
      if (resp.ok) {
        const data = await resp.json()
        this.tables = data.tables || []
      } else {
        this.tables = []
        this.error = `Could not load schemas: HTTP ${resp.status}`
      }
    } catch (err) {
      this.tables = []
      this.error = `Could not load schemas: ${err instanceof Error ? err.message : String(err)}`
    } finally {
      this.loading = false
    }
  }

  private copySource(code: string) {
    navigator.clipboard.writeText(code)
    this.copySuccess = true
    setTimeout(() => (this.copySuccess = false), 2000)
  }

  private async runSchemaDiff() {
    this.showDiff = !this.showDiff
    if (!this.showDiff) return
    this.diffResult = null
    this.diffError = ''
    try {
      const resp = await fetch(`/api/demos/${this.bundleId}/fluent/diff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_bundle_id: this.bundleId }),
      })
      if (resp.ok) {
        this.diffResult = await resp.json()
      } else {
        this.diffError = `Schema diff failed: HTTP ${resp.status}`
      }
    } catch (err) {
      this.diffError = `Schema diff failed: ${err instanceof Error ? err.message : String(err)}`
    }
  }

  render() {
    return html`
      <div class="header-bar">
        <div class="title-group">
          <span class="title-icon">[TS]</span>
          <div>
            <div class="title-text">ServiceNow Fluent SDK Studio</div>
            <div style="font-size: 12px; color: var(--now-text-secondary); margin-top: 2px;">
              Declarative TypeScript Schema Models (*.now.ts)
            </div>
          </div>
          <span class="bundle-badge">${this.bundleId}</span>
        </div>

        <div class="actions-group">
          ${this.availableBundles.length > 0
            ? html`
                <select
                  style="font-size: 12.5px; padding: 5px 10px; border-radius: 6px; border: 1px solid var(--now-border-subtle, #cbd5e1); background: var(--now-bg-surface-0, #ffffff); color: var(--now-text-primary, #0f172a); outline: none;"
                  .value=${this.bundleId}
                  @change=${this.handleBundleChange}
                  title="Switch active bundle schema"
                >
                  ${this.availableBundles.map(
                    (b) => html`
                      <option value=${b.id} ?selected=${b.id === this.bundleId}>
                        ${b.name} (${b.id})
                      </option>
                    `
                  )}
                </select>
              `
            : ''}
          <button class="btn btn-secondary icon-btn" title="Compare Schema Diff" data-tooltip="Compare Diff" @click=${this.runSchemaDiff}>
            <svg viewBox="0 0 24 24"><path d="M10 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h5v2h2V1h-2v2zm-5 16V5h5v14H5zm14-14h-5v2h5v14h-5v2h5c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/></svg>
          </button>
          <button class="btn btn-secondary icon-btn" title="Reload Schemas" data-tooltip="Reload Schemas" @click=${this.fetchSchemas}>
            <svg viewBox="0 0 24 24"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
          </button>
        </div>
      </div>

      <div class="explorer-body">
        <!-- Tables List Sidebar -->
        <div class="tables-sidebar">
          <div style="font-size: 11.5px; font-weight: 700; color: #64748b; margin-bottom: 8px; text-transform: uppercase;">
            Declared Tables (${this.tables.length})
          </div>

          ${this.tables.map(
            (tbl, idx) => html`
              <button
                class="table-nav-btn ${idx === this.selectedTableIndex ? 'active' : ''}"
                @click=${() => (this.selectedTableIndex = idx)}
              >
                <div>
                  <div class="table-nav-name">${tbl.label}</div>
                  <div style="font-size: 11px; color: #64748b; font-family: monospace;">${tbl.name}</div>
                </div>
                <span class="table-col-count">${tbl.columns.length}</span>
              </button>
            `
          )}
        </div>

        <!-- Schema Details -->
        <div class="schema-detail">
          ${this.showDiff && this.diffError
            ? html`<div data-testid="diff-error" style="padding: 12px; color: #dc2626;">${this.diffError}</div>`
            : ''}
          ${this.showDiff && this.diffResult
            ? html`
                <div class="table-card" style="border-left: 4px solid #0284c7;">
                  <div class="table-headline" style="font-size: 15px; margin-bottom: 8px;">
                    Baseline Schema Diff (${this.bundleId})
                  </div>
                  <div style="font-size: 13px; color: #334155;">
                    ${this.diffResult.identical
                      ? html`<span style="color: #15803d; font-weight: 600;">[OK] Working tree schema matches bundle baseline (0 drift).</span>`
                      : html`<span>Modified tables: ${Object.keys(this.diffResult.modified_tables || {}).join(', ')}</span>`}
                  </div>
                </div>
              `
            : ''}
          ${this.renderTableContent()}
        </div>
      </div>
    `
  }

  private renderTableContent() {
    if (this.loading) {
      return html`<div style="padding: 40px; text-align: center; color: #64748b;">Loading Fluent schema AST...</div>`
    }
    if (this.error) {
      return html`<div style="padding: 40px; text-align: center; color: #dc2626;">${this.error}</div>`
    }
    if (this.tables.length === 0) {
      return html`<div style="padding: 40px; text-align: center; color: #64748b;">No Fluent tables found in this bundle.</div>`
    }

    const currentTable = this.tables[this.selectedTableIndex]
    if (!currentTable) return html``

    return html`
      <div class="table-card">
        <div class="table-card-header">
          <div>
            <div class="table-headline">${currentTable.label}</div>
            <div class="table-identifier">${currentTable.name}</div>
          </div>
          <span class="bundle-badge">${currentTable.columns.length} Columns</span>
        </div>

        <table class="columns-table">
          <thead>
            <tr>
              <th>Column Name</th>
              <th>Label</th>
              <th>Type</th>
              <th>Reference Table</th>
              <th>Mandatory</th>
              <th>Max Length</th>
            </tr>
          </thead>
          <tbody>
            ${currentTable.columns.map(
              (col) => html`
                <tr>
                  <td class="col-name">${col.name}</td>
                  <td>${col.label}</td>
                  <td>
                    <span class="type-pill ${col.column_type === 'reference' ? 'reference' : ''}">
                      ${col.column_type}
                    </span>
                  </td>
                  <td>
                    ${col.reference
                      ? html`<span class="col-name" style="color: #1d4ed8;">${col.reference}</span>`
                      : html`<span style="color: #94a3b8;">-</span>`}
                  </td>
                  <td>
                    ${col.mandatory
                      ? html`<span class="mandatory-pill">Required</span>`
                      : html`<span style="color: #94a3b8;">Optional</span>`}
                  </td>
                  <td>${col.max_length ? col.max_length : html`<span style="color: #94a3b8;">-</span>`}</td>
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>

      <!-- Raw Source Code -->
      <div class="table-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div style="font-weight: 700; font-size: 14px; color: #0f172a;">Declarative TypeScript (*.now.ts)</div>
        </div>
        <div class="code-box">
          <button class="copy-btn" title="Copy Source Code" data-tooltip="Copy Code" @click=${() => this.copySource(currentTable.raw_source)}>
            ${this.copySuccess
              ? html`<svg viewBox="0 0 24 24"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg>`
              : html`<svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>`}
          </button>
          <pre style="margin: 0;"><code>${currentTable.raw_source}</code></pre>
        </div>
      </div>
    `
  }
}
