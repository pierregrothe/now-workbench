// web/src/components/now-synthesis-prefs.ts
// Synthesis defaults section of Workbench Settings (author, scope prefix, brand, tone).
// Author: Pierre Grothe
// Date: 2026-11-07

import { html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { PrefsSection } from './prefs-section.js';

@customElement('now-synthesis-prefs')
export class NowSynthesisPrefs extends PrefsSection {
  render() {
    return html`
      <div class="section-card">
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
                this.change(
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
                this.change(
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
                this.change(
                  'default_scoped_prefix',
                  (e.target as HTMLInputElement).value
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
    'now-synthesis-prefs': NowSynthesisPrefs;
  }
}
