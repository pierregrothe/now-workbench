import '../views/now-profile-settings.js';
import '../views/now-team-settings.js';
import '../views/now-groups-settings.js';
import '../views/now-approvals-settings.js';
import '../views/now-impersonation.js';
import '../views/now-limits-settings.js';
import '../views/now-usage-allowances.js';
import '../views/now-usage-card.js';
import { LitElement, html, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './now-admin-panel.js';

import { isAdmin } from '../profile/avatars.js';
import { StoreController } from '../controllers/store-controller.js';
import { workbenchSettingsStyles } from './now-workbench-settings-styles.js';
import { DEFAULT_PREFS, SECTIONS, type SettingsSection, type WorkbenchPreferences } from './settings-model.js';
import './now-capture-prefs.js';
import './now-synthesis-prefs.js';
import './now-workspace-prefs.js';

@customElement('now-workbench-settings')
export class NowWorkbenchSettings extends LitElement {
  static styles = workbenchSettingsStyles;

  @state() private activeSection: SettingsSection = 'profile';
  /** Section requested from outside (the URL or Otto); applied when it changes. */
  @property() section = '';
  private readonly store = new StoreController(this);
  @state() private prefs: WorkbenchPreferences = { ...DEFAULT_PREFS };
  @state() private newApiKeyInput = '';
  @state() private isSaving = false;
  @state() private isVerifyingKey = false;
  @state() private keyVerificationError = '';
  @state() private saveMessage = '';

  protected willUpdate(changed: PropertyValues<this>): void {
    const wanted = SECTIONS.find((sec) => sec.id === this.section);
    if (changed.has('section') && wanted) this.activeSection = wanted.id;
  }

  connectedCallback(): void {
    super.connectedCallback();
    void this.loadSettings();
  }

  private async loadSettings(): Promise<void> {
    try {
      const res = await fetch('/api/settings');
      if (!res.ok) {
        this.saveMessage = `Could not load settings: ${await this.errorDetail(res)}`;
        return;
      }
      this.prefs = (await res.json()) as WorkbenchPreferences;
    } catch (e) {
      // Never present factory defaults as if they were the saved settings (ADR-013).
      this.saveMessage = `Could not load settings: ${e instanceof Error ? e.message : String(e)}`;
    }
  }

  private updateField<K extends keyof WorkbenchPreferences>(
    key: K,
    value: WorkbenchPreferences[K]
  ): void {
    this.prefs = { ...this.prefs, [key]: value };
    this.saveMessage = '';
  }

  private readonly onPrefsChange = (e: CustomEvent<Partial<WorkbenchPreferences>>): void => {
    this.prefs = { ...this.prefs, ...e.detail };
    this.saveMessage = '';
  };

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
      if (!res.ok) {
        this.saveMessage = `Could not reset settings: ${await this.errorDetail(res)}`;
        return;
      }
      this.prefs = (await res.json()) as WorkbenchPreferences;
      this.newApiKeyInput = '';
      this.saveMessage = 'Reset to factory defaults.';
    } catch (e) {
      this.saveMessage = `Could not reset settings: ${e instanceof Error ? e.message : String(e)}`;
    }
  }

  render() {
    const hasKey = this.prefs.has_anthropic_api_key;

    return html`
      <div class="top-bar">
        <div class="title-group">
          <h1>Now Workbench Settings</h1>
        </div>

      </div>

      <div class="prefs-layout">
        <nav class="pref-nav" aria-label="Settings sections">
          ${(this.store.state.profile ? SECTIONS : []).filter((sec) => !sec.adminOnly || isAdmin(this.store.state.profile)).map(
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
      ${this.activeSection === 'profile'
        ? html`<div class="scroll-body"><div class="settings-container"><now-profile-settings></now-profile-settings><now-usage-card></now-usage-card></div></div>`
        : this.activeSection === 'team'
        ? html`<div class="scroll-body"><div class="settings-container"><now-team-settings></now-team-settings><now-usage-allowances></now-usage-allowances></div></div>`
        : this.activeSection === 'groups'
        ? html`<div class="scroll-body"><div class="settings-container"><now-groups-settings .admin=${isAdmin(this.store.state.profile)} .email=${this.store.state.profile?.email ?? ''}></now-groups-settings></div></div>`
        : this.activeSection === 'approvals'
        ? html`<div class="scroll-body"><div class="settings-container"><now-approvals-settings></now-approvals-settings></div></div>`
        : this.activeSection === 'impersonate'
        ? html`<div class="scroll-body"><div class="settings-container"><now-impersonation-settings></now-impersonation-settings></div></div>`
        : this.activeSection === 'limits'
        ? html`<div class="scroll-body"><div class="settings-container"><now-limits-settings></now-limits-settings></div></div>`
        : this.activeSection === 'instances'
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
                      ${this.prefs.anthropic_api_key_from_env
                        ? html`
                            <div class="masked-key-badge locked">
                              <div class="key-info">
                                <span class="key-badge-label">Server key</span>
                                <span class="key-code">${this.prefs.anthropic_api_key_masked}</span>
                              </div>
                            </div>
                            <span class="field-hint">
                              Set in the server's .env file (WORKBENCH_ANTHROPIC_API_KEY). Change it there
                              and restart the container.
                            </span>
                          `
                        : hasKey
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

                ${this.activeSection === 'capture'
                  ? html`<now-capture-prefs .prefs=${this.prefs} @prefs-change=${this.onPrefsChange}></now-capture-prefs>`
                  : this.activeSection === 'synthesis'
                  ? html`<now-synthesis-prefs .prefs=${this.prefs} @prefs-change=${this.onPrefsChange}></now-synthesis-prefs>`
                  : this.activeSection === 'workspace'
                  ? html`<now-workspace-prefs .prefs=${this.prefs} @prefs-change=${this.onPrefsChange}></now-workspace-prefs>`
                  : ''}
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
