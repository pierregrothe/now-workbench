// web/src/components/now-workbench-shell-styles.ts
// Styles of <now-workbench-shell> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const workbenchShellStyles = css`
    :host {
      display: flex;
      height: 100vh;
      height: 100dvh;
      width: 100vw;
      overflow: hidden;
      background-color: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .content-area {
      flex: 1;
      min-width: 0;
      height: 100%;
      overflow: hidden;
      position: relative;
      display: flex;
      flex-direction: column;
      background: var(--now-bg-canvas, #ffffff);
    }

    .drawer-scrim {
      position: fixed;
      inset: 0;
      z-index: 999;
      background: rgba(22, 24, 29, 0.4);
    }

    .thread-error-banner {
      padding: 8px 16px;
      background: #fdecea;
      color: #b3261e;
      font-size: 13px;
    }

    .active-view-stage {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    /* Docked Bottom Chat Bar (shown whenever activeTab !== 'home') */
    .bottom-chat-dock {
      flex-shrink: 0;
      padding: 10px 36px 14px 36px;
      background: var(--otto-canvas, #efece7);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      z-index: 20;
    }

    .intent-route-caption {
      width: 100%;
      max-width: 768px;
      font-size: 11.5px;
      color: var(--now-text-secondary, #6b7280);
      text-align: center;
    }

    .bottom-prompt-box {
      width: calc(100% - 16px);
      max-width: 752px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #ffffff;
      border-radius: 32px;
      padding: 18px 14px 12px 24px;
      margin: 8px 0 4px;
      box-sizing: border-box;
      box-shadow:
        0 0 0 8px #f4f3f0,
        0 0 8px 8px rgba(0, 0, 0, 0.05),
        0 20px 25px 3px rgba(0, 0, 0, 0.1);
    }

    .bottom-prompt-box input {
      border: none;
      background: transparent;
      font-family: inherit;
      font-size: 16px;
      line-height: 24px;
      color: var(--now-text-primary, #16181d);
      outline: none;
    }

    .bottom-prompt-foot {
      display: flex;
      justify-content: flex-end;
    }

    .bottom-send-btn {
      position: relative;
      appearance: none;
      border: none;
      background: #c9f0c1;
      color: #4b5f4b;
      width: 36px;
      height: 36px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      cursor: pointer;
      transition: background 0.12s ease, transform 0.1s ease;
    }

    .bottom-send-btn:hover {
      opacity: 0.9;
      transform: scale(1.05);
    }

    .bottom-send-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }
  
    /* Phones (ADR-030): a slimmer prompt dock that clears the home indicator. */
    @media (max-width: 768px), (max-height: 500px) {
      .bottom-chat-dock {
        padding: 6px 10px calc(8px + env(safe-area-inset-bottom, 0px));
      }

      .bottom-prompt-box {
        width: 100%;
        flex-direction: row;
        align-items: center;
        border-radius: 24px;
        padding: 6px 6px 6px 16px;
        margin: 4px 0 2px;
        box-shadow: 0 0 0 4px #f4f3f0, 0 8px 16px rgba(0, 0, 0, 0.08);
      }

      .bottom-prompt-box input {
        flex: 1;
        min-width: 0;
      }

      .bottom-send-btn {
        width: 40px;
        height: 40px;
        flex-shrink: 0;
      }

      .intent-route-caption {
        display: none;
      }
    }
`;
