// web/src/views/now-approvals-settings.ts
// Approvals inbox: shares and join requests the signed-in person may decide (PRD-003).
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, css, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { profileSettingsStyles } from './profile-settings-styles.js';
import { api, shareTargetLabel, type ApprovalInbox } from './sharing-api.js';

type Notice = { kind: 'ok' | 'error'; text: string } | null;

@customElement('now-approvals-settings')
export class NowApprovalsSettings extends LitElement {
  static styles = [
    profileSettingsStyles,
    css`
      .item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        border-top: 1px solid rgba(0, 0, 0, 0.06);
        padding: 10px 0;
        font-size: 13px;
      }
      .sub {
        font-size: 11.5px;
        color: #6b7280;
      }
      h3 {
        font-size: 13px;
        margin: 16px 0 6px;
      }
    `,
  ];

  @state() private inbox: ApprovalInbox = { shares: [], join_requests: [], group_names: {} };
  @state() private notice: Notice = null;
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      this.inbox = await api<ApprovalInbox>('/api/approvals');
    } catch (err) {
      this.notice = { kind: 'error', text: `Could not load approvals: ${(err as Error).message}` };
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

  private decide(id: string, approve: boolean): void {
    const body = JSON.stringify({ approve });
    void this.run(
      () => api(`/api/approvals/shares/${encodeURIComponent(id)}`, { method: 'POST', body }),
      approve ? 'Approved: members now see this version.' : 'Declined.'
    );
  }

  private member(groupId: string, email: string, accept: boolean): void {
    const url = `/api/groups/${groupId}/members/${encodeURIComponent(email)}`;
    void this.run(
      () =>
        accept
          ? api(url, { method: 'PUT', body: JSON.stringify({ role: 'member' }) })
          : api(url, { method: 'DELETE' }),
      accept ? `${email} accepted.` : `${email} declined.`
    );
  }

  render() {
    const { shares, join_requests: joins, group_names: names } = this.inbox;
    return html`
      <section class="card">
        <h2>Approvals</h2>
        <p class="desc">Artifacts waiting to be shared with a group you administer (or with everyone, for administrators), and people asking to join your groups.</p>
        ${shares.length === 0 && joins.length === 0 ? html`<p class="hint">Nothing is waiting for you.</p>` : ''}
        ${shares.length
          ? html`<h3>Shares</h3>
              ${shares.map(
                (s) => html`<div class="item">
                  <div>
                    <strong>${s.artifact_name}</strong> v${s.version} &rarr; ${shareTargetLabel(s)}
                    <div class="sub">Requested by ${s.requested_by} on ${s.requested_at.slice(0, 10)}</div>
                  </div>
                  <span>
                    <button class="btn primary" ?disabled=${this.busy} @click=${() => this.decide(s.id, true)}>Approve</button>
                    <button class="btn" ?disabled=${this.busy} @click=${() => this.decide(s.id, false)}>Decline</button>
                  </span>
                </div>`
              )}`
          : ''}
        ${joins.length
          ? html`<h3>Join requests</h3>
              ${joins.map(
                (r) => html`<div class="item">
                  <div>
                    <strong>${r.email}</strong> &rarr; ${names[r.group_id] ?? r.group_id}
                    <div class="sub">Asked on ${r.requested_at.slice(0, 10)}</div>
                  </div>
                  <span>
                    <button class="btn primary" ?disabled=${this.busy} @click=${() => this.member(r.group_id, r.email, true)}>Accept</button>
                    <button class="btn" ?disabled=${this.busy} @click=${() => this.member(r.group_id, r.email, false)}>Decline</button>
                  </span>
                </div>`
              )}`
          : ''}
        ${this.notice ? html`<div class="msg ${this.notice.kind}" role=${this.notice.kind === 'error' ? 'alert' : 'status'}>${this.notice.text}</div>` : ''}
      </section>
    `;
  }
}
