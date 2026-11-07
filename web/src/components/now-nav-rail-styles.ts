// web/src/components/now-nav-rail-styles.ts
// Styles of <now-nav-rail> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const navRailStyles = css`
    :host {
      display: block;
      position: relative;
      height: 100%;
      background-color: var(--otto-canvas, #efece7);
      border-right: 1px solid var(--now-border-subtle, #ececeb);
      user-select: none;
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: var(--now-text-primary, #16181d);
      flex-shrink: 0;
      transition: width 0.18s ease;
    }

    .rail-container {
      width: 248px;
      height: 100%;
      display: flex;
      flex-direction: column;
      padding: 12px 12px 18px 12px;
      box-sizing: border-box;
      overflow-y: auto;
      transition: width 0.18s ease;
    }

    .rail-container.resizing {
      transition: none;
    }

    /* Drag handle on the right edge, like the EmployeeWorks sidebar. */
    .resize-handle {
      position: absolute;
      top: 0;
      right: -3px;
      width: 6px;
      height: 100%;
      cursor: col-resize;
      z-index: 5;
    }

    .resize-handle:hover,
    .resize-handle:focus-visible,
    .resize-handle.active {
      background: rgba(22, 24, 29, 0.12);
      outline: none;
    }

    .rail-container.collapsed {
      width: 64px;
      padding: 12px 8px;
      align-items: center;
    }

    .top-chrome {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      min-height: 28px;
      margin-bottom: 4px;
      width: 100%;
    }

    .rail-container.collapsed .top-chrome {
      justify-content: center;
    }

    .collapse-btn {
      position: relative;
      appearance: none;
      border: none;
      background: transparent;
      color: #4a4e58;
      width: 28px;
      height: 28px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }

    .collapse-btn:hover {
      background: var(--otto-canvas-active, #e3dfd8);
      color: #16181d;
    }

    .collapse-btn svg {
      width: 20px;
      height: 20px;
    }

    .brand-header {
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 6px 8px 18px 8px;
      cursor: pointer;
    }

    .rail-container.collapsed .brand-header {
      padding: 6px 0 18px 0;
      justify-content: center;
    }

    .sn-glyph {
      width: 22px;
      height: 22px;
      flex-shrink: 0;
    }

    .brand-title {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--now-text-primary, #0b0f19);
      line-height: 1.2;
      white-space: nowrap;
    }

    .primary-list {
      display: flex;
      flex-direction: column;
      gap: 2px;
      margin-bottom: 18px;
      width: 100%;
    }

    .nav-row {
      appearance: none;
      border: none;
      background: transparent;
      width: 100%;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 999px;
      font-size: 13.5px;
      font-weight: 400;
      color: var(--now-text-secondary, #2c2e33);
      cursor: pointer;
      text-align: left;
      transition: background-color 0.12s ease, color 0.12s ease;
      font-family: inherit;
    }

    .rail-container.collapsed .nav-row {
      justify-content: center;
      padding: 9px;
    }

    .nav-row:hover {
      background-color: var(--otto-canvas-active, #e3dfd8);
      color: var(--now-text-primary, #0b0f19);
    }

    .nav-row.active {
      background-color: var(--otto-canvas-active, #e3dfd8);
      color: var(--now-text-primary, #0b0f19);
      font-weight: 600;
    }

    .nav-row.active .nav-icon {
      color: var(--now-color-brand-green, #032d42);
    }

    .nav-icon {
      width: 17px;
      height: 17px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: currentColor;
    }

    .nav-icon svg {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .section-block {
      display: flex;
      flex-direction: column;
      margin-bottom: 18px;
      width: 100%;
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 4px 10px 6px 10px;
    }

    .section-label {
      font-size: 12px;
      font-weight: 500;
      color: #686b73;
      letter-spacing: -0.005em;
    }

    .compose-btn {
      position: relative;
      appearance: none;
      border: 1px solid #d4d5d2;
      background: #ffffff;
      color: #2c2e33;
      width: 24px;
      height: 24px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background 0.12s ease, border-color 0.12s ease;
    }

    .compose-btn:hover {
      background: #f3f3f1;
      border-color: #b8b9b4;
    }

    .compose-btn svg {
      width: 13px;
      height: 13px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .thread-title {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
    }

    .session-icon {
      width: 15px;
      height: 15px;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--now-text-muted, #64748b);
    }

    .session-icon svg {
      width: 14px;
      height: 14px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .thread-row-wrap {
      display: flex;
      align-items: center;
      gap: 2px;
      width: 100%;
      border-radius: 10px;
      padding-right: 4px;
      transition: background-color 0.12s ease;
    }

    .thread-row-wrap:hover {
      background-color: var(--now-bg-surface-1, #f1f1ef);
    }

    .thread-row-wrap.active {
      background-color: var(--now-bg-surface-1, #ececea);
    }

    .thread-row-wrap .nav-row {
      flex: 1;
      min-width: 0;
      padding: 7px 8px;
      background: transparent !important;
    }

    .thread-count-badge {
      font-size: 10px;
      font-weight: 600;
      color: var(--now-text-muted, #64748b);
      background: var(--now-bg-surface-2, #e2e8f0);
      padding: 1px 5px;
      border-radius: 999px;
      flex-shrink: 0;
    }

    .thread-actions {
      display: flex;
      align-items: center;
      gap: 2px;
      flex-shrink: 0;
      opacity: 0.75;
      transition: opacity 0.12s ease;
    }

    .thread-row-wrap:hover .thread-actions {
      opacity: 1;
    }

    .thread-action-btn {
      appearance: none;
      border: none;
      background: transparent;
      color: var(--now-text-muted, #64748b);
      width: 22px;
      height: 22px;
      border-radius: 5px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      padding: 0;
      transition: all 0.12s ease;
    }

    .thread-action-btn:hover {
      background: rgba(15, 23, 42, 0.08);
      color: var(--now-text-primary, #0f172a);
    }

    .thread-action-btn.delete:hover {
      background: #fee2e2;
      color: #dc2626;
    }

    .thread-action-btn svg {
      width: 13px;
      height: 13px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .archived-toggle-btn {
      appearance: none;
      border: none;
      background: transparent;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-text-muted, #64748b);
      padding: 8px 10px 4px 10px;
      cursor: pointer;
      font-family: inherit;
    }

    .archived-toggle-btn:hover {
      color: var(--now-text-primary, #0f172a);
    }

    .spacer {
      flex: 1;
    }

    .bottom-utilities {
      padding-top: 8px;
      border-top: 1px solid #ececeb;
      display: flex;
      flex-direction: column;
      gap: 2px;
      width: 100%;
    }

    .user-profile-row {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid var(--now-border-subtle, #ececea);
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
    }

    .user-profile-row.collapsed {
      justify-content: center;
      padding-top: 8px;
    }

    .user-avatar-pill {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      font-size: 11px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .user-info-text {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .user-name {
      font-size: 12.5px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-role {
      font-size: 11px;
      color: var(--now-text-muted, #64748b);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-more-btn {
      appearance: none;
      border: none;
      background: transparent;
      color: var(--now-text-muted, #64748b);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 4px;
      border-radius: 4px;
    }

    .user-more-btn svg {
      width: 14px;
      height: 14px;
      fill: currentColor;
    }
  `;
