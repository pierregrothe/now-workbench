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

/** The owner's stored rating, as the thread history carries it. */
export interface ReplyRating {
  rating: Rating;
  comment: string;
}

/** A stored rating as the API returns it (also listed in Settings). */
export interface ReplyFeedback extends ReplyRating {
  message_id: string;
  thread_id: string;
  owner_email: string;
  reply: string;
  created_at: string;
  updated_at: string;
}

/** The first words of a reply, so each row's buttons have their own accessible name. */
export function replyExcerpt(text: string, max = 40): string {
  const flat = text.replace(/\s+/g, ' ').trim();
  return flat.length > max ? `${flat.slice(0, max).trimEnd()}...` : flat;
}

/**
 * Rates one stored reply. Rating again replaces the stored rating and keeps its comment
 * (the thumbs send no comment); Send replaces the comment. Feedback stays in the workbench;
 * Get help opens the help guide through the `open-welcome` event.
 */
@customElement('now-reply-feedback')
export class NowReplyFeedback extends LitElement {
  static styles = replyFeedbackStyles;

  @property({ attribute: false }) messageId = '';
  /** The stored rating and comment from the thread history. */
  @property({ attribute: false }) feedback: ReplyRating | null = null;
  /** A short excerpt of the reply, added to the buttons' names. */
  @property({ attribute: false }) excerpt = '';

  @state() private current: Rating | null = null;
  @state() private draft = '';
  @state() private commentOpen = false;
  @state() private busy = false;
  @state() private status = '';
  @state() private error = '';

  willUpdate(changed: PropertyValues<this>): void {
    if (changed.has('feedback')) {
      this.current = this.feedback?.rating ?? null;
      this.draft = this.feedback?.comment ?? '';
    }
  }

  /** Save, then open the comment box; a failure leaves the choice and the box as they were. */
  private async save(rating: Rating, comment: string | null): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.error = '';
    try {
      const saved = await api<ReplyFeedback>(`/api/feedback/${encodeURIComponent(this.messageId)}`, {
        method: 'PUT',
        body: JSON.stringify({ rating, comment }),
      });
      this.current = saved.rating;
      this.draft = saved.comment;
      this.status = comment === null ? 'Thanks for the feedback.' : 'Thanks, comment saved.';
      this.commentOpen = comment === null;
    } catch (err) {
      this.status = '';
      this.error = `Could not save: ${(err as Error).message}`;
    } finally {
      this.busy = false;
    }
  }

  private thumb(rating: Rating, label: string) {
    const chosen = this.current === rating;
    const name = this.excerpt ? `${label}: "${this.excerpt}"` : label;
    return html`<button
      type="button"
      class="fb-btn ${rating}"
      aria-label=${name}
      title=${label}
      aria-pressed=${chosen ? 'true' : 'false'}
      aria-busy=${this.busy ? 'true' : 'false'}
      @click=${() => void this.save(rating, null)}
    >
      ${thumbIcon(rating === 'down', chosen)}
    </button>`;
  }

  private sendComment(): void {
    if (this.current) void this.save(this.current, this.draft.trim());
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
        <span class="note" role="status">${this.status}</span>
        ${this.error ? html`<span class="note error" role="alert">${this.error}</span>` : ''}
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
            <button type="button" class="fb-btn" aria-busy=${this.busy ? 'true' : 'false'} @click=${() => this.sendComment()}>Send</button>
          </div>`
        : ''}
    `;
  }
}
