// web/src/components/now-workspace-prefs.ts
// Workspace section of Workbench Settings (welcome guide, sidebar, presenter HUD).
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { WorkbenchPreferences } from './settings-model.js';
import { workbenchSettingsStyles } from './now-workbench-settings-styles.js';

/** Edits part of the preferences; raises `prefs-change` with the changed fields (ADR-024). */
@customElement('now-workspace-prefs')
export class NowWorkspacePrefs extends LitElement {
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

  render() {
    return html`
      <div class="section-card">
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
                this.change(
                  'show_welcome_on_startup',
                  (e.target as HTMLInputElement).checked
                )}
            />
          </div>

        </div>

        <div class="grid-2" style="margin-top: 14px;">
          <div class="field">
            <label>Presenter HUD Font Scale</label>
            <select
              .value=${this.prefs.hud_font_scale}
              @change=${(e: Event) =>
                this.change(
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
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-workspace-prefs': NowWorkspacePrefs;
  }
}
