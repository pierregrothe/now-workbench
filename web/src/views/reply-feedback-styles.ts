// web/src/views/reply-feedback-styles.ts
// Styles of <now-reply-feedback> and <now-feedback-list> (ADR-024: CSS beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07
import { css } from 'lit';

export const replyFeedbackStyles = css`
  :host {
    display: block;
    margin-top: 8px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
  }
  .fb-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 30px;
    padding: 4px 8px;
    border: 1px solid transparent;
    border-radius: 8px;
    background: transparent;
    color: var(--now-text-secondary, #4b5563);
    font: inherit;
    font-size: 12.5px;
    cursor: pointer;
  }
  .fb-btn:hover,
  .fb-btn:focus-visible {
    background: #f4f3f0;
    color: var(--now-text-primary, #16181d);
  }
  .fb-btn[aria-pressed='true'] {
    color: #1f7a33;
    background: #e8f5ea;
    border-color: #bfe3c5;
  }
  .fb-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .comment {
    display: flex;
    gap: 6px;
    margin-top: 6px;
    width: 100%;
    max-width: 520px;
  }
  .comment input {
    flex: 1;
    min-width: 0;
    padding: 6px 10px;
    border: 1px solid #d9d6cf;
    border-radius: 8px;
    font: inherit;
    font-size: 13px;
  }
  .note {
    font-size: 12px;
    color: var(--now-text-secondary, #4b5563);
    margin-left: 4px;
  }
  .note.error {
    color: #b42318;
  }
  @media (max-width: 768px), (max-height: 500px) {
    .fb-btn {
      min-height: 40px;
      min-width: 40px;
      justify-content: center;
    }
    .comment input {
      font-size: 16px;
    }
  }
`;

export const feedbackListStyles = css`
  .fb-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .fb-item {
    border: 1px solid #ece9e3;
    border-radius: 12px;
    padding: 10px 12px;
  }
  .fb-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 12px;
    color: var(--now-text-secondary, #4b5563);
  }
  .fb-rating {
    font-weight: 600;
  }
  .fb-rating.up {
    color: #1f7a33;
  }
  .fb-rating.down {
    color: #b42318;
  }
  .fb-reply {
    margin: 6px 0 0;
    font-size: 13px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    max-height: 7.5em;
    overflow: hidden;
  }
  .fb-comment {
    margin: 6px 0 0;
    font-size: 13px;
    font-style: italic;
  }
  @media (max-width: 768px), (max-height: 500px) {
    .fb-item {
      padding: 10px;
    }
  }
`;
