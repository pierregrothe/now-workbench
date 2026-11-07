// web/src/components/now-diagnostics-card.ts
// Platform runtime diagnostics: what the server reports, never assumed values (ADR-013).
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import type { DiagnosticsData } from './admin-instance-model.js';
import { adminSharedStyles } from './admin-shared-styles.js';
import { diagnosticsCardStyles } from './now-diagnostics-card-styles.js';

const OK = '#15803d';
const BAD = '#b91c1c';

@customElement('now-diagnostics-card')
export class NowDiagnosticsCard extends LitElement {
  static styles = [adminSharedStyles, diagnosticsCardStyles];

  @state() private diagnostics: DiagnosticsData | null = null;
  @state() private error = '';

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const res = await fetch('/api/admin/diagnostics');
      if (!res.ok) {
        this.error = `Diagnostics unavailable (HTTP ${res.status}).`;
        return;
      }
      this.diagnostics = (await res.json()) as DiagnosticsData;
    } catch (e) {
      this.error = `Diagnostics unreachable: ${e}`;
    }
  }

  private badge() {
    const tc = this.diagnostics?.toolchain;
    if (!tc) return html`<span class="status-badge ${this.error ? 'error' : 'unknown'}">${this.error ? 'Unavailable' : 'Checking'}</span>`;
    const ok = tc.node_available && tc.now_sdk_available;
    return html`<span class="status-badge ${ok ? 'authenticated' : 'error'}">${ok ? 'Operational' : 'Toolchain incomplete'}</span>`;
  }

  render() {
    const d = this.diagnostics;
    const tc = d?.toolchain;
    return html`
      <div class="section-card">
        <div class="section-header">
          <h3 class="section-title">Platform Runtime Diagnostics</h3>
          ${this.badge()}
        </div>
        ${this.error ? html`<div class="status-feedback error" role="alert">${this.error}</div>` : ''}
        <div class="diag-strip">
          <div class="diag-pill">
            <span class="diag-title">Python Engine</span>
            <span class="diag-content">${d ? `Python ${d.python_runtime}` : '--'}</span>
          </div>
          <div class="diag-pill">
            <span class="diag-title">Node.js Runtime</span>
            <span class="diag-content" style="color: ${tc?.node_available ? OK : BAD};">
              ${tc ? (tc.node_available ? 'Available' : 'Not found') : '--'}
            </span>
          </div>
          <div class="diag-pill">
            <span class="diag-title">ServiceNow SDK</span>
            <span class="diag-content" style="color: ${tc?.now_sdk_available ? OK : BAD};">
              ${tc ? (tc.now_sdk_available ? 'CLI Ready' : 'Not installed') : '--'}
            </span>
          </div>
          <div class="diag-pill">
            <span class="diag-title">Encrypted Storage</span>
            <span class="diag-content">SQLite WAL (PBKDF2)</span>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-diagnostics-card': NowDiagnosticsCard;
  }
}
