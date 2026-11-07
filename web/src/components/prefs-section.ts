// web/src/components/prefs-section.ts
// Base class of the Workbench Settings preference sections (capture, synthesis, workspace).
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, css } from 'lit';
import { property } from 'lit/decorators.js';
import type { WorkbenchPreferences } from './settings-model.js';
import { workbenchSettingsStyles } from './now-workbench-settings-styles.js';

/**
 * A section edits part of the preferences it is given and raises `prefs-change` with the
 * changed fields; the settings panel merges them and saves once (ADR-024).
 */
export class PrefsSection extends LitElement {
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

  protected emit(change: Partial<WorkbenchPreferences>): void {
    this.dispatchEvent(new CustomEvent('prefs-change', { detail: change }));
  }

  protected change<K extends keyof WorkbenchPreferences>(key: K, value: WorkbenchPreferences[K]): void {
    this.emit({ [key]: value } as Partial<WorkbenchPreferences>);
  }
}
