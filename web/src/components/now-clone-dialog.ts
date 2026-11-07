// web/src/components/now-clone-dialog.ts
// Dialog that clones a demo bundle into a new, independent bundle.
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, css, html, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import type { DemoBundle } from './demo-catalog-model.js';
import { demoCatalogStyles } from './now-demo-catalog-styles.js';

/** Clones `bundle`; raises `cloned` on success and `close` when dismissed (ADR-024). */
@customElement('now-clone-dialog')
export class NowCloneDialog extends LitElement {
  static styles = [
    demoCatalogStyles,
    css`
      :host {
        display: contents;
      }
    `,
  ];

  @property({ attribute: false }) bundle!: DemoBundle;
  @state() private cloneName = '';
  @state() private cloneSlug = '';
  @state() private cloneError = '';
  @state() private isCloning = false;

  protected willUpdate(changed: PropertyValues<this>): void {
    if (changed.has('bundle') && this.bundle) {
      this.cloneName = `${this.bundle.manifest.name} (Custom)`;
      this.cloneSlug = `${this.bundle.manifest.id}-clone`;
      this.cloneError = '';
    }
  }

  private close(): void {
    this.dispatchEvent(new CustomEvent('close'));
  }

  private async submitClone() {
    const slug = this.cloneSlug.trim().toLowerCase()
    if (!slug) {
      this.cloneError = 'Please provide a unique target bundle slug.'
      return
    }
    this.isCloning = true
    this.cloneError = ''
    try {
      const res = await fetch(`/api/demos/${this.bundle.manifest.id}/clone`, {
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
      this.dispatchEvent(new CustomEvent('cloned', { detail: { bundleId: slug } }))
    } catch (e) {
      this.cloneError = `Network error: ${e}`
      this.isCloning = false
    }
  }

  render() {
    return html`
      <div class="modal-overlay" @click=${(e: Event) => {
        if (e.target === e.currentTarget) this.close();
      }}>
        <div class="modal-card">
          <div class="modal-header">
            <h2>Clone Demonstration Bundle</h2>
            <button class="btn-secondary icon-btn" style="flex: 0 0 32px; width: 32px; height: 32px;" title="Close" data-tooltip="Close" @click=${this.close}>
              <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </button>
          </div>
          <div class="modal-body">
            <p style="font-size: 13px; color: var(--now-text-secondary); margin: 0;">
              Duplicate baseline <strong>${this.bundle.manifest.name}</strong> to create an isolated customer demo package without modifying baseline reference content.
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
            <button class="btn-secondary icon-btn" ?disabled=${this.isCloning} title="Cancel" data-tooltip="Cancel" @click=${this.close}>
              <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </button>
            <button class="btn-primary icon-btn" ?disabled=${this.isCloning} title="Create Cloned Demo" data-tooltip="Create Clone" @click=${this.submitClone}>
              <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            </button>
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-clone-dialog': NowCloneDialog;
  }
}
