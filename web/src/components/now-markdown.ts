// web/src/components/now-markdown.ts
// Renders Otto's text as HTML: a safe markdown subset built as Lit templates (ADR-028).
// Author: Pierre Grothe
// Date: 2026-11-07
//
// Otto writes light markdown (Claude's natural format). Raw HTML from the model is never
// injected: every piece of text is interpolated by Lit, so a tool result or a record that
// carries markup or script shows as text. Supported: paragraphs, line breaks, headings,
// bullet and numbered lists, fenced code, **bold**, *italics*, `code` and http(s)/mailto links.

import { LitElement, html, nothing, type TemplateResult } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { markdownStyles } from './now-markdown-styles.js';

type Inline = TemplateResult | string;

const INLINE = /(\*\*[^*\n]+?\*\*|__[^_\n]+?__|`[^`\n]+`|\[[^\]\n]+\]\([^)\s]+\)|\*[^*\s][^*\n]*?\*|_[^_\s][^_\n]*?_)/g;
const SAFE_URL = /^(https?:|mailto:)/i;

/** Inline formatting of one line; nested bold/italic/link text is formatted too. */
export function inline(text: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    const tok = m[0];
    if (m.index > last) out.push(text.slice(last, m.index));
    last = m.index + tok.length;
    if (tok.startsWith('**') || tok.startsWith('__')) out.push(html`<strong>${inline(tok.slice(2, -2))}</strong>`);
    else if (tok.startsWith('`')) out.push(html`<code>${tok.slice(1, -1)}</code>`);
    else if (tok.startsWith('[')) {
      const [, label, url] = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(tok) ?? [];
      out.push(SAFE_URL.test(url ?? '') ? html`<a href=${url} target="_blank" rel="noopener noreferrer">${inline(label)}</a>` : tok);
    } else out.push(html`<em>${inline(tok.slice(1, -1))}</em>`);
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const withBreaks = (lines: string[]): Inline[] => lines.flatMap((l, i) => (i ? [html`<br />`, ...inline(l)] : inline(l)));

/** Block structure: fenced code, headings, lists and paragraphs. */
export function blocks(text: string): TemplateResult[] {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const out: TemplateResult[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }
    if (line.trimStart().startsWith('```')) {
      const body: string[] = [];
      for (i++; i < lines.length && !lines[i].trimStart().startsWith('```'); i++) body.push(lines[i]);
      i++;
      out.push(html`<pre><code>${body.join('\n')}</code></pre>`);
      continue;
    }
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      out.push(heading[1].length <= 2 ? html`<h4>${inline(heading[2])}</h4>` : html`<h5>${inline(heading[2])}</h5>`);
      i++;
      continue;
    }
    const listKind = /^\s*[-*+]\s+/.test(line) ? 'ul' : /^\s*\d+[.)]\s+/.test(line) ? 'ol' : '';
    if (listKind) {
      const marker = listKind === 'ul' ? /^\s*[-*+]\s+/ : /^\s*\d+[.)]\s+/;
      const items: string[] = [];
      for (; i < lines.length && marker.test(lines[i]); i++) items.push(lines[i].replace(marker, ''));
      const lis = items.map((it) => html`<li>${inline(it)}</li>`);
      out.push(listKind === 'ul' ? html`<ul>${lis}</ul>` : html`<ol>${lis}</ol>`);
      continue;
    }
    const para: string[] = [];
    for (; i < lines.length && lines[i].trim() && !/^(#{1,6}\s|```|\s*([-*+]|\d+[.)])\s)/.test(lines[i]); i++) para.push(lines[i]);
    out.push(html`<p>${withBreaks(para)}</p>`);
  }
  return out;
}

@customElement('now-markdown')
export class NowMarkdown extends LitElement {
  static styles = markdownStyles;

  @property() text = '';

  render() {
    return this.text ? blocks(this.text) : nothing;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-markdown': NowMarkdown;
  }
}
