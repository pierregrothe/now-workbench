// web/src/components/now-capture-prefs.ts
// Media capture defaults section of Workbench Settings (viewport, media type, waits).
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { WorkbenchPreferences } from './settings-model.js';
import { workbenchSettingsStyles } from './now-workbench-settings-styles.js';

/** Edits part of the preferences; raises `prefs-change` with the changed fields (ADR-024). */
@customElement('now-capture-prefs')
export class NowCapturePrefs extends LitElement {
  static styles = [
    workbenchSettingsStyles,
    css`
      /* The settings stylesheet sizes the panel host; a section takes its content height. */
      :host {
        display: block;
        height: auto;
      }
    `,
  ];

  @property({ attribute: false }) prefs!: WorkbenchPreferences;

  private emit(change: Partial<WorkbenchPreferences>): void {
    this.dispatchEvent(new CustomEvent('prefs-change', { detail: change }));
  }

  private change<K extends keyof WorkbenchPreferences>(key: K, value: WorkbenchPreferences[K]): void {
    this.emit({ [key]: value } as Partial<WorkbenchPreferences>);
  }

  private viewportPreset(preset: string): void {
    const [w, h] = preset.split('x').map((v) => Number(v));
    if (w && h) this.emit({ capture_viewport_width: w, capture_viewport_height: h });
  }

  render() {
    const currentViewport = `${this.prefs.capture_viewport_width}x${this.prefs.capture_viewport_height}`;
    return html`
      <div class="section-card">
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
                this.viewportPreset((e.target as HTMLSelectElement).value)}
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
                this.change(
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
                this.change(
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
                this.change(
                  'capture_fake_mode',
                  (e.target as HTMLInputElement).checked
                )}
            />
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-capture-prefs': NowCapturePrefs;
  }
}
