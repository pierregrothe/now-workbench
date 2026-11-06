// web/src/views/now-impersonation.ts
// "View as" for administrators and group administrators, and the banner shown meanwhile (ADR-020).
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, css, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { profileSettingsStyles } from './profile-settings-styles.js';
import { api } from './sharing-api.js';

interface ImpersonationStatus {
  real_email: string;
  acting_as: string | null;
  candidates: string[];
}

/** The whole app changes identity, so reload everything after a switch. */
function reloadApp(): void {
  window.location.reload();
}

@customElement('now-impersonation-banner')
export class NowImpersonationBanner extends LitElement {
  static styles = css`
    .banner {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 8px 16px;
      background: #fdf0c8;
      color: #4a3b00;
      font-size: 13px;
    }
    button {
      border: none;
      border-radius: 10px;
      padding: 5px 12px;
      background: #16181d;
      color: #ffffff;
      font: inherit;
      font-size: 12.5px;
      cursor: pointer;
    }
  `;

  @state() private status: ImpersonationStatus | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    api<ImpersonationStatus>('/api/impersonation')
      .then((s) => (this.status = s))
      .catch(() => (this.status = null));
  }

  private async stop(): Promise<void> {
    await api('/api/impersonation', { method: 'DELETE' });
    reloadApp();
  }

  render() {
    if (!this.status?.acting_as) return html``;
    return html`<div class="banner" role="status">
      <span>Viewing as <strong>${this.status.acting_as}</strong> (you are ${this.status.real_email}). Everything you do here is done as them.</span>
      <button @click=${() => void this.stop()}>Stop viewing as</button>
    </div>`;
  }
}

@customElement('now-impersonation-settings')
export class NowImpersonationSettings extends LitElement {
  static styles = [
    profileSettingsStyles,
    css`
      .person {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid rgba(0, 0, 0, 0.06);
        padding: 8px 0;
        font-size: 13px;
      }
    `,
  ];

  @state() private status: ImpersonationStatus | null = null;
  @state() private error = '';

  connectedCallback(): void {
    super.connectedCallback();
    api<ImpersonationStatus>('/api/impersonation')
      .then((s) => (this.status = s))
      .catch((err: Error) => (this.error = `Could not load: ${err.message}`));
  }

  private async viewAs(email: string): Promise<void> {
    try {
      await api('/api/impersonation', { method: 'POST', body: JSON.stringify({ email }) });
      reloadApp();
    } catch (err) {
      this.error = (err as Error).message;
    }
  }

  render() {
    const people = this.status?.candidates ?? [];
    return html`<section class="card">
      <h2>View as someone</h2>
      <p class="desc">
        See and do exactly what another person can, to help them or check their setup.
        Administrators can view as anyone; group administrators as their groups' members.
        Every start and stop is logged.
      </p>
      ${people.length === 0 ? html`<p class="hint">There is nobody you can view as.</p>` : ''}
      ${people.map(
        (email) => html`<div class="person">
          <span>${email}</span>
          <button class="btn" @click=${() => void this.viewAs(email)}>View as</button>
        </div>`
      )}
      ${this.error ? html`<div class="msg error" role="alert">${this.error}</div>` : ''}
    </section>`;
  }
}
