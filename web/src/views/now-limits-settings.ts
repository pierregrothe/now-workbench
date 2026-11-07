// web/src/views/now-limits-settings.ts
// Administrators set the conversation limits that apply to everyone (ADR-021).
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { profileSettingsStyles } from './profile-settings-styles.js';
import { api } from './sharing-api.js';

interface Limits {
  max_conversation_tokens: number;
  compact_at_tokens: number;
  max_age_days: number;
  max_file_mb: number;
  max_conversation_mb: number;
  max_files: number;
  monthly_allowance_tokens: number;
}

const FIELDS: { key: keyof Limits; label: string; min: number; max: number }[] = [
  { key: 'max_conversation_tokens', label: 'Tokens per conversation', min: 50000, max: 50000000 },
  { key: 'compact_at_tokens', label: 'Summarize the conversation at (tokens)', min: 50000, max: 900000 },
  { key: 'max_age_days', label: 'Days a conversation stays open', min: 1, max: 3650 },
  { key: 'max_file_mb', label: 'Largest file (MB)', min: 1, max: 32 },
  { key: 'max_conversation_mb', label: 'Files per conversation, total (MB)', min: 1, max: 100 },
  { key: 'max_files', label: 'Files per conversation', min: 1, max: 50 },
  {
    key: 'monthly_allowance_tokens',
    label: 'Monthly Claude allowance per person (tokens; administrators exempt)',
    min: 100000,
    max: 1000000000,
  },
];

type Notice = { kind: 'ok' | 'error'; text: string } | null;

@customElement('now-limits-settings')
export class NowLimitsSettings extends LitElement {
  static styles = profileSettingsStyles;

  @state() private limits: Limits | null = null;
  @state() private notice: Notice = null;
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    api<Limits>('/api/limits')
      .then((l) => (this.limits = l))
      .catch((err: Error) => (this.notice = { kind: 'error', text: `Could not load: ${err.message}` }));
  }

  private async save(e: Event): Promise<void> {
    e.preventDefault();
    if (!this.limits) return;
    this.busy = true;
    try {
      this.limits = await api<Limits>('/api/limits', {
        method: 'PUT',
        body: JSON.stringify(this.limits),
      });
      this.notice = { kind: 'ok', text: 'Limits saved. They apply to everyone right away.' };
    } catch (err) {
      this.notice = { kind: 'error', text: (err as Error).message };
    } finally {
      this.busy = false;
    }
  }

  render() {
    const limits = this.limits;
    return html`<section class="card">
      <h2>Conversation limits</h2>
      <p class="desc">
        Keep Claude usage predictable for everyone. Tokens are counted as billed (cached input at
        a tenth). Long conversations are summarized automatically; when one uses its token
        budget, Otto asks to start a new one. Attached files can be PDFs, images or text.
      </p>
      ${limits
        ? html`<form @submit=${this.save}>
            <div class="fields">
              ${FIELDS.map(
                (f) => html`<label class="field">
                  ${f.label}
                  <input
                    type="number"
                    min=${f.min}
                    max=${f.max}
                    required
                    .value=${String(limits[f.key])}
                    @input=${(e: Event) => {
                      const value = Number((e.target as HTMLInputElement).value);
                      this.limits = { ...limits, [f.key]: value };
                    }}
                  />
                </label>`
              )}
            </div>
            <div class="row">
              <button class="btn primary" type="submit" ?disabled=${this.busy}>Save limits</button>
            </div>
          </form>`
        : ''}
      ${this.notice ? html`<div class="msg ${this.notice.kind}" role=${this.notice.kind === 'error' ? 'alert' : 'status'}>${this.notice.text}</div>` : ''}
    </section>`;
  }
}
