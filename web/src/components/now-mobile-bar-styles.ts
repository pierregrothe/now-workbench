// web/src/components/now-mobile-bar-styles.ts
// Styles of <now-mobile-bar> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const mobileBarStyles = css`
  :host {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
    min-height: 52px;
    padding: env(safe-area-inset-top, 0px) 12px 0 calc(6px + env(safe-area-inset-left, 0px));
    background: var(--otto-canvas, #efece7);
    border-bottom: 1px solid var(--now-border-subtle, #ececeb);
    font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: var(--now-text-primary, #16181d);
  }

  button {
    appearance: none;
    border: none;
    background: transparent;
    color: inherit;
    width: 44px;
    height: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    cursor: pointer;
  }

  button:focus-visible {
    outline: 2px solid var(--now-color-focus, #2563eb);
    outline-offset: -2px;
  }

  button:active {
    background: rgba(22, 24, 29, 0.08);
  }

  h1 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
`;
