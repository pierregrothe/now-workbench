// web/src/components/now-workspace-prefs.ts
// Workspace section of Workbench Settings (welcome guide, sidebar, presenter HUD).
// Author: Pierre Grothe
// Date: 2026-11-07

import { html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { PrefsSection } from './prefs-section.js';

@customElement('now-workspace-prefs')
export class NowWorkspacePrefs extends PrefsSection {
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
