// web/src/views/now-reply-feedback.ts
// The row under each Otto reply: thumbs up or down, an optional comment, and Get help.
// Author: Pierre Grothe
// Date: 2026-11-07
import { LitElement, html } from 'lit';
import type { PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { thumbIcon } from '../icons.js';
import { replyFeedbackStyles } from './reply-feedback-styles.js';
import { api } from './sharing-api.js';

export type Rating = 'up' | 'down';

/** A stored rating as the API returns it (also listed in Settings). */
export interface ReplyFeedback {
  message_id: string;
  thread_id: string;
  owner_email: string;
  rating: Rating;
  comment: string;
  reply: string;
  created_at: string;
  updated_at: string;
}

/**
 * Rates one stored reply. Rating again replaces the stored rating (and its comment). Feedback
 * stays in the workbench; Get help opens the help guide through the `open-welcome` event.
 */
@customElement('now-reply-feedback')
export class NowReplyFeedback extends LitElement {
  static styles = replyFeedbackStyles;

  @property({ attribute: false }) messageId = '';
  /** The stored rating from the thread history. */
  @property({ attribute: false }) rating: Rating | null = null;

  @state() private current: Rating | null = null;
  @state() private comment = '';
  @state() private draft = '';
  @state() private commentOpen = false;
  @state() private busy = false;
  @state() private note: { kind: 'ok' | 'error'; text: string } | null = null;

  willUpdate(changed: PropertyValues<this>): void {
    if (changed.has('rating')) this.current = this.rating;
  }

  private async save(rating: Rating, comment: string): Promise<void> {
    this.busy = true;
    this.note = null;
    try {
      const saved = await api<ReplyFeedback>(`/api/feedback/${encodeURIComponent(this.messageId)}`, {
        method: 'PUT',
        body: JSON.stringify({ rating, comment }),
      });
      this.current = saved.rating;
      this.comment = saved.comment;
      this.note = { kind: 'ok', text: saved.comment ? 'Thanks, comment saved.' : 'Thanks for the feedback.' };
    } catch (err) {
      this.note = { kind: 'error', text: `Could not save: ${(err as Error).message}` };
    } finally {
      this.busy = false;
    }
  }

  private rate(rating: Rating): void {
    this.commentOpen = true;
    this.draft = this.comment;
    void this.save(rating, this.comment);
  }

  private sendComment(): void {
    if (!this.current) return;
    this.commentOpen = false;
    void this.save(this.current, this.draft.trim());
  }

  private thumb(rating: Rating, label: string) {
    const chosen = this.current === rating;
    return html`<button
      type="button"
      class="fb-btn"
      aria-label=${label}
      title=${label}
      aria-pressed=${chosen ? 'true' : 'false'}
      ?disabled=${this.busy}
      @click=${() => this.rate(rating)}
    >
      ${thumbIcon(rating === 'down', chosen)}
    </button>`;
  }

  render() {
    return html`
      <div class="row">
        ${this.thumb('up', 'Good reply')} ${this.thumb('down', 'Bad reply')}
        <button
          type="button"
          class="fb-btn"
          @click=${() => this.dispatchEvent(new CustomEvent('open-welcome', { bubbles: true, composed: true }))}
        >
          Get help
        </button>
        ${this.note
          ? html`<span class="note ${this.note.kind}" role=${this.note.kind === 'error' ? 'alert' : 'status'}>${this.note.text}</span>`
          : ''}
      </div>
      ${this.commentOpen && this.current
        ? html`<div class="comment">
            <input
              type="text"
              maxlength="1000"
              aria-label="Feedback comment"
              placeholder="Add a comment (optional)"
              .value=${this.draft}
              @input=${(e: Event) => (this.draft = (e.target as HTMLInputElement).value)}
              @keydown=${(e: KeyboardEvent) => e.key === 'Enter' && this.sendComment()}
            />
            <button type="button" class="fb-btn" ?disabled=${this.busy} @click=${() => this.sendComment()}>Send</button>
          </div>`
        : ''}
    `;
  }
}
