// web/src/views/now-share-dialog.ts
// Versions and sharing for one artifact the signed-in person owns (PRD-003, ADR-018).
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { profileSettingsStyles } from './profile-settings-styles.js';
import {
  KIND_LABELS,
  api,
  shareTargetLabel,
  type ArtifactShare,
  type ArtifactVersion,
  type Group,
} from './sharing-api.js';

type Notice = { kind: 'ok' | 'error'; text: string } | null;

const STATUS_LABEL: Record<ArtifactShare['status'], string> = {
  pending: 'Waiting for approval',
  approved: 'Shared',
  rejected: 'Declined',
  superseded: 'Replaced',
};

@customElement('now-share-dialog')
export class NowShareDialog extends LitElement {
  static styles = [
    profileSettingsStyles,
    css`
      :host {
        position: fixed;
        inset: 0;
        z-index: 1000;
        background: rgba(22, 24, 29, 0.32);
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .card {
        width: min(560px, 92vw);
        max-height: 86vh;
        overflow: auto;
      }
      .head {
        display: flex;
        justify-content: space-between;
        align-items: start;
        gap: 12px;
      }
      ul {
        list-style: none;
        padding: 0;
        margin: 0 0 16px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        font-size: 13px;
      }
      li {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
      }
      .chip {
        font-size: 11.5px;
        padding: 2px 8px;
        border-radius: 999px;
        background: #efece7;
      }
      .chip.approved {
        background: #dcf5d6;
      }
      .chip.pending {
        background: #fdf0c8;
      }
      h3 {
        font-size: 13px;
        margin: 14px 0 8px;
      }
      select {
        flex: 1;
        padding: 8px 10px;
        border-radius: 10px;
        border: 1px solid rgba(0, 0, 0, 0.12);
        font: inherit;
      }
    `,
  ];

  @property({ type: String }) artifactId = '';
  @property({ type: String }) artifactName = '';

  @state() private versions: ArtifactVersion[] = [];
  @state() private shares: ArtifactShare[] = [];
  @state() private groups: Group[] = [];
  @state() private note = '';
  @state() private target = 'global';
  @state() private notice: Notice = null;
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private base(): string {
    return `/api/artifacts/${encodeURIComponent(this.artifactId)}`;
  }

  private async load(): Promise<void> {
    try {
      const [versions, shares, groups] = await Promise.all([
        api<ArtifactVersion[]>(`${this.base()}/versions`),
        api<ArtifactShare[]>(`${this.base()}/shares`),
        api<Group[]>('/api/groups'),
      ]);
      this.versions = versions;
      this.shares = shares;
      this.groups = groups.filter((g) => g.my_status === 'active');
    } catch (err) {
      this.notice = { kind: 'error', text: `Could not load sharing: ${(err as Error).message}` };
    }
  }

  private async run(action: () => Promise<unknown>, ok: string): Promise<void> {
    this.busy = true;
    try {
      await action();
      this.notice = { kind: 'ok', text: ok };
      await this.load();
      this.dispatchEvent(new CustomEvent('sharing-changed', { bubbles: true, composed: true }));
    } catch (err) {
      this.notice = { kind: 'error', text: (err as Error).message };
    } finally {
      this.busy = false;
    }
  }

  private saveVersion(): Promise<void> {
    return this.run(async () => {
      const v = await api<ArtifactVersion>(`${this.base()}/versions`, {
        method: 'POST',
        body: JSON.stringify({ note: this.note }),
      });
      this.note = '';
      return v;
    }, 'Version saved.');
  }

  private share(): Promise<void> {
    const body =
      this.target === 'global' ? { target: 'global' } : { target: 'group', group_id: this.target };
    return this.run(
      () => api(`${this.base()}/shares`, { method: 'POST', body: JSON.stringify(body) }),
      'Share requested.'
    );
  }

  private withdraw(s: ArtifactShare): Promise<void> {
    return this.run(
      () => api(`${this.base()}/shares/${encodeURIComponent(s.id)}`, { method: 'DELETE' }),
      s.status === 'pending' ? 'Request withdrawn.' : 'No longer shared.'
    );
  }

  private close(): void {
    this.dispatchEvent(new CustomEvent('close', { bubbles: true, composed: true }));
  }

  render() {
    const latest = this.versions[0];
    return html`
      <section class="card" role="dialog" aria-modal="true" aria-label="Share ${this.artifactName}">
        <div class="head">
          <div>
            <h2>Share "${this.artifactName}"</h2>
            <p class="desc">
              Sharing shows a frozen version, read-only. Each new version needs approval again;
              until then people keep the last approved one.
            </p>
          </div>
          <button class="btn" aria-label="Close" @click=${this.close}>Close</button>
        </div>

        <h3>Versions</h3>
        <ul>
          ${this.versions.slice(0, 5).map(
            (v) => html`<li>
              <span><strong>v${v.version}</strong> ${v.note || ''}</span>
              <span class="hint">${v.created_at.slice(0, 10)}</span>
            </li>`
          )}
        </ul>
        <div class="row">
          <input type="text" aria-label="What changed" placeholder="What changed (optional)" .value=${this.note} @input=${(e: Event) => (this.note = (e.target as HTMLInputElement).value)} />
          <button class="btn" ?disabled=${this.busy} @click=${() => void this.saveVersion()}>Save version</button>
        </div>

        <h3>Shared with</h3>
        <ul>
          ${this.shares.length === 0 ? html`<li class="hint">Only you.</li>` : ''}
          ${this.shares.map(
            (s) => html`<li>
              <span>${shareTargetLabel(s)} &middot; v${s.version}</span>
              <span>
                <span class="chip ${s.status}">${STATUS_LABEL[s.status]}</span>
                <button class="btn" ?disabled=${this.busy} @click=${() => void this.withdraw(s)}>
                  ${s.status === 'pending' ? 'Withdraw' : 'Stop sharing'}
                </button>
              </span>
            </li>`
          )}
        </ul>
        <div class="row">
          <select aria-label="Share with" .value=${this.target} @change=${(e: Event) => (this.target = (e.target as HTMLSelectElement).value)}>
            <option value="global">Everyone (an administrator approves)</option>
            ${this.groups.map(
              (g) => html`<option value=${g.id}>${g.name} (${KIND_LABELS[g.kind]})</option>`
            )}
          </select>
          <button class="btn primary" ?disabled=${this.busy || !latest} @click=${() => void this.share()}>
            Share v${latest?.version ?? '-'}
          </button>
        </div>
        ${this.notice ? html`<div class="msg ${this.notice.kind}" role=${this.notice.kind === 'error' ? 'alert' : 'status'}>${this.notice.text}</div>` : ''}
      </section>
    `;
  }
}
