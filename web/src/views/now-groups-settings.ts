// web/src/views/now-groups-settings.ts
// Groups (region, territory, business unit): join, leave, and manage members (PRD-003).
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { profileSettingsStyles } from './profile-settings-styles.js';
import { KIND_LABELS, api, type Group, type GroupKind, type GroupMember } from './sharing-api.js';

type Notice = { kind: 'ok' | 'error'; text: string } | null;

@customElement('now-groups-settings')
export class NowGroupsSettings extends LitElement {
  static styles = [
    profileSettingsStyles,
    css`
      .group {
        border-top: 1px solid rgba(0, 0, 0, 0.06);
        padding: 12px 0;
        font-size: 13px;
      }
      .group-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
      }
      .kind {
        font-size: 11.5px;
        color: #6b7280;
      }
      .members {
        margin-top: 10px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .member {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
      }
      select {
        padding: 8px 10px;
        border-radius: 10px;
        border: 1px solid rgba(0, 0, 0, 0.12);
        font: inherit;
      }
    `,
  ];

  /** True when the signed-in person is a workbench administrator. */
  @property({ type: Boolean }) admin = false;
  /** The signed-in person's email (used to leave a group). */
  @property({ type: String }) email = '';

  @state() private groups: Group[] = [];
  @state() private open: string | null = null;
  @state() private members: GroupMember[] = [];
  @state() private name = '';
  @state() private kind: GroupKind = 'region';
  @state() private addEmail = '';
  @state() private notice: Notice = null;
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      this.groups = await api<Group[]>('/api/groups');
      if (this.open) this.members = await api<GroupMember[]>(`/api/groups/${this.open}/members`);
    } catch (err) {
      this.notice = { kind: 'error', text: `Could not load groups: ${(err as Error).message}` };
    }
  }

  private async run(action: () => Promise<unknown>, ok: string): Promise<void> {
    this.busy = true;
    try {
      await action();
      this.notice = { kind: 'ok', text: ok };
      await this.load();
    } catch (err) {
      this.notice = { kind: 'error', text: (err as Error).message };
    } finally {
      this.busy = false;
    }
  }

  private create(e: Event): void {
    e.preventDefault();
    const body = JSON.stringify({ name: this.name.trim(), kind: this.kind });
    void this.run(async () => {
      await api('/api/groups', { method: 'POST', body });
      this.name = '';
    }, `Group "${this.name.trim()}" created.`);
  }

  private async manage(g: Group): Promise<void> {
    this.open = this.open === g.id ? null : g.id;
    this.members = [];
    await this.load();
  }

  private putMember(g: Group, email: string, role: 'member' | 'admin', ok: string): void {
    const url = `/api/groups/${g.id}/members/${encodeURIComponent(email)}`;
    void this.run(() => api(url, { method: 'PUT', body: JSON.stringify({ role }) }), ok);
  }

  private removeMember(g: Group, email: string, ok: string): void {
    const url = `/api/groups/${g.id}/members/${encodeURIComponent(email)}`;
    void this.run(() => api(url, { method: 'DELETE' }), ok);
  }

  private canManage(g: Group): boolean {
    return this.admin || (g.my_status === 'active' && g.my_role === 'admin');
  }

  private renderMembers(g: Group) {
    return html`<div class="members">
      ${this.members.map(
        (m) => html`<div class="member">
          <span>${m.email}${m.role === 'admin' ? ' (group admin)' : ''}${m.status === 'pending' ? ' - asked to join' : ''}</span>
          <span>
            ${m.status === 'pending'
              ? html`<button class="btn primary" ?disabled=${this.busy} @click=${() => this.putMember(g, m.email, 'member', `${m.email} accepted.`)}>Accept</button>`
              : ''}
            ${this.admin && m.status === 'active'
              ? html`<button class="btn" ?disabled=${this.busy} @click=${() => this.putMember(g, m.email, m.role === 'admin' ? 'member' : 'admin', 'Role updated.')}>
                  ${m.role === 'admin' ? 'Make member' : 'Make group admin'}
                </button>`
              : ''}
            <button class="btn" ?disabled=${this.busy} @click=${() => this.removeMember(g, m.email, `${m.email} removed.`)}>
              ${m.status === 'pending' ? 'Decline' : 'Remove'}
            </button>
          </span>
        </div>`
      )}
      <form class="row" @submit=${(e: Event) => {
        e.preventDefault();
        this.putMember(g, this.addEmail.trim(), 'member', `${this.addEmail.trim()} added.`);
        this.addEmail = '';
      }}>
        <input type="email" aria-label="Add member email" placeholder="name@example.com" required .value=${this.addEmail} @input=${(e: Event) => (this.addEmail = (e.target as HTMLInputElement).value)} />
        <button class="btn" type="submit" ?disabled=${this.busy}>Add member</button>
      </form>
    </div>`;
  }

  private renderGroup(g: Group) {
    const mine = g.my_status === 'active';
    return html`<div class="group">
      <div class="group-head">
        <div>
          <strong>${g.name}</strong>
          <div class="kind">${KIND_LABELS[g.kind]} &middot; ${g.member_count} member(s)${g.my_role === 'admin' && mine ? ' &middot; you administer it' : ''}</div>
        </div>
        <span>
          ${g.my_status === null
            ? html`<button class="btn" ?disabled=${this.busy} @click=${() => void this.run(() => api(`/api/groups/${g.id}/join`, { method: 'POST' }), `Asked to join ${g.name}.`)}>Ask to join</button>`
            : g.my_status === 'pending'
            ? html`<span class="hint">Request pending</span>`
            : html`<button class="btn" ?disabled=${this.busy} @click=${() => this.removeMember(g, this.email, `You left ${g.name}.`)}>Leave</button>`}
          ${this.canManage(g) ? html`<button class="btn" @click=${() => void this.manage(g)}>${this.open === g.id ? 'Done' : 'Manage'}</button>` : ''}
          ${this.admin ? html`<button class="btn" ?disabled=${this.busy} @click=${() => void this.run(() => api(`/api/groups/${g.id}`, { method: 'DELETE' }), `${g.name} deleted.`)}>Delete</button>` : ''}
        </span>
      </div>
      ${this.open === g.id ? this.renderMembers(g) : ''}
    </div>`;
  }

  render() {
    return html`
      <section class="card">
        <h2>Groups</h2>
        <p class="desc">Regions, territories and business units. Join the ones you work with to share demos with them; a group administrator accepts each request.</p>
        ${this.groups.length === 0 ? html`<p class="hint">No groups yet.</p>` : ''}
        ${this.groups.map((g) => this.renderGroup(g))}
        ${this.admin
          ? html`<form class="row" @submit=${this.create}>
              <input type="text" aria-label="New group name" placeholder="Group name" required minlength="2" .value=${this.name} @input=${(e: Event) => (this.name = (e.target as HTMLInputElement).value)} />
              <select aria-label="Group kind" .value=${this.kind} @change=${(e: Event) => (this.kind = (e.target as HTMLSelectElement).value as GroupKind)}>
                ${(Object.keys(KIND_LABELS) as GroupKind[]).map((k) => html`<option value=${k}>${KIND_LABELS[k]}</option>`)}
              </select>
              <button class="btn primary" type="submit" ?disabled=${this.busy}>Create group</button>
            </form>`
          : ''}
        ${this.notice ? html`<div class="msg ${this.notice.kind}" role=${this.notice.kind === 'error' ? 'alert' : 'status'}>${this.notice.text}</div>` : ''}
      </section>
    `;
  }
}
