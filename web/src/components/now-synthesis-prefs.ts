// web/src/components/now-synthesis-prefs.ts
// Synthesis defaults section of Workbench Settings (author, scope prefix, brand, tone).
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { WorkbenchPreferences } from './settings-model.js';
import { workbenchSettingsStyles } from './now-workbench-settings-styles.js';

/** Edits part of the preferences; raises `prefs-change` with the changed fields (ADR-024). */
@customElement('now-synthesis-prefs')
export class NowSynthesisPrefs extends LitElement {
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
