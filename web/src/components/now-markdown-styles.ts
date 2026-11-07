// web/src/components/now-markdown-styles.ts
// Styles of <now-markdown> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const markdownStyles = css`
  :host {
    display: block;
    white-space: normal;
    line-height: 1.55;
    overflow-wrap: anywhere;
  }
  p,
  ul,
  ol,
  pre,
  h4,
  h5 {
    margin: 0 0 8px;
  }
  :is(p, ul, ol, pre, h4, h5):last-child {
    margin-bottom: 0;
  }
  h4 {
    font-size: 14px;
  }
  h5 {
    font-size: 13px;
  }
  ul,
  ol {
    padding-left: 20px;
  }
  li + li {
    margin-top: 2px;
  }
  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.92em;
    background: rgba(11, 11, 11, 0.06);
    border-radius: 4px;
    padding: 1px 4px;
  }
  pre {
    background: #0f172a;
    color: #f8fafc;
    border-radius: 8px;
    padding: 10px 12px;
    overflow-x: auto;
  }
  pre code {
    background: none;
    padding: 0;
    color: inherit;
  }
  a {
    color: var(--now-link, #1c5cab);
  }
`;
