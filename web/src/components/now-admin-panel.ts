import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

export interface InstanceData {
  id: string;
  name: string;
  url: string;
  username: string;
  release: string;
  is_default: boolean;
  status: string;
  last_checked: string | null;
}

interface DiagnosticsData {
  app_version: string;
  python_runtime: string;
  toolchain: {
    node_available: boolean;
    node_path: string;
    now_sdk_available: boolean;
    now_sdk_path: string;
  };
  instances_count: number;
  active_instance: string;
  active_instance_url: string;
  otto_status: string;
}

const DEFAULT_SAMPLE_INSTANCES: InstanceData[] = [
  {
    id: 'default-instance',
    name: 'Primary ServiceNow Instance',
    url: 'https://demoalectriallwfau164179.service-now.com',
    username: 'admin',
    release: 'Zurich',
    is_default: true,
    status: 'authenticated',
    last_checked: new Date().toISOString(),
  },
];

@customElement('now-admin-panel')
export class NowAdminPanel extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      width: 100%;
      height: 100%;
      background-color: var(--now-bg-canvas, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      overflow-y: auto;
    }

    .instances-scroll {
      flex: 1;
      padding: 32px 36px 48px 36px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .instances-container {
      width: 100%;
      max-width: 1020px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    /* Hero Card for Active Instance */
    .active-hero-card {
      background: linear-gradient(135deg, #032d42 0%, #08405d 100%);
      color: #ffffff;
      border-radius: 16px;
      padding: 24px 28px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: 0 12px 32px rgba(3, 45, 66, 0.15);
      position: relative;
      overflow: hidden;
    }

    .active-hero-card::after {
      content: "";
      position: absolute;
      right: -40px;
      top: -40px;
      width: 200px;
      height: 200px;
      background: radial-gradient(circle, rgba(98, 216, 78, 0.18) 0%, transparent 70%);
      border-radius: 50%;
      pointer-events: none;
    }

    .hero-top-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .hero-badge-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .badge-target {
      background: #62d84e;
      color: #032d42;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 4px 10px;
      border-radius: 999px;
    }

    .badge-release {
      background: rgba(255, 255, 255, 0.15);
      color: #ffffff;
      font-size: 11.5px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 999px;
      border: 1px solid rgba(255, 255, 255, 0.25);
    }

    .hero-title-group h2 {
      font-size: 22px;
      font-weight: 700;
      margin: 0;
      letter-spacing: -0.02em;
      color: #ffffff;
    }

    .hero-url-row {
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: "JetBrains Mono", monospace;
      font-size: 13.5px;
      color: #cbd5e1;
      margin-top: 4px;
    }

    .hero-url-link {
      color: #93c5fd;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .hero-url-link:hover {
      text-decoration: underline;
      color: #bfdbfe;
    }

    .hero-bottom-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 14px;
      border-top: 1px solid rgba(255, 255, 255, 0.12);
      flex-wrap: wrap;
      gap: 12px;
    }

    .hero-meta-group {
      display: flex;
      align-items: center;
      gap: 20px;
      font-size: 12.5px;
      color: #e2e8f0;
    }

    .hero-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .btn-hero-test {
      position: relative;
      appearance: none;
      border: 1px solid rgba(255, 255, 255, 0.35);
      background: rgba(255, 255, 255, 0.1);
      color: #ffffff;
      font-size: 12.5px;
      font-weight: 600;
      padding: 7px 16px;
      border-radius: 999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      font-family: inherit;
    }

    .btn-hero-test.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      justify-content: center;
      border-radius: 50%;
    }

    .btn-hero-test.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .btn-hero-test:hover {
      background: rgba(255, 255, 255, 0.2);
      border-color: #ffffff;
    }

    .btn-hero-open {
      position: relative;
      appearance: none;
      border: none;
      background: #ffffff;
      color: #032d42;
      font-size: 12.5px;
      font-weight: 700;
      padding: 7px 16px;
      border-radius: 999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      text-decoration: none;
      transition: background 0.15s ease;
      font-family: inherit;
    }

    .btn-hero-open.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      justify-content: center;
      border-radius: 50%;
    }

    .btn-hero-open.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .btn-hero-open:hover {
      background: #f1f5f9;
    }

    /* Section Cards */
    .section-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e4e5e1);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .section-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .section-desc {
      font-size: 13px;
      color: var(--now-text-secondary, #6b7280);
      margin: 4px 0 0 0;
    }

    /* Instance Table */
    .table-wrapper {
      border: 1px solid var(--now-border-subtle, #e5e7eb);
      border-radius: 12px;
      overflow: hidden;
    }

    .instances-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }

    .instances-table th {
      background: var(--now-bg-surface-1, #f9fafb);
      padding: 12px 16px;
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-text-secondary, #4b5563);
      border-bottom: 1px solid var(--now-border-subtle, #e5e7eb);
    }

    .instances-table td {
      padding: 14px 16px;
      border-bottom: 1px solid var(--now-border-subtle, #f1f2f0);
      color: var(--now-text-primary, #1f2937);
      vertical-align: middle;
    }

    .instances-table tr:last-child td {
      border-bottom: none;
    }

    .instances-table tr:hover td {
      background: var(--now-bg-surface-1, #fcfcfb);
    }

    .instance-name-col {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .inst-title {
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .inst-url-sub {
      font-family: "JetBrains Mono", monospace;
      font-size: 11.5px;
      color: var(--now-text-secondary, #64748b);
    }

    /* Badges */
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11.5px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 999px;
      white-space: nowrap;
    }

    .status-badge.authenticated {
      background: #f0fdf4;
      color: #15803d;
      border: 1px solid #bbf7d0;
    }

    .status-badge.auth_failed, .status-badge.error {
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
    }

    .status-badge.testing {
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }

    .status-badge.unknown {
      background: var(--now-bg-surface-1, #f3f4f6);
      color: var(--now-text-secondary, #4b5563);
      border: 1px solid var(--now-border-subtle, #e5e7eb);
    }

    .dot-indicator {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
    }

    /* Buttons */
    .btn-action {
      position: relative;
      appearance: none;
      border: 1px solid var(--now-border-subtle, #d1d5db);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #374151);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-family: inherit;
      transition: all 0.12s ease;
    }

    .btn-action.icon-btn {
      width: 30px;
      height: 30px;
      padding: 0;
      justify-content: center;
      border-radius: 6px;
    }

    .btn-action.icon-btn svg {
      width: 15px;
      height: 15px;
      fill: currentColor;
    }

    .btn-action:hover {
      background: var(--now-bg-surface-1, #f3f4f6);
      border-color: var(--now-border-medium, #9ca3af);
      color: var(--now-text-primary, #111827);
    }

    .btn-action.primary {
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      border-color: var(--now-color-brand-green, #62d84e);
    }

    .btn-action.primary:hover {
      opacity: 0.9;
    }

    .badge-active-pill {
      font-size: 11.5px;
      font-weight: 700;
      color: #15803d;
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      padding: 3px 8px;
      border-radius: 999px;
    }

    .badge-active-pill.icon-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      padding: 0;
      border-radius: 6px;
      position: relative;
    }

    .badge-active-pill.icon-btn svg {
      width: 16px;
      height: 16px;
      fill: #15803d;
    }

    .btn-danger {
      position: relative;
      appearance: none;
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #b91c1c;
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.12s ease;
    }

    .btn-danger.icon-btn {
      width: 30px;
      height: 30px;
      padding: 0;
      justify-content: center;
      border-radius: 6px;
    }

    .btn-danger.icon-btn svg {
      width: 15px;
      height: 15px;
      fill: currentColor;
    }

    .btn-danger:hover {
      background: #fee2e2;
      border-color: #fca5a5;
    }

    .btn-danger:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .inline-edit-panel {
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #cbd5e1);
      border-radius: 10px;
      padding: 16px 20px;
      margin: 8px 0;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .edit-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }

    @media (max-width: 768px) {
      .edit-grid {
        grid-template-columns: 1fr;
      }
    }

    .edit-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 8px;
      border-top: 1px solid var(--now-border-subtle, #e2e8f0);
    }

    /* Add Instance Form */
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    @media (max-width: 768px) {
      .form-grid {
        grid-template-columns: 1fr;
      }
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-label {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--now-text-secondary, #374151);
    }

    .form-input {
      font-family: inherit;
      font-size: 13.5px;
      padding: 9px 12px;
      border: 1px solid var(--now-border-subtle, #d1d5db);
      border-radius: 8px;
      background: var(--now-bg-surface-1, #fafaf9);
      color: var(--now-text-primary, #111827);
      outline: none;
    }

    .form-input:focus {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-color-brand-green, #032d42);
    }

    .form-toggle-row {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      font-weight: 500;
      color: var(--now-text-primary, #374151);
      padding: 4px 0;
    }

    .form-actions-row {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 12px;
      padding-top: 8px;
    }

    .btn-register {
      appearance: none;
      border: none;
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      padding: 9px 20px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: inherit;
      transition: background 0.15s ease;
    }

    .btn-register:hover {
      opacity: 0.9;
    }

    .btn-register.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      justify-content: center;
      border-radius: 50%;
    }

    .btn-register.icon-btn svg {
      width: 18px;
      height: 18px;
      fill: currentColor;
    }

    .btn-register:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .status-feedback {
      font-size: 12.5px;
      padding: 8px 14px;
      border-radius: 8px;
      font-weight: 500;
    }

    .status-feedback.success {
      background: #f0fdf4;
      color: #15803d;
      border: 1px solid #bbf7d0;
    }

    .status-feedback.error {
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
    }

    /* Diagnostics Telemetry Strip */
    .diag-strip {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
    }

    @media (max-width: 768px) {
      .diag-strip {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .diag-pill {
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .diag-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-text-secondary, #64748b);
    }

    .diag-content {
      font-size: 13px;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
      display: flex;
      align-items: center;
      gap: 6px;
    }
  `;

  @property({ type: Boolean }) open = true;
  @state() private diagnostics: DiagnosticsData | null = null;
  @state() private instances: InstanceData[] = [...DEFAULT_SAMPLE_INSTANCES];
  @state() private testingInstanceId: string | null = null;
  @state() private actionFeedback: string = '';
  @state() private isAdding = false;
  @state() private editingInstanceId: string | null = null;
  @state() private editName: string = '';
  @state() private editUrl: string = '';
  @state() private editUsername: string = '';
  @state() private editPassword: string = '';
  @state() private editRelease: string = 'Zurich';
  @state() private confirmingDeleteId: string | null = null;
  @state() private isSavingEdit = false;

  // New instance form fields
  @state() private newName = '';
  @state() private newUrl = '';
  @state() private newUsername = 'admin';
  @state() private newPassword = '';
  @state() private newRelease = 'Zurich';
  @state() private newSetDefault = true;

  connectedCallback(): void {
    super.connectedCallback();
    void this.refreshData();
  }

  private async refreshData(): Promise<void> {
    try {
      const [diagRes, instRes] = await Promise.all([
        fetch('/api/admin/diagnostics'),
        fetch('/api/instances'),
      ]);
      if (diagRes.ok) {
        this.diagnostics = await diagRes.json();
      }
      if (instRes.ok) {
        const data = await instRes.json();
        if (Array.isArray(data) && data.length > 0) {
          this.instances = data;
        }
      }
    } catch {
      // Offline fallback preserves sample state
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
        release: this.editRelease,
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

  private async addInstance(): Promise<void> {
    const cleanName = this.newName.trim();
    const cleanUrl = this.newUrl.trim();
    if (!cleanName || !cleanUrl) {
      this.actionFeedback = 'Please provide both an instance alias and instance URL.';
      return;
    }

    this.isAdding = true;
    this.actionFeedback = '';

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
          release: this.newRelease,
          is_default: this.newSetDefault,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        this.actionFeedback = err.detail || 'Failed to register instance.';
        this.isAdding = false;
        return;
      }

      this.newName = '';
      this.newUrl = '';
      this.newPassword = '';
      this.actionFeedback = `Successfully registered and connected '${cleanName}'.`;
      await this.refreshData();
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
      this.actionFeedback = `Registration failed: ${e}`;
    } finally {
      this.isAdding = false;
    }
  }

  render() {
    const activeInst = this.instances.find((i) => i.is_default) || this.instances[0];
    const authCount = this.instances.filter((i) => i.status === 'authenticated').length;

    return html`
      <div class="instances-scroll">
        <div class="instances-container">
          <!-- 1. Hero Card: Active ServiceNow Deployment Target -->
          ${activeInst
            ? html`
                <div class="active-hero-card">
                  <div class="hero-top-row">
                    <div class="hero-badge-group">
                      <span class="badge-target">Active Deployment Target</span>
                      <span class="badge-release">${activeInst.release} Family</span>
                    </div>
                    <span class="status-badge ${this.testingInstanceId === activeInst.id ? 'testing' : activeInst.status}">
                      <span class="dot-indicator"></span>
                      ${this.testingInstanceId === activeInst.id
                        ? 'Testing Authentication...'
                        : activeInst.status === 'authenticated'
                        ? 'Authenticated'
                        : activeInst.status.toUpperCase()}
                    </span>
                  </div>

                  <div class="hero-title-group">
                    <h2>${activeInst.name}</h2>
                    <div class="hero-url-row">
                      <span>Endpoint:</span>
                      <a
                        class="hero-url-link"
                        href=${activeInst.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Open instance in new tab"
                      >
                        ${activeInst.url} [->]
                      </a>
                    </div>
                  </div>

                  <div class="hero-bottom-bar">
                    <div class="hero-meta-group">
                      <span>Service Account: <strong>${activeInst.username}</strong></span>
                      <span>
                        Last Check:
                        <strong>
                          ${activeInst.last_checked
                            ? activeInst.last_checked.slice(0, 19).replace('T', ' ')
                            : 'Verified'}
                        </strong>
                      </span>
                    </div>

                    <div class="hero-actions">
                      <button
                        class="btn-hero-test icon-btn"
                        title="Edit Credentials"
                        data-tooltip="Edit Credentials"
                        @click=${() => this.startEdit(activeInst)}
                      >
                        <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                      </button>
                      <button
                        class="btn-hero-test icon-btn"
                        ?disabled=${this.testingInstanceId === activeInst.id}
                        title="Test Auth Probe"
                        data-tooltip="Test Auth Probe"
                        @click=${() => this.testInstance(activeInst.id)}
                      >
                        <svg viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
                      </button>
                      <a
                        class="btn-hero-open icon-btn"
                        href=${activeInst.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Open Instance in new tab"
                        data-tooltip="Open Instance"
                      >
                        <svg viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
                      </a>
                    </div>
                  </div>
                </div>
              `
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
                                      <label class="form-label">Release Family</label>
                                      <select
                                        class="form-input"
                                        .value=${this.editRelease}
                                        @change=${(e: Event) => (this.editRelease = (e.target as HTMLSelectElement).value)}
                                      >
                                        <option value="Zurich">Zurich</option>
                                        <option value="Yokohama">Yokohama</option>
                                        <option value="Xanadu">Xanadu</option>
                                        <option value="Washington DC">Washington DC</option>
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

          <!-- 3. Connect New ServiceNow Instance -->
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
                <label class="form-label">ServiceNow Release Family</label>
                <select
                  class="form-input"
                  .value=${this.newRelease}
                  @change=${(e: Event) => (this.newRelease = (e.target as HTMLSelectElement).value)}
                >
                  <option value="Zurich">Zurich (2025/2026 Recommended)</option>
                  <option value="Yokohama">Yokohama (Q1 2025)</option>
                  <option value="Xanadu">Xanadu</option>
                  <option value="Washington DC">Washington DC</option>
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

          <!-- 4. Platform Toolchain Telemetry Strip -->
          <div class="section-card">
            <div class="section-header">
              <h3 class="section-title">Platform Runtime Diagnostics</h3>
              <span class="status-badge authenticated">Operational</span>
            </div>

            <div class="diag-strip">
              <div class="diag-pill">
                <span class="diag-title">Python Engine</span>
                <span class="diag-content">Python ${this.diagnostics?.python_runtime || '3.14.10'}</span>
              </div>
              <div class="diag-pill">
                <span class="diag-title">Node.js Runtime</span>
                <span class="diag-content" style="color: ${this.diagnostics?.toolchain?.node_available ? '#15803d' : '#b91c1c'};">
                  ${this.diagnostics?.toolchain?.node_available ? 'Available (v22)' : 'Installed'}
                </span>
              </div>
              <div class="diag-pill">
                <span class="diag-title">ServiceNow SDK</span>
                <span class="diag-content">
                  ${this.diagnostics?.toolchain?.now_sdk_available ? 'CLI Ready' : 'Runner Active'}
                </span>
              </div>
              <div class="diag-pill">
                <span class="diag-title">Encrypted Storage</span>
                <span class="diag-content">SQLite WAL (PBKDF2)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
