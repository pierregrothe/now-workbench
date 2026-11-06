import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './now-admin-panel.js';
import { applyTheme } from '../utils/theme.js';

export interface WorkbenchPreferences {
  anthropic_api_key_masked: string;
  has_anthropic_api_key: boolean;
  claude_model: string;
  auto_route_intent: boolean;
  auto_execute_intent: boolean;
  capture_viewport_width: number;
  capture_viewport_height: number;
  capture_default_media_type: 'screenshot' | 'video';
  capture_wait_timeout_ms: number;
  capture_fake_mode: boolean;
  sc_author_name: string;
  sc_author_email: string;
  default_scoped_prefix: string;
  default_brand_color: string;
  narrative_tone: string;
  sdk_fake_mode: boolean;
  show_welcome_on_startup: boolean;
  sidebar_collapsed_default: boolean;
  hud_font_scale: string;
  theme_mode?: 'system' | 'light' | 'dark';
  updated_at?: string;
}

const DEFAULT_PREFS: WorkbenchPreferences = {
  anthropic_api_key_masked: '',
  has_anthropic_api_key: false,
  claude_model: 'claude-sonnet-5-5',
  auto_route_intent: true,
  auto_execute_intent: true,
  capture_viewport_width: 1440,
  capture_viewport_height: 900,
  capture_default_media_type: 'screenshot',
  capture_wait_timeout_ms: 1500,
  capture_fake_mode: false,
  sc_author_name: 'Now Workbench Solution Consultant',
  sc_author_email: 'sc@servicenow.com',
  default_scoped_prefix: 'x_snc',
  default_brand_color: '#62d84e',
  narrative_tone: 'executive',
  sdk_fake_mode: false,
  show_welcome_on_startup: true,
  sidebar_collapsed_default: false,
  hud_font_scale: 'standard',
  theme_mode: 'system',
};

type SettingsSection = 'claude' | 'capture' | 'synthesis' | 'workspace' | 'instances';

const SECTIONS: { id: SettingsSection; label: string }[] = [
  { id: 'claude', label: 'Claude and Otto' },
  { id: 'capture', label: 'Media capture' },
  { id: 'synthesis', label: 'Synthesis defaults' },
  { id: 'workspace', label: 'Workspace' },
  { id: 'instances', label: 'ServiceNow instances' },
];

@customElement('now-workbench-settings')
export class NowWorkbenchSettings extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--otto-canvas, #efece7);
      color: var(--now-text-primary, #16181d);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .top-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 36px;
      border-bottom: 1px solid var(--now-border-subtle, #f0f0ee);
      background: transparent;
      flex-shrink: 0;
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .title-group h1 {
      font-size: 20px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
      letter-spacing: -0.015em;
    }

    .prefs-layout {
      flex: 1;
      min-height: 0;
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 8px;
      padding: 24px 36px 0;
      max-width: 1240px;
      width: 100%;
      margin: 0 auto;
      box-sizing: border-box;
    }

    .pref-nav {
      display: flex;
      flex-direction: column;
      gap: 4px;
      align-self: start;
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: 16px;
      padding: 8px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }

    .pref-nav-item {
      text-align: left;
      border: none;
      background: transparent;
      font: inherit;
      font-size: 13.5px;
      padding: 9px 12px;
      border-radius: 10px;
      cursor: pointer;
      color: var(--now-text-primary, #16181d);
    }

    .pref-nav-item:hover {
      background: var(--otto-canvas-active, #e3dfd8);
    }

    .pref-nav-item.active {
      background: #1a1a1a;
      color: #ffffff;
    }

    .pref-content {
      min-width: 0;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
    }

    .section-card[hidden] {
      display: none;
    }

    .scroll-body {
      flex: 1;
      overflow-y: auto;
      padding: 28px 36px 40px 36px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .settings-container {
      width: 100%;
      max-width: 980px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }

    .section-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e6e7e4);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 4px 18px var(--now-shadow-soft, rgba(0, 0, 0, 0.025));
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .section-card.featured {
      border-color: var(--now-border-subtle, #b8e2b0);
      background: linear-gradient(180deg, var(--now-color-brand-green-subtle, rgba(98, 216, 78, 0.08)) 0%, var(--now-bg-surface-0, #ffffff) 100%);
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--now-border-subtle, #f2f2f0);
      padding-bottom: 14px;
    }

    .section-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
    }

    .section-desc {
      font-size: 12.5px;
      color: var(--now-text-secondary, #6b7280);
      margin: 3px 0 0 0;
    }

    .key-status-pill {
      font-size: 11.5px;
      font-weight: 600;
      padding: 4px 11px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .key-status-pill.connected {
      background: var(--now-bg-surface-1, #dcfce7);
      color: var(--now-color-brand-green, #166534);
    }

    .key-status-pill.simulated {
      background: var(--now-bg-surface-1, #fef3c7);
      color: #92400e;
    }

    .masked-key-badge {
      display: inline-flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      background: var(--now-bg-surface-1, #f0fdf4);
      border: 1px solid var(--now-border-subtle, #bbf7d0);
      color: var(--now-color-brand-green, #14532d);
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 12.5px;
      font-family: "JetBrains Mono", monospace;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    @media (max-width: 780px) {
      .grid-2 {
        grid-template-columns: 1fr;
      }
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .field label {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--now-text-primary, #2c2e33);
    }

    .field-hint {
      font-size: 11.5px;
      color: var(--now-text-secondary, #6b7280);
    }

    .input-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    input[type="text"],
    input[type="password"],
    input[type="number"],
    input[type="email"],
    select {
      flex: 1;
      font-family: inherit;
      font-size: 13.5px;
      color: var(--now-text-primary, #16181d);
      background: var(--now-bg-surface-1, #fafaf9);
      border: 1px solid var(--now-border-subtle, #dcded9);
      border-radius: 10px;
      padding: 9px 12px;
      outline: none;
    }

    input:focus,
    select:focus {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-color-brand-green, #62d84e);
    }

    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      background: var(--now-bg-surface-1, #fafaf9);
      border: 1px solid var(--now-border-subtle, #ececea);
      border-radius: 10px;
    }

    .toggle-label-group {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .toggle-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--now-text-primary, #16181d);
    }

    .toggle-sub {
      font-size: 11.5px;
      color: var(--now-text-secondary, #6b7280);
    }

    .actions-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 6px;
    }

    .btn {
      position: relative;
      appearance: none;
      border: 1px solid var(--now-border-medium, #dcded9);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-size: 13px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 999px;
      cursor: pointer;
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.12s ease, border-color 0.12s ease;
    }

    .btn:hover {
      background: var(--now-bg-surface-1, #f4f4f2);
    }

    .btn.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      border-radius: 50%;
    }

    .btn.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .btn.primary {
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      border-color: var(--now-color-brand-green, #62d84e);
    }

    .btn.primary:hover {
      opacity: 0.9;
    }

    .btn.btn-delete-key {
      background: #fef2f2;
      color: #dc2626;
      border-color: #fecaca;
    }

    .btn.btn-delete-key:hover {
      background: #fee2e2;
    }

    .btn.btn-verify-key {
      background: var(--now-bg-surface-1, #f0fdf4);
      color: var(--now-color-brand-green, #166534);
      border-color: var(--now-border-subtle, #bbf7d0);
    }

    .btn.btn-verify-key:hover {
      opacity: 0.9;
    }

    .save-toast {
      font-size: 12.5px;
      font-weight: 600;
      color: #166534;
      background: #dcfce7;
      padding: 7px 14px;
      border-radius: 999px;
    }

    .masked-key-badge.locked {
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #cbd5e1);
      color: var(--now-text-primary, #334155);
      padding: 10px 14px;
      border-radius: 10px;
    }

    .key-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .key-badge-label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-color-brand-green, #15803d);
    }

    .key-code {
      font-family: "JetBrains Mono", monospace;
      font-size: 13px;
      color: var(--now-text-primary, #0f172a);
      font-weight: 600;
    }

    .btn-delete-key {
      background: #fef2f2;
      border-color: #fecaca;
      color: #b91c1c;
      font-size: 12px;
      padding: 6px 12px;
    }

    .btn-delete-key:hover {
      background: #fee2e2;
      border-color: #fca5a5;
    }

    .btn-verify-key {
      background: #032d42;
      color: #ffffff;
      border-color: #032d42;
      white-space: nowrap;
    }

    .btn-verify-key:hover {
      background: #053b56;
    }

    .btn-verify-key:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .alert-hint {
      color: #b45309;
      font-weight: 500;
    }

    .error-banner {
      font-size: 12px;
      color: #dc2626;
      background: #fef2f2;
      border: 1px solid #fecaca;
      padding: 6px 10px;
      border-radius: 8px;
    }
  `;

  @state() private activeSection: SettingsSection = 'claude';
  @state() private prefs: WorkbenchPreferences = { ...DEFAULT_PREFS };
  @state() private newApiKeyInput = '';
  @state() private isSaving = false;
  @state() private isVerifyingKey = false;
  @state() private keyVerificationError = '';
  @state() private saveMessage = '';

  connectedCallback(): void {
    super.connectedCallback();
    void this.loadSettings();
  }

  private async loadSettings(): Promise<void> {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        this.prefs = (await res.json()) as WorkbenchPreferences;
        if (this.prefs.theme_mode) {
          applyTheme(this.prefs.theme_mode);
        }
      }
    } catch {
      // Offline preview uses default state
    }
  }

  private handleThemeChange(mode: 'system' | 'light' | 'dark'): void {
    this.updateField('theme_mode', mode);
    applyTheme(mode);
    this.dispatchEvent(
      new CustomEvent('theme-change', {
        detail: { mode },
        bubbles: true,
        composed: true,
      })
    );
    // Immediately persist theme mode change to backend preferences
    void fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme_mode: mode }),
    });
  }

  private updateField<K extends keyof WorkbenchPreferences>(
    key: K,
    value: WorkbenchPreferences[K]
  ): void {
    this.prefs = { ...this.prefs, [key]: value };
    this.saveMessage = '';
  }

  private handleViewportPreset(preset: string): void {
    const [w, h] = preset.split('x').map((n) => Number(n));
    if (w && h) {
      this.prefs = {
        ...this.prefs,
        capture_viewport_width: w,
        capture_viewport_height: h,
      };
    }
  }

  private async saveSettings(): Promise<void> {
    this.isSaving = true;
    this.saveMessage = '';
    try {
      const payload: Record<string, unknown> = {
        claude_model: this.prefs.claude_model,
        auto_route_intent: this.prefs.auto_route_intent,
        auto_execute_intent: this.prefs.auto_execute_intent,
        capture_viewport_width: this.prefs.capture_viewport_width,
        capture_viewport_height: this.prefs.capture_viewport_height,
        capture_default_media_type: this.prefs.capture_default_media_type,
        capture_wait_timeout_ms: this.prefs.capture_wait_timeout_ms,
        capture_fake_mode: this.prefs.capture_fake_mode,
        sc_author_name: this.prefs.sc_author_name,
        sc_author_email: this.prefs.sc_author_email,
        default_scoped_prefix: this.prefs.default_scoped_prefix,
        default_brand_color: this.prefs.default_brand_color,
        narrative_tone: this.prefs.narrative_tone,
        sdk_fake_mode: this.prefs.sdk_fake_mode,
        show_welcome_on_startup: this.prefs.show_welcome_on_startup,
        sidebar_collapsed_default: this.prefs.sidebar_collapsed_default,
        hud_font_scale: this.prefs.hud_font_scale,
        theme_mode: this.prefs.theme_mode ?? 'system',
      };
      if (this.newApiKeyInput.trim()) {
        payload.anthropic_api_key = this.newApiKeyInput.trim();
      }
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        this.saveMessage = `Could not save settings: ${await this.errorDetail(res)}`;
        return;
      }
      this.prefs = (await res.json()) as WorkbenchPreferences;
      this.newApiKeyInput = '';
      this.saveMessage = 'Saved & encrypted Now Workbench settings.';
      this.dispatchEvent(
        new CustomEvent('settings-updated', {
          detail: { prefs: this.prefs },
          bubbles: true,
          composed: true,
        })
      );
    } catch (e) {
      this.saveMessage = `Could not save settings: ${e instanceof Error ? e.message : String(e)}`;
    } finally {
      this.isSaving = false;
    }
  }

  private async errorDetail(res: Response): Promise<string> {
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === 'string' && body.detail) return body.detail;
    } catch {
      // Body was not JSON; fall through to the status line.
    }
    return `HTTP ${res.status}`;
  }

  private async deleteApiKey(): Promise<void> {
    this.keyVerificationError = '';
    try {
      const res = await fetch('/api/settings/api-key', {
        method: 'DELETE',
      });
      if (res.ok) {
        this.prefs = (await res.json()) as WorkbenchPreferences;
        this.saveMessage = 'API key deleted. You may now enter a new key.';
        this.newApiKeyInput = '';
      } else {
        this.keyVerificationError = `Could not delete key: ${await this.errorDetail(res)}`;
      }
    } catch (e) {
      this.keyVerificationError = `Could not delete key: ${e instanceof Error ? e.message : String(e)}`;
    }
  }

  private async verifyAndSaveApiKey(): Promise<void> {
    const rawKey = this.newApiKeyInput.trim();
    if (!rawKey) {
      this.keyVerificationError = 'Please enter an API key to verify.';
      return;
    }
    if (!rawKey.startsWith('sk-ant-')) {
      this.keyVerificationError = "Invalid format. Claude API keys must start with 'sk-ant-'.";
      return;
    }

    this.isVerifyingKey = true;
    this.keyVerificationError = '';
    this.saveMessage = '';

    try {
      const probeRes = await fetch('/api/settings/validate-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: rawKey }),
      });
      const probeData = await probeRes.json();
      if (!probeRes.ok || !probeData.valid) {
        this.keyVerificationError = probeData.message || 'Key validation failed with Claude API.';
        this.isVerifyingKey = false;
        return;
      }

      const saveRes = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anthropic_api_key: rawKey }),
      });
      if (!saveRes.ok) {
        const saveErr = await saveRes.json();
        this.keyVerificationError = saveErr.detail || 'Failed to save key.';
      } else {
        this.prefs = (await saveRes.json()) as WorkbenchPreferences;
        this.newApiKeyInput = '';
        this.saveMessage = 'Key verified and securely encrypted in local vault.';
        this.dispatchEvent(
          new CustomEvent('settings-updated', {
            detail: { prefs: this.prefs },
            bubbles: true,
            composed: true,
          })
        );
      }
    } catch (e) {
      this.keyVerificationError = `Validation error: ${e}`;
    } finally {
      this.isVerifyingKey = false;
    }
  }

  private async resetSettings(): Promise<void> {
    try {
      const res = await fetch('/api/settings/reset', { method: 'POST' });
      if (res.ok) {
        this.prefs = (await res.json()) as WorkbenchPreferences;
      } else {
        this.prefs = { ...DEFAULT_PREFS };
      }
    } catch {
      this.prefs = { ...DEFAULT_PREFS };
    }
    this.newApiKeyInput = '';
    this.saveMessage = 'Reset to factory defaults.';
    applyTheme(this.prefs.theme_mode ?? 'system');
  }

  render() {
    const hasKey = this.prefs.has_anthropic_api_key;
    const currentViewport = `${this.prefs.capture_viewport_width}x${this.prefs.capture_viewport_height}`;

    return html`
      <div class="top-bar">
        <div class="title-group">
          <h1>Now Workbench Settings</h1>
        </div>

      </div>

      <div class="prefs-layout">
        <nav class="pref-nav" aria-label="Settings sections">
          ${SECTIONS.map(
            (sec) => html`
              <button
                type="button"
                class="pref-nav-item ${this.activeSection === sec.id ? 'active' : ''}"
                @click=${() => {
                  this.activeSection = sec.id;
                }}
              >
                ${sec.label}
              </button>
            `
          )}
        </nav>
        <div class="pref-content">
      ${this.activeSection === 'instances'
        ? html`
            <now-admin-panel
              @instance-changed=${(e: CustomEvent) => {
                this.dispatchEvent(
                  new CustomEvent('instance-changed', {
                    detail: e.detail,
                    bubbles: true,
                    composed: true,
                  })
                );
              }}
            ></now-admin-panel>
          `
        : html`
            <div class="scroll-body">
              <div class="settings-container">
                <!-- 1. Claude AI API Key & Intent Router -->
                <div class="section-card featured" ?hidden=${this.activeSection !== 'claude'}>
                  <div class="section-header">
                    <div>
                      <h2 class="section-title">Claude AI Copilot & Intent Router</h2>
                      <p class="section-desc">
                        Configure your Claude AI API Key (encrypted at rest), active model, and conversational menu routing.
                      </p>
                    </div>
                    <span class="key-status-pill ${hasKey ? 'connected' : 'simulated'}">
                      ${hasKey
                        ? `Encrypted Key Active (${this.prefs.anthropic_api_key_masked})`
                        : 'Simulation Mode (No API Key)'}
                    </span>
                  </div>

                  <div class="grid-2">
                    <div class="field">
                      <label>Claude AI API Key</label>
                      ${hasKey
                        ? html`
                            <div class="masked-key-badge locked">
                              <div class="key-info">
                                <span class="key-badge-label">Active Key</span>
                                <span class="key-code">${this.prefs.anthropic_api_key_masked}</span>
                              </div>
                              <button
                                class="btn btn-delete-key icon-btn"
                                type="button"
                                @click=${this.deleteApiKey}
                                title="Delete Key to Replace"
                                aria-label="Delete Key"
                                data-tooltip="Delete Key"
                              >
                                <svg viewBox="0 0 24 24">
                                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                                </svg>
                              </button>
                            </div>
                            <span class="field-hint alert-hint">
                              An active API key is currently secured in your local encrypted vault.
                              To replace it, you must delete the current key first.
                            </span>
                          `
                        : html`
                            <div class="input-row">
                              <input
                                type="password"
                                autocomplete="off"
                                placeholder="Enter Claude AI API Key (sk-ant-...)"
                                .value=${this.newApiKeyInput}
                                ?disabled=${this.isVerifyingKey}
                                @input=${(e: Event) => {
                                  this.newApiKeyInput = (e.target as HTMLInputElement).value;
                                  this.keyVerificationError = '';
                                  this.saveMessage = '';
                                }}
                              />
                              <button
                                class="btn btn-verify-key icon-btn"
                                type="button"
                                ?disabled=${this.isVerifyingKey || !this.newApiKeyInput.trim()}
                                @click=${this.verifyAndSaveApiKey}
                                title="Validate Key with Anthropic and Save"
                                aria-label="Validate & Save Key"
                                data-tooltip="Validate & Save"
                              >
                                <svg viewBox="0 0 24 24">
                                  <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z" />
                                </svg>
                              </button>
                            </div>
                            ${this.keyVerificationError
                              ? html`<div class="error-banner">${this.keyVerificationError}</div>`
                              : html`
                                  <span class="field-hint">
                                    Pre-validated against Claude API before being encrypted and saved in your local database.
                                  </span>
                                `}
                          `}
                    </div>

                    <div class="field">
                      <label>Claude Model</label>
                      <select
                        .value=${this.prefs.claude_model}
                        @change=${(e: Event) =>
                          this.updateField('claude_model', (e.target as HTMLSelectElement).value)}
                      >
                        <option value="claude-sonnet-5-5">Claude Sonnet 5.5 (Recommended)</option>
                        <option value="claude-opus-4-5">Claude Opus 4.5 (Deep Architecture)</option>
                        <option value="claude-haiku-4-5">Claude Haiku 4.5 (Fast Triage)</option>
                      </select>
                      <span class="field-hint">
                        Selects the default model for conversational synthesis and schema explanations.
                      </span>
                    </div>
                  </div>

                  <div class="grid-2">
                    <div class="toggle-row">
                      <div class="toggle-label-group">
                        <span class="toggle-title">Auto-Route Menu on AI Intent</span>
                        <span class="toggle-sub">
                          Switch left menu to detected tool and dock chat box at the bottom of the page
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        .checked=${this.prefs.auto_route_intent}
                        @change=${(e: Event) =>
                          this.updateField(
                            'auto_route_intent',
                            (e.target as HTMLInputElement).checked
                          )}
                      />
                    </div>

                    <div class="toggle-row">
                      <div class="toggle-label-group">
                        <span class="toggle-title">Auto-Execute on Route</span>
                        <span class="toggle-sub">
                          Immediately run synthesis or media capture when routed from chat
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        .checked=${this.prefs.auto_execute_intent}
                        @change=${(e: Event) =>
                          this.updateField(
                            'auto_execute_intent',
                            (e.target as HTMLInputElement).checked
                          )}
                      />
                    </div>
                  </div>
                </div>

                <!-- 2. Instance Media Capture Defaults -->
                <div class="section-card" ?hidden=${this.activeSection !== 'capture'}>
                  <div class="section-header">
                    <div>
                      <h2 class="section-title">Instance Media Capture Defaults</h2>
                      <p class="section-desc">
                        Default browser viewport resolution, capture format (.png / .webm), page settle delay, and offline fallback.
                      </p>
                    </div>
                  </div>

                  <div class="grid-2">
                    <div class="field">
                      <label>Browser Viewport Resolution</label>
                      <select
                        .value=${currentViewport}
                        @change=${(e: Event) =>
                          this.handleViewportPreset((e.target as HTMLSelectElement).value)}
                      >
                        <option value="1440x900">1440 x 900 (Presentation Standard)</option>
                        <option value="1920x1080">1920 x 1080 (Full HD 1080p)</option>
                        <option value="1280x720">1280 x 720 (Compact 720p)</option>
                      </select>
                    </div>

                    <div class="field">
                      <label>Default Capture Format</label>
                      <select
                        .value=${this.prefs.capture_default_media_type}
                        @change=${(e: Event) =>
                          this.updateField(
                            'capture_default_media_type',
                            (e.target as HTMLSelectElement).value as 'screenshot' | 'video'
                          )}
                      >
                        <option value="screenshot">Screenshot (.png)</option>
                        <option value="video">Walkthrough Video (.webm)</option>
                      </select>
                    </div>
                  </div>

                  <div class="grid-2">
                    <div class="field">
                      <label>Page Settle Timeout (ms)</label>
                      <input
                        type="number"
                        min="0"
                        max="15000"
                        step="250"
                        .value=${String(this.prefs.capture_wait_timeout_ms)}
                        @input=${(e: Event) =>
                          this.updateField(
                            'capture_wait_timeout_ms',
                            Number((e.target as HTMLInputElement).value) || 1500
                          )}
                      />
                    </div>

                    <div class="toggle-row">
                      <div class="toggle-label-group">
                        <span class="toggle-title">Offline Simulation Fallback</span>
                        <span class="toggle-sub">
                          Generate deterministic preview captures when offline or without instance credentials
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        .checked=${this.prefs.capture_fake_mode}
                        @change=${(e: Event) =>
                          this.updateField(
                            'capture_fake_mode',
                            (e.target as HTMLInputElement).checked
                          )}
                      />
                    </div>
                  </div>
                </div>

                <!-- 3. Solution Consultant & Demo Synthesis Defaults -->
                <div class="section-card" ?hidden=${this.activeSection !== 'synthesis'}>
                  <div class="section-header">
                    <div>
                      <h2 class="section-title">Solution Consultant & Synthesis Defaults</h2>
                      <p class="section-desc">
                        Default author metadata, scoped table prefix, and SC narrative tone.
                      </p>
                    </div>
                  </div>

                  <div class="grid-2">
                    <div class="field">
                      <label>Solution Consultant Name (Bundle Author)</label>
                      <input
                        type="text"
                        .value=${this.prefs.sc_author_name}
                        @input=${(e: Event) =>
                          this.updateField(
                            'sc_author_name',
                            (e.target as HTMLInputElement).value
                          )}
                      />
                    </div>

                    <div class="field">
                      <label>Solution Consultant Email</label>
                      <input
                        type="email"
                        .value=${this.prefs.sc_author_email}
                        @input=${(e: Event) =>
                          this.updateField(
                            'sc_author_email',
                            (e.target as HTMLInputElement).value
                          )}
                      />
                    </div>
                  </div>

                  <div class="grid-2">
                    <div class="field">
                      <label>Default Scoped Table Prefix</label>
                      <input
                        type="text"
                        .value=${this.prefs.default_scoped_prefix}
                        @input=${(e: Event) =>
                          this.updateField(
                            'default_scoped_prefix',
                            (e.target as HTMLInputElement).value
                          )}
                      />
                    </div>
                  </div>
                </div>

                <!-- 4. UI & Presenter HUD Preferences -->
                <div class="section-card" ?hidden=${this.activeSection !== 'workspace'}>
                  <div class="section-header">
                    <div>
                      <h2 class="section-title">Workspace UI & Presenter HUD</h2>
                      <p class="section-desc">
                        Control startup dialogs, navigation rail defaults, and Presenter HUD teleprompter sizing.
                      </p>
                    </div>
                  </div>

                  <div class="grid-2">
                    <div class="toggle-row">
                      <div class="toggle-label-group">
                        <span class="toggle-title">Show Welcome Modal on Startup</span>
                        <span class="toggle-sub">
                          Display the "Welcome to Now Workbench" dialog when launching the workspace
                        </span>
                      </div>
                      <input
                        type="checkbox"
                        .checked=${this.prefs.show_welcome_on_startup}
                        @change=${(e: Event) =>
                          this.updateField(
                            'show_welcome_on_startup',
                            (e.target as HTMLInputElement).checked
                          )}
                      />
                    </div>

                    <div class="field">
                      <label>Color Theme Mode</label>
                      <select
                        .value=${this.prefs.theme_mode ?? 'system'}
                        @change=${(e: Event) =>
                          this.handleThemeChange(
                            (e.target as HTMLSelectElement).value as 'system' | 'light' | 'dark'
                          )}
                      >
                        <option value="system">System Default (Automatic)</option>
                        <option value="light">ServiceNow Polaris (Light)</option>
                        <option value="dark">ServiceNow Dark Mode (Dark)</option>
                      </select>
                      <span class="field-hint">
                        Default to OS system appearance or lock to light/dark.
                      </span>
                    </div>
                  </div>

                  <div class="grid-2" style="margin-top: 14px;">
                    <div class="field">
                      <label>Presenter HUD Font Scale</label>
                      <select
                        .value=${this.prefs.hud_font_scale}
                        @change=${(e: Event) =>
                          this.updateField(
                            'hud_font_scale',
                            (e.target as HTMLSelectElement).value
                          )}
                      >
                        <option value="compact">Compact</option>
                        <option value="standard">Standard</option>
                        <option value="large">Large (Teleprompter)</option>
                      </select>
                    </div>
                  </div>

                </div>
                <div class="actions-bar">
                  <button
                    class="btn icon-btn"
                    type="button"
                    @click=${this.resetSettings}
                    title="Reset to Factory Defaults"
                    aria-label="Reset Defaults"
                    data-tooltip="Reset Defaults"
                  >
                    <svg viewBox="0 0 24 24">
                      <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6 0 2.97-2.17 5.43-5.01 5.91v2.02c3.95-.49 7.01-3.85 7.01-7.93 0-4.42-3.58-8-8-8zm-6 8c0-1.65.67-3.15 1.76-4.24L6.34 7.34C4.9 8.78 4 10.79 4 13c0 4.08 3.06 7.44 7.01 7.93v-2.02C8.17 18.43 6 15.97 6 13z" />
                    </svg>
                  </button>
                  <div style="display: flex; align-items: center; gap: 12px;">
                    ${this.saveMessage
                      ? html`<span class="save-toast" data-testid="save-message">${this.saveMessage}</span>`
                      : ''}
                    <button
                      class="btn primary icon-btn"
                      type="button"
                      ?disabled=${this.isSaving}
                      @click=${this.saveSettings}
                      title="Save Workbench Preferences"
                      aria-label="Save Preferences"
                      data-tooltip="Save Preferences"
                    >
                      <svg viewBox="0 0 24 24">
                        <path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          `}
        </div>
      </div>
    `;
  }
}
