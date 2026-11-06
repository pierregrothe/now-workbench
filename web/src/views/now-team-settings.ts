// web/src/views/now-team-settings.ts
// Admin-only Team settings: who may use the workbench and with which roles.
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { ROLE_LABELS } from '../profile/avatars.js';
import { profileSettingsStyles } from './profile-settings-styles.js';

interface Member {
  email: string;
  roles: string[];
  added_by: string;
  created_at: string;
}

type Notice = { kind: 'ok' | 'error'; text: string } | null;

@customElement('now-team-settings')
export class NowTeamSettings extends LitElement {
  static styles = profileSettingsStyles;

  @state() private members: Member[] = [];
  @state() private email = '';
  @state() private asAdmin = false;
  @state() private asConsultant = true;
  @state() private notice: Notice = null;
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async request(url: string, init: RequestInit = {}): Promise<void> {
    this.busy = true;
    try {
      const res = await fetch(url, init);
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = (body as { detail?: unknown }).detail;
        throw new Error(typeof d === 'string' ? d : `HTTP ${res.status}`);
      }
      this.members = body as Member[];
    } finally {
      this.busy = false;
    }
  }

  private async load(): Promise<void> {
    try {
      await this.request('/api/team');
    } catch (err) {
      this.notice = { kind: 'error', text: `Could not load the team: ${(err as Error).message}` };
    }
  }

  private async put(email: string, admin: boolean, consultant: boolean, ok: string): Promise<void> {
    try {
      await this.request(`/api/team/${encodeURIComponent(email)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ admin, solution_consultant: consultant }),
      });
      this.notice = { kind: 'ok', text: ok };
    } catch (err) {
      this.notice = { kind: 'error', text: (err as Error).message };
    }
  }

  private async add(e: Event): Promise<void> {
    e.preventDefault();
    await this.put(this.email.trim(), this.asAdmin, this.asConsultant, `${this.email.trim()} added.`);
    if (this.notice?.kind === 'ok') this.email = '';
  }

  private async toggle(m: Member, role: string): Promise<void> {
    const has = new Set(m.roles);
    if (has.has(role)) has.delete(role);
    else has.add(role);
    await this.put(m.email, has.has('admin'), has.has('solution_consultant'), `Roles updated for ${m.email}.`);
  }

  private async removeMember(m: Member): Promise<void> {
    try {
      await this.request(`/api/team/${encodeURIComponent(m.email)}`, { method: 'DELETE' });
      this.notice = { kind: 'ok', text: `${m.email} removed.` };
    } catch (err) {
      this.notice = { kind: 'error', text: (err as Error).message };
    }
  }

  render() {
    return html`
      <section class="card">
        <h2>Team</h2>
        <p class="desc">People who may use this workbench once Cloudflare has signed them in. Use the email their Apple or Google account reports.</p>
        <table style="width:100%; border-collapse:collapse; font-size:13px;">
          <thead><tr style="text-align:left; color:#6b7280;"><th style="padding:6px 0;">Email</th><th>${ROLE_LABELS.admin}</th><th>${ROLE_LABELS.solution_consultant}</th><th></th></tr></thead>
          <tbody>
            ${this.members.map(
              (m) => html`<tr style="border-top:1px solid rgba(0,0,0,0.06);">
                <td style="padding:8px 0;">${m.email}</td>
                <td><input type="checkbox" aria-label="${ROLE_LABELS.admin} for ${m.email}" .checked=${m.roles.includes('admin')} ?disabled=${this.busy} @change=${() => void this.toggle(m, 'admin')} /></td>
                <td><input type="checkbox" aria-label="${ROLE_LABELS.solution_consultant} for ${m.email}" .checked=${m.roles.includes('solution_consultant')} ?disabled=${this.busy} @change=${() => void this.toggle(m, 'solution_consultant')} /></td>
                <td style="text-align:right;"><button class="btn" ?disabled=${this.busy} @click=${() => void this.removeMember(m)}>Remove</button></td>
              </tr>`
            )}
          </tbody>
        </table>
        <form class="row" @submit=${this.add}>
          <input type="email" aria-label="New member email" placeholder="name@example.com" required .value=${this.email} @input=${(e: Event) => (this.email = (e.target as HTMLInputElement).value)} />
          <label class="hint"><input type="checkbox" .checked=${this.asAdmin} @change=${(e: Event) => (this.asAdmin = (e.target as HTMLInputElement).checked)} /> ${ROLE_LABELS.admin}</label>
          <label class="hint"><input type="checkbox" .checked=${this.asConsultant} @change=${(e: Event) => (this.asConsultant = (e.target as HTMLInputElement).checked)} /> ${ROLE_LABELS.solution_consultant}</label>
          <button class="btn primary" type="submit" ?disabled=${this.busy}>Add person</button>
        </form>
        ${this.notice ? html`<div class="msg ${this.notice.kind}" role=${this.notice.kind === 'error' ? 'alert' : 'status'}>${this.notice.text}</div>` : ''}
      </section>
    `;
  }
}
