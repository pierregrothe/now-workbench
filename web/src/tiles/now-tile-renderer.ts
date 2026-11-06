// web/src/tiles/now-tile-renderer.ts
// Dispatcher and renderer for Generative UI Tile Catalog (ADR-010).
// Author: Pierre Grothe
// Date: 2026-10-31

import { openArrowIcon } from '../icons.js';
import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './now-media-tile.js';

export interface UITileAction {
  id: string;
  label: string;
  variant?: 'primary' | 'secondary' | 'accent' | 'danger';
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
    | 'media-player';
  title?: string;
  props: Record<string, any>;
}

@customElement('now-tile-renderer')
export class NowTileRenderer extends LitElement {
  @property({ type: Object }) tile!: UITileSpec;
  @property({ type: Boolean }) isProbing: boolean = false;

  static styles = css`
    :host { display: block; font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .gen-tile { background: var(--now-bg-surface-0, #ffffff); border: 1px solid rgba(0,0,0,0.05); border-radius: 16px; padding: 18px 20px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); transition: all 0.15s ease; text-align: left; }
    .gen-tile:hover { box-shadow: 0 4px 18px rgba(0,0,0,0.06); }
    .open-btn { border: none; background: transparent; cursor: pointer; font-size: 15px; line-height: 1; color: var(--now-text-secondary, #4b5563); padding: 2px 4px; border-radius: 6px; }
    .open-btn:hover { background: rgba(0,0,0,0.06); }
    .gen-tile.kpi { }
    .gen-kpi-top { display: flex; align-items: center; justify-content: space-between; }
    .gen-kpi-icon { width: 32px; height: 32px; border-radius: 8px; background: #dcfce7; color: #15803d; display: flex; align-items: center; justify-content: center; }
    .gen-kpi-icon svg { width: 17px; height: 17px; stroke: currentColor; stroke-width: 2; fill: none; }
    .gen-kpi-number { font-size: 34px; font-weight: 800; color: var(--now-text-primary, #0f172a); line-height: 1; letter-spacing: -0.02em; margin-top: 4px; }
    .gen-kpi-label { font-size: 13.5px; font-weight: 700; color: var(--now-text-primary, #0f172a); }
    .gen-kpi-sub { font-size: 11.5px; color: var(--now-text-secondary, #475467); }
    .gen-card-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .gen-card-title { font-size: 14.5px; font-weight: 700; color: var(--now-text-primary, #0f172a); margin: 0; display: flex; align-items: center; gap: 6px; }
    .gen-card-url { font-size: 11.5px; font-family: monospace; color: var(--now-text-secondary, #475467); background: var(--now-bg-surface-1, #f8fafc); padding: 5px 10px; border-radius: 6px; border: 1px solid var(--now-border-subtle, #f1f5f9); word-break: break-all; }
    .gen-card-meta-row { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--now-text-secondary, #475467); }
    .gen-tile.alert-tile { background: #fef2f2; border-color: #fee2e2; border-left: 4px solid #dc2626; }
    .gen-alert-title { font-size: 14px; font-weight: 700; color: #991b1b; margin: 0; }
    .gen-alert-desc { font-size: 12.5px; color: #7f1d1d; line-height: 1.45; margin: 0; }
    .gen-tile.rich { background: var(--now-bg-surface-0, #ffffff); }
    .gen-rich-title { font-size: 13.5px; font-weight: 700; color: var(--now-text-primary, #0f172a); margin: 0; }
    .gen-rich-body { font-size: 12.5px; color: var(--now-text-secondary, #475467); line-height: 1.5; white-space: pre-wrap; }
    .gen-tile.table-tile { background: var(--now-bg-surface-0, #ffffff); border-left: 4px solid #2563eb; overflow-x: auto; }
    .gen-table-title { font-size: 13.5px; font-weight: 700; color: var(--now-text-primary, #0f172a); margin: 0; }
    .gen-data-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 4px; }
    .gen-data-table th { text-align: left; padding: 6px 10px; background: var(--now-bg-surface-1, #f8fafc); color: #64748b; font-weight: 600; border-bottom: 1px solid #e2e8f0; font-size: 11px; text-transform: uppercase; }
    .gen-data-table td { padding: 6px 10px; border-bottom: 1px solid #f1f5f9; color: #0f172a; }
    .gen-actions-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
    .ct-action-btn { padding: 5px 12px; border-radius: 6px; font-size: 11.5px; font-weight: 600; border: 1px solid #cbd5e1; background: #ffffff; color: #334155; cursor: pointer; transition: all 0.15s ease; }
    .ct-action-btn:hover { background: #f1f5f9; border-color: #94a3b8; }
    .ct-action-btn.primary { background: var(--now-color-primary, #032d42); color: #ffffff; border-color: var(--now-color-primary, #032d42); }
    .ct-tag { display: inline-flex; align-items: center; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 600; text-transform: uppercase; }
    .ct-tag.high { background: #dcfce7; color: #15803d; }
    .ct-tag.critical { background: #fee2e2; color: #b91c1c; }
    .ct-tag.medium { background: #fef3c7; color: #b45309; }
    .ct-tag.low { background: #f1f5f9; color: #475569; }
  `;

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
    if (s.includes('online') || s.includes('reachable') || s.includes('healthy') || s.includes('active')) return 'high';
    if (s.includes('unauthorized') || s.includes('error') || s.includes('failed') || s.includes('down')) return 'critical';
    if (s.includes('slow') || s.includes('degraded') || s.includes('warn') || s.includes('untested')) return 'medium';
    return 'low';
  }

  render() {
    if (!this.tile) return '';
    const t = this.tile;
    const p = t.props || {};

    switch (t.type) {
      case 'instance-kpi': {
        const statusLabel = p.badge || p.status || 'Active';
        const badgeVariant = this.statusBadgeVariant(statusLabel);
        return html`
          <div class="gen-tile kpi">
            <div class="gen-kpi-top">
              <div class="gen-kpi-icon"><svg viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><path d="M22 6l-10 7L2 6"></path></svg></div>
              <span class="ct-tag ${badgeVariant}">${statusLabel}</span>
            </div>
            <div class="gen-kpi-number">${p.count ?? 1}</div>
            <div class="gen-kpi-label">${p.label || 'Managed Instances'}</div>
            <div class="gen-kpi-sub">${p.subtitle || ''}</div>
            ${p.actions && p.actions.length ? html`
              <div class="gen-actions-row">
                ${p.actions.map((act: any) => html`
                  <button type="button" class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}" ?disabled=${(act.id === 'probe' || act.id === 'probe_all') && this.isProbing} @click=${() => this.handleAction(act.id, { ...p, ...act })}>
                    ${(act.id === 'probe' || act.id === 'probe_all') && this.isProbing ? 'Testing...' : act.label}
                  </button>
                `)}
              </div>
            ` : ''}
          </div>
        `;
      }

      case 'instance-card': {
        const statusText = p.probe_status || p.status || 'Active';
        const badgeVariant = this.statusBadgeVariant(statusText);
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
              <span>Status: <span class="ct-tag ${badgeVariant}">${statusText}</span></span>
              ${p.is_default ? html`<span class="ct-tag high">Primary Target</span>` : ''}
            </div>
            ${p.actions && p.actions.length ? html`
              <div class="gen-actions-row">
                ${p.actions.map((act: any) => html`
                  <button type="button" class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}" ?disabled=${(act.id === 'probe' || act.id === 'probe_all') && this.isProbing} @click=${() => this.handleAction(act.id, { ...p, ...act })}>
                    ${(act.id === 'probe' || act.id === 'probe_all') && this.isProbing ? 'Testing...' : act.label}
                  </button>
                `)}
              </div>
            ` : ''}
          </div>
        `;
      }

      case 'demo-bundle': {
        return html`
          <div class="gen-tile card">
            <div class="gen-card-header"><h4 class="gen-card-title">${p.name || 'Demo Bundle'}</h4><span style="display:flex; align-items:center; gap:6px;">${p.release ? html`<span class="ct-tag low">${p.release}</span>` : ''}<button type="button" class="open-btn" aria-label="Open details" title="Open details" @click=${() => this.handleAction('open_item', { ...p, kind: 'bundle' })}>${openArrowIcon(14)}</button></span></div>
            <div style="font-size:12px; color:var(--now-text-secondary, #475467);">Industry: <strong>${p.industry || 'General'}</strong></div>
            <div class="gen-card-meta-row"><span>Tables: <strong>${p.tables_count ?? 0}</strong></span><span>Records: <strong>${p.records_count ?? 0}</strong></span></div>
            ${p.actions && p.actions.length ? html`
              <div class="gen-actions-row">
                ${p.actions.map((act: any) => html`<button type="button" class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}" @click=${() => this.handleAction(act.id, { ...p, ...act })}>${act.label}</button>`)}
              </div>
            ` : ''}
          </div>
        `;
      }

      case 'security-alert': {
        return html`
          <div class="gen-tile alert-tile">
            <div class="gen-card-header"><h4 class="gen-alert-title">${t.title || p.agent_name || 'Security Review Required'}</h4><span class="ct-tag medium">${p.severity || 'MEDIUM'}</span></div>
            <p class="gen-alert-desc">${p.issue || ''}</p>
            ${p.remediation ? html`<div style="font-size:11.5px; color:#991b1b; font-weight:600;">Remediation: ${p.remediation}</div>` : ''}
            ${p.actions && p.actions.length ? html`
              <div class="gen-actions-row">
                ${p.actions.map((act: any) => html`<button type="button" class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}" @click=${() => this.handleAction(act.id, { ...p, ...act })}>${act.label}</button>`)}
              </div>
            ` : ''}
          </div>
        `;
      }

      case 'fluent-schema': {
        return html`
          <div class="gen-tile card">
            <div class="gen-card-header"><h4 class="gen-card-title">${p.table_name || 'Fluent Table'}</h4><span class="ct-tag low">${p.file_path || '*.now.ts'}</span></div>
            <pre style="margin:4px 0; padding:8px 10px; background:#0f172a; color:#f8fafc; border-radius:6px; font-size:11px; overflow-x:auto; font-family:monospace;">${p.code || ''}</pre>
            ${p.actions && p.actions.length ? html`
              <div class="gen-actions-row">
                ${p.actions.map((act: any) => html`<button type="button" class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}" @click=${() => this.handleAction(act.id, { ...p, ...act })}>${act.label}</button>`)}
              </div>
            ` : ''}
          </div>
        `;
      }

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
            ${p.actions && p.actions.length ? html`
              <div class="gen-actions-row">
                ${p.actions.map((act: any) => html`<button type="button" class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}" @click=${() => this.handleAction(act.id, { ...p, ...act })}>${act.label}</button>`)}
              </div>
            ` : ''}
          </div>
        `;
      }

      case 'media-player': {
        return html`
          <now-media-tile
            .title=${t.title || 'Demonstration Media'}
            .url=${p.url || ''}
            .mediaType=${p.media_type || (p.url?.endsWith('.webm') ? 'video' : 'screenshot')}
            .label=${p.label || ''}
            .actions=${p.actions || []}
          ></now-media-tile>
        `;
      }

      case 'rich-text':
      default: {
        return html`
          <div class="gen-tile rich">
            <h4 class="gen-rich-title">${t.title || 'Summary'}</h4>
            <div class="gen-rich-body">${p.body || ''}</div>
            ${p.actions && p.actions.length ? html`
              <div class="gen-actions-row">
                ${p.actions.map((act: any) => html`<button type="button" class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}" @click=${() => this.handleAction(act.id, { ...p, ...act })}>${act.label}</button>`)}
              </div>
            ` : ''}
          </div>
        `;
      }
    }
  }
}
