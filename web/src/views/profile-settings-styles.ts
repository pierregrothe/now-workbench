// web/src/views/profile-settings-styles.ts
// Styles for the Profile settings section.
// Author: Pierre Grothe
// Date: 2026-11-06
import { css } from 'lit';

export const profileSettingsStyles = css`
  :host {
    display: flex;
    flex-direction: column;
    gap: 18px;
    font-family: inherit;
    color: var(--now-text-primary, #16181d);
  }
  .card {
    background: #ffffff;
    border-radius: 16px;
    padding: 22px 24px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }
  h2 {
    margin: 0 0 4px;
    font-size: 16px;
    font-weight: 600;
  }
  .desc {
    margin: 0 0 16px;
    font-size: 12.5px;
    color: var(--now-text-secondary, #4b5563);
  }
  .avatar-row {
    display: flex;
    align-items: center;
    gap: 20px;
    margin-bottom: 16px;
  }
  .avatar-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, 48px);
    gap: 10px;
  }
  .preset {
    width: 48px;
    height: 48px;
    padding: 0;
    border: 2px solid transparent;
    border-radius: 50%;
    overflow: hidden;
    cursor: pointer;
    background: none;
  }
  .preset img {
    width: 100%;
    height: 100%;
    display: block;
  }
  .preset[aria-pressed='true'] {
    border-color: #1a1a1a;
  }
  .fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
    gap: 14px;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12.5px;
    font-weight: 500;
  }
  .field.wide {
    grid-column: 1 / -1;
  }
  input[type='text'],
  input[type='email'],
  input[type='password'],
  input[type='number'] {
    border: 1px solid rgba(0, 0, 0, 0.14);
    border-radius: 10px;
    padding: 9px 12px;
    font: inherit;
    font-size: 13.5px;
    background: #ffffff;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 14px;
    flex-wrap: wrap;
  }
  .btn {
    border: none;
    border-radius: 999px;
    padding: 8px 16px;
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    background: #e3dfd8;
    color: #16181d;
  }
  .btn.primary {
    background: #1a4d63;
    color: #ffffff;
  }
  .btn:disabled {
    opacity: 0.55;
    cursor: default;
  }
  .chip {
    font-size: 12px;
    font-weight: 600;
    border-radius: 999px;
    padding: 3px 10px;
  }
  .chip.ok {
    background: #dcfce7;
    color: #166534;
  }
  .chip.todo {
    background: #fef3c7;
    color: #92400e;
  }
  .code-input {
    letter-spacing: 0.18em;
    text-transform: uppercase;
    width: 190px;
  }
  .msg {
    font-size: 12.5px;
    margin-top: 10px;
  }
  .msg.error {
    color: #b91c1c;
  }
  .msg.ok {
    color: #166534;
  }
  .hint {
    font-size: 12px;
    color: var(--now-text-secondary, #6b7280);
  }
  .usage-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .usage-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 12px;
    padding-top: 10px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);
  }
  .usage-who {
    font-weight: 600;
    font-size: 13px;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .usage-row input[type='number'] {
    width: 9.5em;
  }
`;
