// web/src/views/now-usage-card.ts
// Everyone sees their own Claude usage this month and their allowance (ADR-031).
// Author: Pierre Grothe
// Date: 2026-11-07
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { profileSettingsStyles } from './profile-settings-styles.js';
import { api } from './sharing-api.js';
import { usageLine, type AllowanceView } from './now-usage-allowances.js';

@customElement('now-usage-card')
export class NowUsageCard extends LitElement {
  static styles = profileSettingsStyles;

  @state() private standing: AllowanceView | null = null;
  @state() private error = '';

  connectedCallback(): void {
    super.connectedCallback();
    api<AllowanceView>('/api/usage/allowance')
      .then((a) => (this.standing = a))
      .catch((err: Error) => (this.error = `Could not load your usage: ${err.message}`));
  }

  render() {
    const a = this.standing;
    return html`<section class="card">
      <h2>Claude usage this month</h2>
      ${a
        ? html`<p class="desc" data-testid="own-usage">
            ${usageLine(a)}. ${a.state === 'exempt' ? '' : html`It resets on ${a.resets_on}.`}
          </p>`
        : ''}
      ${this.error ? html`<div class="msg error" role="alert">${this.error}</div>` : ''}
    </section>`;
  }
}
