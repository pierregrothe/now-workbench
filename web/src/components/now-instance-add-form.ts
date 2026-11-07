// web/src/components/now-instance-add-form.ts
// Form that registers a new ServiceNow instance (credentials are sealed server-side).
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { renderPurposeOptions } from './admin-instance-model.js';
import type { InstancePurpose } from '../context/instance-model.js';
import { adminSharedStyles } from './admin-shared-styles.js';
import { instanceAddFormStyles } from './now-instance-add-form-styles.js';

/** Registers an instance; raises `instance-added` (and `instance-changed` when made default). */
@customElement('now-instance-add-form')
export class NowInstanceAddForm extends LitElement {
  static styles = [adminSharedStyles, instanceAddFormStyles];

  @state() private isAdding = false;
  @state() private feedback = '';
  @state() private newName = '';
  @state() private newUrl = '';
  @state() private newUsername = 'admin';
  @state() private newPassword = '';
  @state() private newSetDefault = true;
  @state() private newPurpose: InstancePurpose = 'demo';

  private async addInstance(): Promise<void> {
    const cleanName = this.newName.trim();
    const cleanUrl = this.newUrl.trim();
    if (!cleanName || !cleanUrl) {
      this.feedback = 'Please provide both an instance alias and instance URL.';
      return;
    }

    this.isAdding = true;
    this.feedback = '';

    const id = cleanName.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-');
    try {
      const res = await fetch('/api/instances', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id,
          name: cleanName,
          url: cleanUrl,
          username: this.newUsername.trim() || 'admin',
          password: this.newPassword.trim(),
          purpose: this.newPurpose,
          is_default: this.newSetDefault,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        this.feedback = err.detail || 'Failed to register instance.';
        this.isAdding = false;
        return;
      }

      this.newName = '';
      this.newUrl = '';
      this.newPassword = '';
      this.feedback = `Successfully registered and connected '${cleanName}'.`;
      this.dispatchEvent(new CustomEvent('instance-added', { detail: { instanceId: id } }));
      if (this.newSetDefault) {
        this.dispatchEvent(
          new CustomEvent('instance-changed', {
            detail: { instanceId: id },
            bubbles: true,
            composed: true,
          })
        );
      }
    } catch (e) {
      this.feedback = `Registration failed: ${e}`;
    } finally {
      this.isAdding = false;
    }
  }

  render() {
    return html`
      <div class="section-card">
        <div>
          <h3 class="section-title">+ Connect New ServiceNow Instance</h3>
          <p class="section-desc">
            Register an additional demo sandbox, trial sub-production, or customer test environment. Credentials are encrypted in SQLite at rest.
          </p>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Instance Alias</label>
            <input
              type="text"
              class="form-input"
              placeholder="e.g. Novartis BioHealth Sub-Prod"
              .value=${this.newName}
              @input=${(e: Event) => (this.newName = (e.target as HTMLInputElement).value)}
            />
          </div>

          <div class="form-group">
            <label class="form-label">Instance URL</label>
            <input
              type="text"
              class="form-input"
              placeholder="https://instancename.service-now.com"
              .value=${this.newUrl}
              @input=${(e: Event) => (this.newUrl = (e.target as HTMLInputElement).value)}
            />
          </div>

          <div class="form-group">
            <label class="form-label">Admin Username</label>
            <input
              type="text"
              class="form-input"
              placeholder="admin"
              .value=${this.newUsername}
              @input=${(e: Event) => (this.newUsername = (e.target as HTMLInputElement).value)}
            />
          </div>

          <div class="form-group">
            <label class="form-label">Admin Password (Encrypted at Rest)</label>
            <input
              type="password"
              class="form-input"
              placeholder="Enter instance credentials"
              .value=${this.newPassword}
              @input=${(e: Event) => (this.newPassword = (e.target as HTMLInputElement).value)}
            />
          </div>

          <div class="form-group">
            <label class="form-label" for="new-purpose">Purpose</label>
            <select
              id="new-purpose"
              class="form-input"
              @change=${(e: Event) => (this.newPurpose = (e.target as HTMLSelectElement).value as InstancePurpose)}
            >
              ${renderPurposeOptions(this.newPurpose)}
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Target Role</label>
            <div class="form-toggle-row">
              <input
                type="checkbox"
                id="set-default-toggle"
                .checked=${this.newSetDefault}
                @change=${(e: Event) => (this.newSetDefault = (e.target as HTMLInputElement).checked)}
              />
              <label for="set-default-toggle">Mark as active default target immediately</label>
            </div>
          </div>

          <div class="form-actions-row">
            <button
              class="btn-register icon-btn"
              ?disabled=${this.isAdding || !this.newName.trim() || !this.newUrl.trim()}
              title="Connect Instance"
              data-tooltip="Connect Instance"
              @click=${this.addInstance}
            >
              <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            </button>
          </div>
        </div>
      </div>
      ${this.feedback
        ? html`<div class="status-feedback ${this.feedback.includes('failed') ? 'error' : 'success'}">${this.feedback}</div>`
        : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-instance-add-form': NowInstanceAddForm;
  }
}
