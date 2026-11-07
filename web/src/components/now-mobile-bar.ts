// web/src/components/now-mobile-bar.ts
// Phone top bar: opens the navigation drawer and names the current screen.
// Author: Pierre Grothe
// Date: 2026-11-07
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { menuToggleIcon, searchIcon } from '../icons.js';
import { OPEN_PALETTE_EVENT } from './now-command-palette.js';
import { mobileBarStyles } from './now-mobile-bar-styles.js';

const TITLES: Record<string, string> = {
  home: 'Otto',
  synthesizer: 'Use-Case Synthesizer',
  capture: 'Media Capture',
  artifacts: 'Artifact library',
  fluent: 'Fluent SDK Explorer',
  actions: 'Actions',
  admin: 'Workbench Settings',
};

/** Fires `menu-toggle` from the menu button and opens the command palette from the search button. */
@customElement('now-mobile-bar')
export class NowMobileBar extends LitElement {
  static styles = mobileBarStyles;

  @property({ type: String }) tab = 'home';
  @property({ type: Boolean }) open = false;

  render() {
    return html`
      <button
        aria-label=${this.open ? 'Close navigation' : 'Open navigation'}
        aria-expanded=${this.open ? 'true' : 'false'}
        aria-controls="navigation"
        @click=${() => this.dispatchEvent(new CustomEvent('menu-toggle', { bubbles: true, composed: true }))}
      >
        ${menuToggleIcon(!this.open, 22)}
      </button>
      <h1>${TITLES[this.tab] ?? 'Now Workbench'}</h1>
      <button
        class="palette"
        aria-label="Open command palette"
        @click=${() => this.dispatchEvent(new CustomEvent(OPEN_PALETTE_EVENT, { bubbles: true, composed: true }))}
      >
        ${searchIcon(20)}
      </button>
    `;
  }
}
