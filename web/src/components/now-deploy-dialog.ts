// web/src/components/now-deploy-dialog.ts
// Dialog that seeds a demo bundle's records into an instance, with rollback of that run.
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { CatalogInstance, DemoBundle } from './demo-catalog-model.js';
import { demoCatalogStyles } from './now-demo-catalog-styles.js';

/** Seeds `bundle` into a chosen instance; raises `demo-deploy` on success and `close`. */
@customElement('now-deploy-dialog')
export class NowDeployDialog extends LitElement {
  static styles = [
    demoCatalogStyles,
    css`
      :host {
        display: contents;
      }
    `,
  ];

  @property({ attribute: false }) bundle!: DemoBundle;
  @state() private deployInstances: CatalogInstance[] = [];
  @state() private selectedDeployInstanceId = '';
  @state() private isDeploying = false;
  @state() private deployError = '';
  @state() private deploySuccess = '';
  @state() private lastOperationId = '';

  connectedCallback(): void {
    super.connectedCallback();
    void this.loadInstancesForDeploy();
  }

  private close(): void {
    this.dispatchEvent(new CustomEvent('close'));
  }

  private async loadInstancesForDeploy(): Promise<void> {
    this.deployInstances = []
    this.selectedDeployInstanceId = ''
    try {
      const res = await fetch('/api/instances')
      if (!res.ok) {
        this.deployError = `Could not load instances: HTTP ${res.status}`
        return
      }
      const list = (await res.json()) as CatalogInstance[]
      if (!list || list.length === 0) {
        this.deployError = 'No ServiceNow instances registered'
        return
      }
      this.deployInstances = list
      const def = list.find((i) => i.is_default) ?? list[0]
      this.selectedDeployInstanceId = def.id
    } catch (e) {
      this.deployError = `Could not load instances: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  private async submitDeploy() {
    this.isDeploying = true
    this.deployError = ''
    this.deploySuccess = ''
    try {
      const res = await fetch(`/api/demos/${this.bundle.manifest.id}/seed`, {
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
        detail: { bundleId: this.bundle.manifest.id, instanceId: this.selectedDeployInstanceId },
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
        if (data.success === false) {
          // Partial rollback: keep the operation id so the user can retry (deletes are idempotent).
          const failures = Array.isArray(data.errors) ? data.errors.join('; ') : 'unknown error'
          this.deployError = `Rollback incomplete (${data.deleted_count} removed): ${failures}`
        } else {
          this.deploySuccess = `Rolled back successfully (${data.deleted_count} records removed).`
          this.lastOperationId = ''
        }
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

  render() {
    return html`
      <div class="modal-overlay" @click=${(e: Event) => {
        if (e.target === e.currentTarget) this.close();
      }}>
        <div class="modal-card">
          <div class="modal-header">
            <h2>Deploy & Seed Demonstration</h2>
            <button class="btn-secondary icon-btn modal-close" title="Close" data-tooltip="Close" @click=${this.close}>
              <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </button>
          </div>
          <div class="modal-body">
            <p style="font-size: 13px; color: var(--now-text-secondary); margin: 0;">
              Deploy Fluent metadata and transactionally seed records from <strong>${this.bundle.manifest.name}</strong> into your ServiceNow environment.
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
            ${this.deployError ? html`<div class="modal-error" data-testid="deploy-error">${this.deployError}</div>` : ''}
          </div>

          <div class="modal-footer">
            ${this.lastOperationId
              ? html`
                  <button class="btn-secondary icon-btn" ?disabled=${this.isDeploying} title="Rollback Seeded Records" data-tooltip="Rollback" @click=${this.rollbackDeploy} style="color: #b91c1c;">
                    <svg viewBox="0 0 24 24"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C20.93 11.13 17.07 8 12.5 8z"/></svg>
                  </button>
                `
              : ''}
            <button class="btn-secondary icon-btn" ?disabled=${this.isDeploying} title="Close" data-tooltip="Close" @click=${this.close}>
              <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </button>
            ${!this.deploySuccess
              ? html`
                  <button class="btn-primary icon-btn" data-testid="deploy-submit" ?disabled=${this.isDeploying || !this.selectedDeployInstanceId} title="Deploy Demo Now" data-tooltip="Deploy Now" @click=${this.submitDeploy}>
                    <svg viewBox="0 0 24 24"><path d="M12 2.5s-4.5 4.5-4.5 10c0 2.21 1.79 4 4 4s4-1.79 4-4c0-5.5-4.5-10-4.5-10zm0 11.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm-5.5-1.5c0-1.87.67-3.6 1.8-5-1.4.9-2.5 2.3-2.9 4 .4.4.8.7 1.1 1zm11 0c.3-.3.7-.6 1.1-1-.4-1.7-1.5-3.1-2.9-4 1.13 1.4 1.8 3.13 1.8 5zM7.5 19l-1.5 2.5h12L16.5 19z"/></svg>
                  </button>
                `
              : ''}
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-deploy-dialog': NowDeployDialog;
  }
}
