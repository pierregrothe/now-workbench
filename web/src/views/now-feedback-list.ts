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

@customElement('now-feedback-list')
export class NowFeedbackList extends LitElement {
  static styles = [profileSettingsStyles, feedbackListStyles];

  /** Shows who rated each reply (the server decides what is listed). */
  @property({ type: Boolean }) admin = false;

  @state() private items: ReplyFeedback[] | null = null;
  @state() private error = '';

  connectedCallback(): void {
    super.connectedCallback();
    api<ReplyFeedback[]>('/api/feedback')
      .then((items) => (this.items = items))
      .catch((err: Error) => (this.error = `Could not load feedback: ${err.message}`));
  }

  private renderItem(f: ReplyFeedback) {
    return html`<li class="fb-item" data-testid="feedback-item">
      <div class="fb-meta">
        <span class="fb-rating ${f.rating}">${f.rating === 'up' ? 'Thumbs up' : 'Thumbs down'}</span>
        ${this.admin ? html`<span class="fb-who">${f.owner_email || '(before sign-in)'}</span>` : ''}
        <span>${new Date(f.updated_at).toLocaleString()}</span>
      </div>
      <p class="fb-reply">${f.reply}</p>
      ${f.comment ? html`<p class="fb-comment">"${f.comment}"</p>` : ''}
    </li>`;
  }

  render() {
    return html`<section class="card">
      <h2>Reply feedback</h2>
      <p class="desc">
        ${this.admin
          ? "Every rating people gave Otto's replies, newest first. Feedback stays in this workbench."
          : "The ratings you gave Otto's replies, newest first. Feedback stays in this workbench."}
      </p>
      ${this.items && this.items.length === 0 ? html`<p class="desc">No feedback yet.</p>` : ''}
      ${this.items ? html`<ul class="fb-list">${this.items.map((f) => this.renderItem(f))}</ul>` : ''}
      ${this.error ? html`<div class="msg error" role="alert">${this.error}</div>` : ''}
    </section>`;
  }
}
