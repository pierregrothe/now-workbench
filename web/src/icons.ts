// web/src/icons.ts
// Shared icons drawn to match the ServiceNow Otto interface (thin outlines, paper-plane send).
// Author: Pierre Grothe
// Date: 2026-11-06
import { html } from 'lit';
import type { TemplateResult } from 'lit';

/** Paper-plane send icon (a solid plane with a fold line), as on the Otto prompt box. */
export const sendIcon = (size = 16): TemplateResult => html`
  <svg viewBox="0 0 24 24" width=${size} height=${size} aria-hidden="true">
    <path fill="currentColor" d="M21.6 2.4 2.6 9.9a.7.7 0 0 0 0 1.3l7.3 3 3 7.3a.7.7 0 0 0 1.3 0z" />
    <path d="M9.9 14.2 21 3" fill="none" stroke="rgba(255,255,255,0.75)" stroke-width="1.2" stroke-linecap="round" />
  </svg>
`;

/** Otto's mark: a rounded diamond with a round hole. */
export const ottoGlyph = (size = 16, color = '#3ec24a'): TemplateResult => html`
  <svg viewBox="0 0 24 24" width=${size} height=${size} aria-hidden="true" style="flex:none;">
    <path
      fill=${color}
      fill-rule="evenodd"
      d="M12 1.6c.8 0 1.6.3 2.2.9l7.3 7.3c1.2 1.2 1.2 3.2 0 4.4l-7.3 7.3c-1.2 1.2-3.2 1.2-4.4 0l-7.3-7.3c-1.2-1.2-1.2-3.2 0-4.4l7.3-7.3c.6-.6 1.4-.9 2.2-.9zm0 6.6a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6z"
    />
  </svg>
`;

/** Thin up-right arrow used to open a tile. */
export const openArrowIcon = (size = 14): TemplateResult => html`
  <svg viewBox="0 0 16 16" width=${size} height=${size} aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 12 12 4M5.2 4H12v6.8" />
  </svg>
`;

/** Document with a binding edge and lines, the Artifact library icon. */
export const libraryIcon = (): TemplateResult => html`
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="5" y="3" width="14" height="18" rx="2.5"></rect>
    <path d="M9 3v18M12.5 8.5h3M12.5 12h3"></path>
  </svg>
`;

/**
 * Sidebar toggle in the Otto style: three left-aligned lines with a chevron that points
 * toward the direction the sidebar will move (left to collapse, right to expand).
 */
export const menuToggleIcon = (collapsed: boolean, size = 20): TemplateResult => html`
  <svg viewBox="0 0 20 20" width=${size} height=${size} aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 5h9M3 10h6M3 15h9" />
    ${collapsed ? html`<path d="m14 7 3 3-3 3" />` : html`<path d="m17 7-3 3 3 3" />`}
  </svg>
`;

/** Tap glyph (a pointing finger with a press ring), as on the Otto "Learn more" pill. */
export const tapIcon = (size = 14): TemplateResult => html`
  <svg viewBox="0 0 16 16" width=${size} height=${size} aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M6.5 8.5V3.25a1 1 0 0 1 2 0V7.5l2.6.45a1.6 1.6 0 0 1 1.3 1.8l-.4 2.6a1.8 1.8 0 0 1-1.8 1.65H8.4a2 2 0 0 1-1.6-.8L4.6 10.3a.95.95 0 0 1 1.4-1.25z" />
    <path d="M4.4 4.6a3.2 3.2 0 0 1 6.2 0" />
  </svg>
`;

/** Paperclip outline for attaching files to a question. */
export const attachIcon = (size = 18): TemplateResult => html`
  <svg viewBox="0 0 20 20" width=${size} height=${size} aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M15.5 9.2 9.6 15.1a3.6 3.6 0 0 1-5.1-5.1l6.3-6.3a2.4 2.4 0 0 1 3.4 3.4l-6.2 6.2a1.2 1.2 0 0 1-1.7-1.7l5.6-5.6" />
  </svg>
`;

/** Magnifier, the command palette entry for touch and mouse. */
export const searchIcon = (size = 18): TemplateResult => html`
  <svg viewBox="0 0 24 24" width=${size} height=${size} aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
    <circle cx="10.5" cy="10.5" r="6.5" />
    <path d="m15.5 15.5 4.5 4.5" />
  </svg>
`;

/** Thumb outline; `down` flips it for a thumbs down. Filled when the choice is made. */
export const thumbIcon = (down: boolean, filled = false, size = 16): TemplateResult => html`
  <svg viewBox="0 0 24 24" width=${size} height=${size} aria-hidden="true" fill=${filled ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style=${down ? 'transform: rotate(180deg);' : ''}>
    <path d="M7 10v11H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1z" />
    <path d="M7 10l4-7a2 2 0 0 1 2.9 2.2L13 9h5.6a2 2 0 0 1 2 2.4l-1.6 7.8a2 2 0 0 1-2 1.8H7" />
  </svg>
`;
