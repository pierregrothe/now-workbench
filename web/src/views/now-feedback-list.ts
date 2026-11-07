// web/src/views/now-feedback-list.ts
// Ratings of Otto's replies: administrators see everyone's, consultants their own.
// Author: Pierre Grothe
// Date: 2026-11-07
import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { profileSettingsStyles } from './profile-settings-styles.js';
import { feedbackListStyles } from './reply-feedback-styles.js';
import { api } from './sharing-api.js';
import type { ReplyFeedback } from './now-reply-feedback.js';

/** Replies longer than this are clipped until expanded. */
const CLIP_AT = 400;

@customElement('now-feedback-list')
export class NowFeedbackList extends LitElement {
  static styles = [profileSettingsStyles, feedbackListStyles];

  /** Shows who rated each reply (the server decides what is listed). */
  @property({ type: Boolean }) admin = false;

  @state() private items: ReplyFeedback[] | null = null;
  @state() private error = '';
  /** Replies shown in full (the rest are clipped to a few lines). */
  @state() private expanded = new Set<string>();

  connectedCallback(): void {
    super.connectedCallback();
    api<ReplyFeedback[]>('/api/feedback')
      .then((items) => (this.items = items))
      .catch((err: Error) => (this.error = `Could not load feedback: ${err.message}`));
  }

  private toggle(id: string): void {
    const next = new Set(this.expanded);
    if (!next.delete(id)) next.add(id);
    this.expanded = next;
  }

  private renderItem(f: ReplyFeedback) {
    const long = f.reply.length > CLIP_AT || f.reply.split('\n').length > 5;
    const open = this.expanded.has(f.message_id);
    return html`<li class="fb-item" data-testid="feedback-item">
      <div class="fb-meta">
        <span class="fb-rating ${f.rating}">${f.rating === 'up' ? 'Thumbs up' : 'Thumbs down'}</span>
        ${this.admin ? html`<span class="fb-who">${f.owner_email || '(before sign-in)'}</span>` : ''}
        <span>${new Date(f.updated_at).toLocaleString()}</span>
      </div>
      <p class="fb-reply ${long && !open ? 'clipped' : ''}" id="reply-${f.message_id}">${f.reply}</p>
      ${long
        ? html`<button type="button" class="fb-more" aria-expanded=${open ? 'true' : 'false'} aria-controls="reply-${f.message_id}" @click=${() => this.toggle(f.message_id)}>
            ${open ? 'Show less' : 'Show the whole reply'}
          </button>`
        : ''}
      ${f.comment ? html`<p class="fb-comment">"${f.comment}"</p>` : ''}
    </li>`;
  }

  render() {
    return html`<section class="card">
      <h2>Reply feedback</h2>
      <p class="desc">
        ${this.admin
          ? "The newest 200 ratings people gave Otto's replies. Feedback stays in this workbench."
          : "The newest 200 ratings you gave Otto's replies. Feedback stays in this workbench."}
      </p>
      ${this.items && this.items.length === 0 ? html`<p class="desc">No feedback yet.</p>` : ''}
      ${this.items ? html`<ul class="fb-list">${this.items.map((f) => this.renderItem(f))}</ul>` : ''}
      ${this.error ? html`<div class="msg error" role="alert">${this.error}</div>` : ''}
    </section>`;
  }
}
