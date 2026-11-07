import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { purposeLabel, renderPurposeOptions } from './admin-instance-model.js';
import type { InstanceData, InstancePurpose } from '../context/instance-model.js';
import { adminSharedStyles } from './admin-shared-styles.js';
import { adminPanelStyles } from './now-admin-panel-styles.js';
import './now-diagnostics-card.js';
import './now-instance-add-form.js';
import './now-instance-hero.js';


@customElement('now-admin-panel')
export class NowAdminPanel extends LitElement {
  static styles = [adminSharedStyles, adminPanelStyles];

  @property({ type: Boolean }) open = true;
  @state() private instances: InstanceData[] = [];
  @state() private instancesError = '';
  @state() private testingInstanceId: string | null = null;
  @state() private actionFeedback: string = '';
  @state() private editingInstanceId: string | null = null;
  @state() private editName: string = '';
  @state() private editUrl: string = '';
  @state() private editUsername: string = '';
  @state() private editPassword: string = '';
  @state() private editRelease = '';
  @state() private confirmingDeleteId: string | null = null;
  @state() private isSavingEdit = false;

  // New instance form fields
  @state() private editPurpose: InstancePurpose = 'demo';

  connectedCallback(): void {
    super.connectedCallback();
    void this.refreshData();
  }

  private async refreshData(): Promise<void> {
    try {
      const instRes = await fetch('/api/instances');
      if (instRes.ok) {
        const data = await instRes.json();
        // Render exactly what the registry holds -- an empty registry stays empty (ADR-011).
        this.instances = Array.isArray(data) ? data : [];
        this.instancesError = '';
      } else {
        this.instancesError = `Instance registry unavailable (HTTP ${instRes.status}).`;
      }
    } catch (e) {
      this.instancesError = `Instance registry unreachable: ${e}`;
    }
  }

  private async activateInstance(id: string): Promise<void> {
    this.actionFeedback = '';
    try {
      const res = await fetch(`/api/instances/${id}/activate`, { method: 'POST' });
      if (res.ok) {
        this.actionFeedback = 'Target instance activated successfully.';
        await this.refreshData();
        this.dispatchEvent(
          new CustomEvent('instance-changed', {
            detail: { instanceId: id },
            bubbles: true,
            composed: true,
          })
        );
      }
    } catch (e) {
      this.actionFeedback = `Activation failed: ${e}`;
    }
  }

  private async testInstance(id: string): Promise<void> {
    this.testingInstanceId = id;
    this.actionFeedback = '';
    try {
      const res = await fetch(`/api/instances/${id}/test`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        this.actionFeedback = data.success
          ? `Authenticated successfully as '${data.username}' (HTTP ${data.http_code})`
          : `Test result: ${data.status} - ${data.message || 'Verification failed'}`;
        this.dispatchEvent(
          new CustomEvent('instance-changed', {
            detail: { instanceId: id, status: data.status },
            bubbles: true,
            composed: true,
          })
        );
      } else {
        this.actionFeedback = 'Test failed with HTTP error.';
      }
      await this.refreshData();
    } catch (e) {
      this.actionFeedback = `Connectivity test failed: ${e}`;
    } finally {
      this.testingInstanceId = null;
    }
  }

  private startEdit(inst: InstanceData): void {
    this.editingInstanceId = inst.id;
    this.editName = inst.name;
    this.editUrl = inst.url;
    this.editUsername = inst.username;
    this.editPassword = '';
    this.editRelease = inst.release;
    this.editPurpose = inst.purpose;
    this.confirmingDeleteId = null;
    this.actionFeedback = '';
  }

  private cancelEdit(): void {
    this.editingInstanceId = null;
    this.confirmingDeleteId = null;
  }

  private async saveEdit(id: string): Promise<void> {
    this.isSavingEdit = true;
    this.actionFeedback = '';
    try {
      const payload: Record<string, string> = {
        name: this.editName.trim(),
        url: this.editUrl.trim(),
        username: this.editUsername.trim(),
        purpose: this.editPurpose,
      };
      if (this.editPassword.trim()) {
        payload.password = this.editPassword.trim();
      }
      const res = await fetch(`/api/instances/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        this.actionFeedback = `Updated instance '${this.editName}'.`;
        this.editingInstanceId = null;
        await this.refreshData();
        this.dispatchEvent(new CustomEvent('instance-changed', { bubbles: true, composed: true }));
      } else {
        const err = await res.json();
        this.actionFeedback = err.detail || 'Failed to update instance.';
      }
    } catch (e) {
      this.actionFeedback = `Update error: ${e}`;
    } finally {
      this.isSavingEdit = false;
    }
  }

  private async deleteInstance(id: string): Promise<void> {
    this.actionFeedback = '';
    try {
      const res = await fetch(`/api/instances/${id}`, { method: 'DELETE' });
      if (res.ok) {
        this.actionFeedback = 'Instance deleted from registry.';
        this.confirmingDeleteId = null;
        this.editingInstanceId = null;
        await this.refreshData();
        this.dispatchEvent(new CustomEvent('instance-changed', { bubbles: true, composed: true }));
      } else {
        const err = await res.json();
        this.actionFeedback = err.detail || 'Failed to delete instance.';
      }
    } catch (e) {
      this.actionFeedback = `Delete error: ${e}`;
    }
  }


  render() {
    const activeInst = this.instances.find((i) => i.is_default) || this.instances[0];
    const authCount = this.instances.filter((i) => i.status === 'authenticated').length;

    return html`
      <div class="instances-scroll">
        <div class="instances-container">
          ${activeInst
            ? html`<now-instance-hero
                .instance=${activeInst}
                ?testing=${this.testingInstanceId === activeInst.id}
                @edit-instance=${() => this.startEdit(activeInst)}
                @test-instance=${() => this.testInstance(activeInst.id)}
              ></now-instance-hero>`
            : ''}

          <!-- 2. Registered Instances Table -->
          <div class="section-card">
            <div class="section-header">
              <div>
                <h3 class="section-title">Connected Sub-Production Instances (${this.instances.length})</h3>
                <p class="section-desc">
                  Select default target for Table API demo record seeding, Fluent deployments, and screenshot capture.
                </p>
              </div>
              <span class="status-badge authenticated">
                <span class="dot-indicator"></span>
                ${authCount}/${this.instances.length} Authenticated
              </span>
            </div>

            <div class="table-wrapper">
              <table class="instances-table">
                <thead>
                  <tr>
                    <th>Instance</th>
                    <th>Release</th>
                    <th>User</th>
                    <th>Auth Status</th>
                    <th>Role</th>
                    <th style="text-align: right;">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.instances.length === 0
                    ? html`<tr>
                        <td colspan="6" class="empty-state" data-testid="instances-empty">
                          ${this.instancesError ||
                          'No ServiceNow instances registered yet. Add one below to get started.'}
                        </td>
                      </tr>`
                    : ''}
                  ${this.instances.map(
                    (inst) => html`
                      <tr>
                        <td>
                          <div class="instance-name-col">
                            <span class="inst-title">${inst.name}</span>
                            <a
                              class="inst-url-sub"
                              href=${inst.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              ${inst.url}
                            </a>
                          </div>
                        </td>
                        <td>
                          <span style="font-weight: 600; color: #475467;">${inst.release}</span>
                          <span
                            class="env-badge ${inst.purpose === 'production' ? 'prod' : ''}"
                            data-testid="row-purpose"
                            title="Purpose you declared for this instance"
                            >${purposeLabel(inst.purpose)}</span
                          >
                          ${inst.profile?.datacenter
                            ? html`<span class="row-dc">${inst.profile.datacenter}</span>`
                            : ''}
                        </td>
                        <td>
                          <span style="font-family: monospace; color: #334155;">${inst.username}</span>
                        </td>
                        <td>
                          <span class="status-badge ${this.testingInstanceId === inst.id ? 'testing' : inst.status}">
                            <span class="dot-indicator"></span>
                            ${this.testingInstanceId === inst.id ? 'Testing...' : inst.status}
                          </span>
                        </td>
                        <td>
                          ${inst.is_default
                            ? html`<span class="badge-active-pill icon-btn" title="Default Target" data-tooltip="Default"><svg viewBox="0 0 24 24"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg></span>`
                            : html`<button class="btn-action icon-btn" title="Set as active default target" data-tooltip="Set Default" @click=${() => this.activateInstance(inst.id)}><svg viewBox="0 0 24 24"><path d="M22 9.24l-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03L22 9.24zM12 15.4l-3.76 2.27 1-4.28-3.32-2.88 4.38-.38L12 6.1l1.71 4.04 4.38.38-3.32 2.88 1 4.28L12 15.4z"/></svg></button>`}
                        </td>
                        <td style="text-align: right;">
                          <div style="display: flex; align-items: center; justify-content: flex-end; gap: 6px;">
                            <button
                              class="btn-action icon-btn"
                              ?disabled=${this.testingInstanceId === inst.id}
                              title="Test authentication probe"
                              data-tooltip="Test Auth Probe"
                              @click=${() => this.testInstance(inst.id)}
                            >
                              <svg viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
                            </button>
                            <button
                              class="btn-action icon-btn ${this.editingInstanceId === inst.id ? 'primary' : ''}"
                              title="Rename, change URL, or update credentials"
                              data-tooltip="${this.editingInstanceId === inst.id ? 'Close' : 'Edit / Auth'}"
                              @click=${() => (this.editingInstanceId === inst.id ? this.cancelEdit() : this.startEdit(inst))}
                            >
                              <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                            </button>
                            ${this.confirmingDeleteId === inst.id
                              ? html`
                                  <button class="btn-danger icon-btn" title="Confirm Delete" data-tooltip="Confirm Delete" @click=${() => this.deleteInstance(inst.id)}>
                                    <svg viewBox="0 0 24 24"><path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/></svg>
                                  </button>
                                  <button class="btn-action icon-btn" title="Cancel Delete" data-tooltip="Cancel" @click=${() => (this.confirmingDeleteId = null)}>
                                    <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                                  </button>
                                `
                              : html`
                                  <button
                                    class="btn-action icon-btn"
                                    ?disabled=${this.instances.length <= 1}
                                    title=${this.instances.length <= 1 ? 'Cannot delete the only instance' : 'Delete instance'}
                                    data-tooltip="Delete"
                                    @click=${() => (this.confirmingDeleteId = inst.id)}
                                  >
                                    <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                                  </button>
                                `}
                          </div>
                        </td>
                      </tr>
                      ${this.editingInstanceId === inst.id
                        ? html`
                            <tr>
                              <td colspan="6" style="padding: 0 16px 14px 16px; background: #f8fafc;">
                                <div class="inline-edit-panel">
                                  <div style="font-size: 12px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px;">
                                    Edit Instance & Authentication: ${inst.name}
                                  </div>
                                  <div class="edit-grid">
                                    <div class="form-group">
                                      <label class="form-label">Instance Display Name</label>
                                      <input
                                        type="text"
                                        class="form-input"
                                        .value=${this.editName}
                                        @input=${(e: Event) => (this.editName = (e.target as HTMLInputElement).value)}
                                      />
                                    </div>
                                    <div class="form-group">
                                      <label class="form-label">Endpoint URL</label>
                                      <input
                                        type="text"
                                        class="form-input"
                                        .value=${this.editUrl}
                                        @input=${(e: Event) => (this.editUrl = (e.target as HTMLInputElement).value)}
                                      />
                                    </div>
                                    <div class="form-group">
                                      <label class="form-label">Release Family (auto-detected)</label>
                                      <input
                                        type="text"
                                        class="form-input"
                                        data-testid="edit-release"
                                        .value=${this.editRelease}
                                        readonly
                                        title="Read from the instance build (glide.war) on every connection test"
                                      />
                                    </div>
                                    <div class="form-group">
                                      <label class="form-label" for="edit-purpose">Purpose</label>
                                      <select
                                        id="edit-purpose"
                                        class="form-input"
                                        @change=${(e: Event) =>
                                          (this.editPurpose = (e.target as HTMLSelectElement).value as InstancePurpose)}
                                      >
                                        ${renderPurposeOptions(this.editPurpose)}
                                      </select>
                                    </div>
                                    <div class="form-group">
                                      <label class="form-label">Service Account Username</label>
                                      <input
                                        type="text"
                                        class="form-input"
                                        .value=${this.editUsername}
                                        @input=${(e: Event) => (this.editUsername = (e.target as HTMLInputElement).value)}
                                      />
                                    </div>
                                    <div class="form-group" style="grid-column: span 2;">
                                      <label class="form-label">Service Account Password / Secret</label>
                                      <input
                                        type="password"
                                        class="form-input"
                                        placeholder="Leave blank to keep existing encrypted credentials"
                                        .value=${this.editPassword}
                                        @input=${(e: Event) => (this.editPassword = (e.target as HTMLInputElement).value)}
                                      />
                                    </div>
                                  </div>
                                  <div class="edit-actions">
                                    <button
                                      class="btn-danger icon-btn"
                                      ?disabled=${this.instances.length <= 1}
                                      title="Delete Instance"
                                      data-tooltip="Delete Instance"
                                      @click=${() => this.deleteInstance(inst.id)}
                                    >
                                      <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                                    </button>
                                    <div style="display: flex; gap: 8px;">
                                      <button class="btn-action icon-btn" title="Cancel Edit" data-tooltip="Cancel" @click=${this.cancelEdit}>
                                        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                                      </button>
                                      <button
                                        class="btn-action primary icon-btn"
                                        ?disabled=${this.isSavingEdit}
                                        title="Save Changes"
                                        data-tooltip="Save Changes"
                                        @click=${() => this.saveEdit(inst.id)}
                                      >
                                        <svg viewBox="0 0 24 24"><path d="M17 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/></svg>
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          `
                        : ''}
                    `
                  )}
                </tbody>
              </table>
            </div>

            ${this.actionFeedback
              ? html`
                  <div class="status-feedback ${this.actionFeedback.includes('failed') ? 'error' : 'success'}">
                    ${this.actionFeedback}
                  </div>
                `
              : ''}
          </div>

          <now-instance-add-form @instance-added=${() => void this.refreshData()}></now-instance-add-form>

          <now-diagnostics-card></now-diagnostics-card>
        </div>
      </div>
    `;
  }
}
