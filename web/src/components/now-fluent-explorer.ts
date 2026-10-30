import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'

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
  @state() private copySuccess = false

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--now-bg-canvas, #f8fafc);
      overflow: hidden;
      font-family: inherit;
    }

    .header-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 24px;
      background: var(--now-bg-surface-0, #ffffff);
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .title-icon {
      font-size: 20px;
    }

    .title-text {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
    }

    .bundle-badge {
      font-size: 11.5px;
      padding: 3px 10px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1d4ed8;
      border-radius: 9999px;
      font-weight: 600;
    }

    .actions-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .btn {
      position: relative;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }

    .btn.icon-btn {
      width: 32px;
      height: 32px;
      padding: 0;
      justify-content: center;
      border-radius: 6px;
    }

    .btn.icon-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }

    .btn-secondary {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-border-subtle, #cbd5e1);
      color: var(--now-text-primary, #0f172a);
    }

    .btn-secondary:hover {
      background: var(--now-bg-surface-1, #f8fafc);
      border-color: #94a3b8;
    }

    .explorer-body {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    .tables-sidebar {
      width: 280px;
      background: var(--now-bg-surface-0, #ffffff);
      border-right: 1px solid var(--now-border-subtle, #e2e8f0);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 12px;
      gap: 6px;
    }

    .table-nav-btn {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid transparent;
      background: transparent;
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      transition: background-color 0.1s ease;
    }

    .table-nav-btn:hover {
      background: var(--now-bg-surface-1, #f1f5f9);
    }

    .table-nav-btn.active {
      background: #f0fdf4;
      border-color: #bbf7d0;
    }

    .table-nav-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .table-col-count {
      font-size: 11px;
      padding: 2px 7px;
      background: var(--now-bg-surface-2, #e2e8f0);
      border-radius: 12px;
      color: var(--now-text-primary, #475569);
      font-weight: 600;
    }

    .table-nav-btn.active .table-col-count {
      background: var(--now-color-brand-green, #293e40);
      color: #ffffff;
    }

    .schema-detail {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 24px;
      gap: 20px;
    }

    .table-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 10px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      padding: 20px;
    }

    .table-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 12px;
    }

    .table-headline {
      font-size: 18px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
    }

    .table-identifier {
      font-size: 12.5px;
      color: var(--now-text-secondary, #64748b);
      font-family: monospace;
      margin-top: 2px;
    }

    .columns-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    .columns-table th {
      text-align: left;
      padding: 10px 14px;
      background: var(--now-bg-surface-1, #f8fafc);
      color: var(--now-text-secondary, #64748b);
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
    }

    .columns-table td {
      padding: 12px 14px;
      border-bottom: 1px solid #f1f5f9;
      color: var(--now-text-primary, #0f172a);
    }

    .col-name {
      font-family: monospace;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .type-pill {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
      background: var(--now-bg-surface-1, #f1f5f9);
      font-weight: 600;
      color: var(--now-text-secondary, #334155);
    }

    .type-pill.reference {
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }

    .mandatory-pill {
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 4px;
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
      font-weight: 600;
    }

    .code-box {
      background: #1e293b;
      color: #e2e8f0;
      border-radius: 8px;
      padding: 16px;
      font-family: monospace;
      font-size: 12.5px;
      line-height: 1.5;
      overflow-x: auto;
      position: relative;
    }

    .copy-btn {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #ffffff;
      padding: 0;
      width: 28px;
      height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      cursor: pointer;
    }

    .copy-btn svg {
      width: 15px;
      height: 15px;
      fill: currentColor;
    }

    .copy-btn:hover {
      background: rgba(255, 255, 255, 0.2);
    }
  `

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
        this.error = 'No Fluent schema found for this bundle.'
      }
    } catch {
      this.tables = [
        {
          name: 'x_snc_ai_triage_case',
          label: 'AI Triage Case',
          columns: [
            {
              name: 'short_description',
              label: 'Short Description',
              column_type: 'StringColumn',
              reference: null,
              mandatory: true,
              max_length: 160,
            },
            {
              name: 'assigned_to',
              label: 'Assigned To',
              column_type: 'ReferenceColumn',
              reference: 'sys_user',
              mandatory: false,
              max_length: null,
            },
          ],
          raw_source:
            "export const x_snc_ai_triage_case = Table({\n  name: 'x_snc_ai_triage_case',\n  label: 'AI Triage Case',\n  schema: {\n    short_description: StringColumn({ label: 'Short Description', mandatory: true, maxLength: 160 }),\n    assigned_to: ReferenceColumn({ label: 'Assigned To', referenceTable: 'sys_user' }),\n  },\n});",
        },
      ]
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
    try {
      const resp = await fetch(`/api/demos/${this.bundleId}/fluent/diff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_bundle_id: this.bundleId }),
      })
      if (resp.ok) {
        this.diffResult = await resp.json()
      }
    } catch {
      this.diffResult = { identical: true, added_tables: [], removed_tables: [], modified_tables: {} }
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
