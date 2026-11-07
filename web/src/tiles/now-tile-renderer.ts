// web/src/tiles/now-tile-renderer.ts
// Dispatcher and renderer for the Generative UI tile catalog (ADR-010, ADR-025).
// Author: Pierre Grothe
// Date: 2026-10-31
//
// Entity tiles reuse the app's own elements (ADR-024), so a tile and its screen cannot drift
// apart. A missing value is shown as missing; nothing is filled in (ADR-013).

import { openArrowIcon } from '../icons.js';
import { LitElement, html, svg } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { InstanceData } from '../context/instance-model.js';
import { tileRendererStyles } from './now-tile-renderer-styles.js';
import { SERIES_COLORS, smoothPath } from './now-chart-geometry.js';
import type { ChartProps } from './now-chart-geometry.js';
import './now-chart-tile.js';
import './now-media-tile.js';
import '../components/now-instance-hero.js';
import '../components/now-diagnostics-card.js';

export interface UITileAction {
  id: string;
  label: string;
  variant?: 'primary' | 'secondary' | 'accent' | 'danger';
  /** For `ask` actions: the follow-up question sent to Otto when clicked. */
  prompt?: string;
}

export interface GenerativeUIResponse {
  summary: string;
  layout: '1-col' | '2-col' | '3-col' | 'auto';
  tiles: UITileSpec[];
}

export interface UITileSpec {
  id: string;
  type:
    | 'instance-kpi'
    | 'instance-card'
    | 'demo-bundle'
    | 'security-alert'
    | 'fluent-schema'
    | 'rich-text'
    | 'data-table'
    | 'media-player'
    | 'instance'
    | 'diagnostics'
    | 'kpis'
    | 'steps'
    | 'comparison'
    | 'callout'
    | 'chart';
  title?: string;
  props: Record<string, any>;
  /** Columns (of three) the tile spans; absent follows the reply's layout. */
  span?: 1 | 2 | 3 | null;
}

const STEP_MARK: Record<string, string> = { done: '\u2713', running: '\u2026', failed: '!', skipped: '-', todo: '' };
const PROBE_ACTIONS = new Set(['probe', 'probe_all']);
/** Kinds that need the whole row (screen cards, tables) unless the tile sets its own span. */
const FULL_WIDTH_TILES = new Set(['instance', 'diagnostics', 'data-table']);
/** Grid tracks (of six) a tile takes by default under each reply layout. */
const LAYOUT_TRACKS: Record<string, number> = { '1-col': 6, '2-col': 3, '3-col': 2 };

/** A KPI's trend: a 2px line with its latest point marked (ADR-027). */
function sparkline(values: number[]) {
  if (values.length < 2) return '';
  const w = 120;
  const h = 28;
  const lo = Math.min(...values);
  const span = Math.max(...values) - lo || 1;
  const pts = values.map((v, i) => [(i / (values.length - 1)) * (w - 6) + 3, h - 4 - ((v - lo) / span) * (h - 8)] as [number, number]);
  const [lx, ly] = pts[pts.length - 1];
  return html`<svg class="kpi-trend" width=${w} height=${h} role="img" aria-label="Trend, latest ${values[values.length - 1]}">
    ${svg`<path d=${smoothPath(pts)} fill="none" stroke=${SERIES_COLORS[0]} stroke-width="2" stroke-linejoin="round" stroke-linecap="round"></path>
      <circle cx=${lx} cy=${ly} r="3.5" fill=${SERIES_COLORS[0]} stroke="#fff" stroke-width="2"></circle>`}
  </svg>`;
}

@customElement('now-tile-renderer')
export class NowTileRenderer extends LitElement {
  @property({ type: Object }) tile!: UITileSpec;
  @property({ type: Boolean }) isProbing: boolean = false;
  /** The reply's layout; a tile without its own span follows it. */
  @property() layout = 'auto';

  static styles = tileRendererStyles;

  protected willUpdate(): void {
    this.style.setProperty('--tile-span', String(this.tracks()));
  }

  /** Width in grid tracks (of six): the tile's own span, else full for wide kinds, else the layout. */
  private tracks(): number {
    const span = this.tile?.span;
    if (span && span >= 1 && span <= 3) return span * 2;
    if (FULL_WIDTH_TILES.has(this.tile?.type)) return 6;
    return LAYOUT_TRACKS[this.layout] ?? 3;
  }

  private handleAction(actionId: string, props: Record<string, any>): void {
    this.dispatchEvent(
      new CustomEvent('tile-action', {
        detail: { tileId: this.tile?.id, actionId, props },
        bubbles: true,
        composed: true,
      })
    );
  }

  private statusBadgeVariant(statusText?: string): 'high' | 'medium' | 'critical' | 'low' {
    if (!statusText) return 'low';
    const s = statusText.toLowerCase();
    if (s.includes('online') || s.includes('reachable') || s.includes('healthy') || s.includes('active') || s.includes('authenticated')) return 'high';
    if (s.includes('unauthorized') || s.includes('error') || s.includes('failed') || s.includes('down')) return 'critical';
    if (s.includes('slow') || s.includes('degraded') || s.includes('warn') || s.includes('untested')) return 'medium';
    return 'low';
  }

  /** The action buttons every tile type shares. */
  private renderActions(p: Record<string, any>) {
    const actions: UITileAction[] = Array.isArray(p.actions) ? p.actions : [];
    if (!actions.length) return '';
    return html`<div class="gen-actions-row">
      ${actions.map((act) => {
        const probing = PROBE_ACTIONS.has(act.id) && this.isProbing;
        return html`<button
          type="button"
          class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
          ?disabled=${probing}
          @click=${() => this.handleAction(act.id, { ...p, ...act })}
        >
          ${probing ? 'Testing...' : act.label}
        </button>`;
      })}
    </div>`;
  }

  private renderStatus(status?: string) {
    return status ? html`<span class="ct-tag ${this.statusBadgeVariant(status)}">${status}</span>` : '';
  }

  render() {
    if (!this.tile) return '';
    const t = this.tile;
    const p = t.props || {};

    switch (t.type) {
      case 'instance': {
        return html`<now-instance-hero
            .instance=${p as InstanceData}
            ?testing=${this.isProbing}
            @edit-instance=${() => this.handleAction('manage', p)}
            @test-instance=${() => this.handleAction('probe', p)}
          ></now-instance-hero>
          ${this.renderActions(p)}`;
      }

      case 'diagnostics':
        return html`<now-diagnostics-card></now-diagnostics-card>${this.renderActions(p)}`;

      case 'kpis': {
        const items: any[] = Array.isArray(p.items) ? p.items : [];
        return html`
          <div class="gen-tile">
            ${t.title ? html`<h4 class="gen-rich-title">${t.title}</h4>` : ''}
            <div class="kpi-grid">
              ${items.map(
                (k) => html`<div class="kpi-item ${k.tone || 'neutral'}">
                  <span class="kpi-label">${k.label}</span>
                  <span class="kpi-value">${k.value}</span>
                  ${Array.isArray(k.trend) ? sparkline(k.trend) : ''}
                  ${k.hint ? html`<span class="kpi-hint">${k.hint}</span>` : ''}
                </div>`
              )}
            </div>
            ${this.renderActions(p)}
          </div>
        `;
      }

      case 'steps': {
        const items: any[] = Array.isArray(p.items) ? p.items : [];
        return html`
          <div class="gen-tile">
            ${t.title ? html`<h4 class="gen-rich-title">${t.title}</h4>` : ''}
            <ol class="steps-list">
              ${items.map(
                (s, i) => html`<li class="step ${s.status || 'todo'}">
                  <span class="step-dot" aria-label=${s.status || 'todo'}>${STEP_MARK[s.status] ?? ''}${!STEP_MARK[s.status] ? i + 1 : ''}</span>
                  <span><span class="step-label">${s.label}</span>${s.detail ? html`<div class="step-detail">${s.detail}</div>` : ''}</span>
                </li>`
              )}
            </ol>
            ${this.renderActions(p)}
          </div>
        `;
      }

      case 'comparison': {
        const cols: any[] = Array.isArray(p.columns) ? p.columns : [];
        return html`
          <div class="gen-tile">
            ${t.title ? html`<h4 class="gen-rich-title">${t.title}</h4>` : ''}
            <div class="compare-grid">
              ${cols.map(
                (c) => html`<div class="compare-col">
                  <h5>${c.heading}</h5>
                  <ul>${(c.points || []).map((pt: string) => html`<li>${pt}</li>`)}</ul>
                </div>`
              )}
            </div>
            ${this.renderActions(p)}
          </div>
        `;
      }

      case 'chart':
        return html`<div class="gen-tile">
          <now-chart-tile .props=${p as ChartProps} .heading=${t.title || ''}></now-chart-tile>
          ${this.renderActions(p)}
        </div>`;

      case 'callout':
        return html`
          <div class="gen-tile callout ${p.tone || 'info'}" role=${p.tone === 'danger' || p.tone === 'warning' ? 'alert' : 'note'}>
            ${t.title ? html`<h4 class="gen-rich-title">${t.title}</h4>` : ''}
            <div class="gen-rich-body">${p.body || ''}</div>
            ${this.renderActions(p)}
          </div>
        `;

      case 'instance-kpi':
        return html`
          <div class="gen-tile kpi">
            <div class="gen-kpi-top">
              <div class="gen-kpi-icon"><svg viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><path d="M22 6l-10 7L2 6"></path></svg></div>
              ${this.renderStatus(p.badge || p.status)}
            </div>
            <div class="gen-kpi-number">${p.count ?? '--'}</div>
            <div class="gen-kpi-label">${p.label || 'Managed Instances'}</div>
            <div class="gen-kpi-sub">${p.subtitle || ''}</div>
            ${this.renderActions(p)}
          </div>
        `;

      case 'instance-card':
        return html`
          <div class="gen-tile card">
            <div class="gen-card-header">
              <h4 class="gen-card-title">${p.name || 'ServiceNow Instance'}</h4>
              <span style="display:flex; align-items:center; gap:6px;">
                ${p.release ? html`<span class="ct-tag low">${p.release}</span>` : ''}
                <button type="button" class="open-btn" aria-label="Open details" title="Open details" @click=${() => this.handleAction('open_item', { ...p, kind: 'instance' })}>${openArrowIcon(14)}</button>
              </span>
            </div>
            <div class="gen-card-url">${p.url || ''}</div>
            <div class="gen-card-meta-row">
              <span>Status: ${this.renderStatus(p.probe_status || p.status) || '--'}</span>
              ${p.is_default ? html`<span class="ct-tag high">Primary Target</span>` : ''}
            </div>
            ${this.renderActions(p)}
          </div>
        `;

      case 'demo-bundle':
        return html`
          <div class="gen-tile card">
            <div class="gen-card-header"><h4 class="gen-card-title">${p.name || 'Demo Bundle'}</h4><span style="display:flex; align-items:center; gap:6px;">${p.release ? html`<span class="ct-tag low">${p.release}</span>` : ''}<button type="button" class="open-btn" aria-label="Open details" title="Open details" @click=${() => this.handleAction('open_item', { ...p, kind: 'bundle' })}>${openArrowIcon(14)}</button></span></div>
            ${p.industry ? html`<div style="font-size:12px; color:var(--now-text-secondary, #475467);">Industry: <strong>${p.industry}</strong></div>` : ''}
            <div class="gen-card-meta-row"><span>Tables: <strong>${p.tables_count ?? '--'}</strong></span><span>Records: <strong>${p.records_count ?? '--'}</strong></span></div>
            ${this.renderActions(p)}
          </div>
        `;

      case 'security-alert':
        return html`
          <div class="gen-tile alert-tile">
            <div class="gen-card-header"><h4 class="gen-alert-title">${t.title || p.agent_name || 'Security Review Required'}</h4>${p.severity ? html`<span class="ct-tag medium">${p.severity}</span>` : ''}</div>
            <p class="gen-alert-desc">${p.issue || ''}</p>
            ${p.remediation ? html`<div style="font-size:11.5px; color:#991b1b; font-weight:600;">Remediation: ${p.remediation}</div>` : ''}
            ${this.renderActions(p)}
          </div>
        `;

      case 'fluent-schema':
        return html`
          <div class="gen-tile card">
            <div class="gen-card-header"><h4 class="gen-card-title">${p.table_name || 'Fluent Table'}</h4>${p.file_path ? html`<span class="ct-tag low">${p.file_path}</span>` : ''}</div>
            <pre style="margin:4px 0; padding:8px 10px; background:#0f172a; color:#f8fafc; border-radius:6px; font-size:11px; overflow-x:auto; font-family:monospace;">${p.code || ''}</pre>
            ${this.renderActions(p)}
          </div>
        `;

      case 'data-table': {
        const columns: string[] = Array.isArray(p.columns) ? p.columns : [];
        const rows: any[][] = Array.isArray(p.rows) ? p.rows : [];
        return html`
          <div class="gen-tile table-tile">
            <h4 class="gen-table-title">${t.title || 'Data Table'}</h4>
            <div style="overflow-x: auto;">
              <table class="gen-data-table">
                <thead><tr>${columns.map((c) => html`<th>${c}</th>`)}</tr></thead>
                <tbody>${rows.map((r) => html`<tr>${r.map((cell) => html`<td>${cell}</td>`)}</tr>`)}</tbody>
              </table>
            </div>
            ${this.renderActions(p)}
          </div>
        `;
      }

      case 'media-player':
        return html`
          <now-media-tile
            .title=${t.title || 'Demonstration Media'}
            .url=${p.url || ''}
            .mediaType=${p.media_type || (p.url?.endsWith('.webm') ? 'video' : 'screenshot')}
            .label=${p.label || ''}
            .actions=${p.actions || []}
          ></now-media-tile>
        `;

      case 'rich-text':
      default:
        return html`
          <div class="gen-tile rich">
            <h4 class="gen-rich-title">${t.title || 'Summary'}</h4>
            <div class="gen-rich-body">${p.body || ''}</div>
            ${this.renderActions(p)}
          </div>
        `;
    }
  }
}
