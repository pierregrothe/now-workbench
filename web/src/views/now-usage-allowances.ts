// web/src/views/now-usage-allowances.ts
// Administrators see everyone's Claude usage this month and set per-person allowances.
// Author: Pierre Grothe
// Date: 2026-11-07
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { profileSettingsStyles } from './profile-settings-styles.js';
import { api } from './sharing-api.js';

export interface AllowanceView {
  state: 'exempt' | 'ok' | 'warn' | 'refused';
  used: number;
  allowance: number;
  percent: number;
  resets_on: string;
}

interface PersonAllowance extends AllowanceView {
  email: string;
  overridden: boolean;
}

type Notice = { kind: 'ok' | 'error'; text: string } | null;

/** "1,234 of 10,000,000 (0%)", or "1,234 (exempt)" for administrators. */
export function usageLine(a: AllowanceView): string {
  const used = a.used.toLocaleString('en-US');
  if (a.state === 'exempt') return `${used} tokens (administrator, no limit)`;
  return `${used} of ${a.allowance.toLocaleString('en-US')} tokens (${a.percent}%)`;
}

@customElement('now-usage-allowances')
export class NowUsageAllowances extends LitElement {
  static styles = profileSettingsStyles;

  @state() private people: PersonAllowance[] = [];
  @state() private drafts: Record<string, string> = {};
  @state() private notice: Notice = null;
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    api<PersonAllowance[]>('/api/usage/allowances')
      .then((p) => (this.people = p))
      .catch((err: Error) => (this.notice = { kind: 'error', text: `Could not load usage: ${err.message}` }));
  }

  private async save(email: string, tokens: number | null): Promise<void> {
    this.busy = true;
    try {
      this.people = await api<PersonAllowance[]>(`/api/usage/allowances/${encodeURIComponent(email)}`, {
        method: 'PUT',
        body: JSON.stringify({ monthly_tokens: tokens }),
      });
      const { [email]: _done, ...rest } = this.drafts;
      this.drafts = rest;
      this.notice = {
        kind: 'ok',
        text: tokens === null ? `${email} is back on the default allowance.` : `Allowance saved for ${email}.`,
      };
    } catch (err) {
      this.notice = { kind: 'error', text: (err as Error).message };
    } finally {
      this.busy = false;
    }
  }

  private renderPerson(p: PersonAllowance) {
    const draft = this.drafts[p.email] ?? '';
    return html`<li class="usage-row">
      <span class="usage-who">${p.email}</span>
      <span class="hint">${usageLine(p)}${p.overridden ? ' - own allowance' : ''}</span>
      ${p.state === 'exempt'
        ? ''
        : html`<span class="row">
            <input
              type="number"
              min="100000"
              max="1000000000"
              step="100000"
              aria-label="Monthly allowance for ${p.email}"
              placeholder=${String(p.allowance)}
              .value=${draft}
              @input=${(e: Event) => (this.drafts = { ...this.drafts, [p.email]: (e.target as HTMLInputElement).value })}
            />
            <button class="btn primary" ?disabled=${this.busy || !draft} @click=${() => void this.save(p.email, Number(draft))}>Set</button>
            ${p.overridden
              ? html`<button class="btn" ?disabled=${this.busy} @click=${() => void this.save(p.email, null)}>Use default</button>`
              : ''}
          </span>`}
    </li>`;
  }

  render() {
    return html`<section class="card">
      <h2>Claude usage this month</h2>
      <p class="desc">
        Billable tokens each person used since the 1st (UTC), against their monthly allowance. At
        80% Otto warns them; at 100% he stops answering until the 1st or until you raise it.
        Administrators have no limit. The default allowance is under Conversation limits.
      </p>
      <ul class="usage-list">${this.people.map((p) => this.renderPerson(p))}</ul>
      ${this.notice ? html`<div class="msg ${this.notice.kind}" role=${this.notice.kind === 'error' ? 'alert' : 'status'}>${this.notice.text}</div>` : ''}
    </section>`;
  }
}
