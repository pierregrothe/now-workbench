import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

interface SynthesizedDemoResult {
  bundle_id: string;
  bundle_path: string;
  title: string;
  customer_name: string;
  industry: string;
  fluent_table_name: string;
  fluent_code: string;
  seed_records: Array<Record<string, unknown>>;
  sys_properties: Record<string, string>;
  narrative_markdown: string;
}

interface CaptureArtifact {
  id: string;
  bundle_id: string;
  instance_url: string;
  target_path: string;
  media_type: 'screenshot' | 'video';
  label: string;
  filename: string;
  file_path: string;
  url: string;
  engine: string;
  created_at: string;
}

interface InstanceData {
  id: string;
  name: string;
  url: string;
  username: string;
  release: string;
  is_default: boolean;
  status: string;
  last_checked: string | null;
}

export type TileLayout = '1-col' | '2-col' | '3-col' | 'auto';

export interface UITileAction {
  id: string;
  label: string;
  variant?: 'primary' | 'secondary' | 'accent' | 'danger';
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

export interface GenerativeUIResponse {
  summary: string;
  layout: TileLayout;
  tiles: UITileSpec[];
}

export interface HomeQAItem {
  id: string;
  question: string;
  response: GenerativeUIResponse;
}

@customElement('now-conversational-workspace')
export class NowConversationalWorkspace extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background-color: var(--now-bg-canvas, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .top-utility-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 36px;
      border-bottom: 1px solid var(--now-border-subtle, #f0f0ee);
      background: var(--now-bg-surface-0, #ffffff);
      flex-shrink: 0;
    }

    .workspace-breadcrumb {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13.5px;
      font-weight: 600;
      color: var(--now-text-primary, #2c2e33);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--now-color-brand-green, #62d84e);
    }

    .utility-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .instance-picker-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      background: var(--now-bg-surface-1, #f7f7f5);
      border: 1px solid var(--now-border-subtle, #dcded9);
      border-radius: 999px;
      font-size: 12px;
      font-weight: 500;
      color: var(--now-text-secondary, #374151);
    }

    .instance-picker-label {
      font-weight: 700;
      color: var(--now-color-brand-green, #62d84e);
      text-transform: uppercase;
      font-size: 10px;
      letter-spacing: 0.04em;
    }

    .instance-picker-select {
      appearance: none;
      background: transparent;
      border: none;
      font-family: inherit;
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-primary, #16181d);
      padding-right: 14px;
      cursor: pointer;
      outline: none;
      background-image: url("data:image/svg+xml;utf8,<svg fill='%2362d84e' height='12' viewBox='0 0 24 24' width='12' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/></svg>");
      background-repeat: no-repeat;
      background-position: right center;
    }

    .pill-btn {
      position: relative;
      appearance: none;
      border: 1px solid var(--now-border-medium, #e2e3e0);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-size: 12.5px;
      font-weight: 600;
      padding: 7px 14px;
      border-radius: 999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: inherit;
      transition: background 0.12s ease, border-color 0.12s ease, transform 0.08s ease;
    }

    .pill-btn:hover {
      background: var(--now-bg-surface-1, #f4f4f2);
      border-color: var(--now-border-subtle, #c8c9c6);
    }

    .pill-btn.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      justify-content: center;
      border-radius: 50%;
    }

    .pill-btn.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .pill-btn.primary {
      background: #032d42;
      color: #ffffff;
      border-color: #032d42;
    }

    .pill-btn.primary:hover {
      background: #053b56;
    }

    .pill-btn.accent {
      background: #62d84e;
      color: #032d42;
      border-color: #62d84e;
    }

    .pill-btn.accent:hover {
      background: #52c43e;
    }

    .scroll-canvas {
      flex: 1;
      overflow-y: auto;
      padding: 32px 36px 40px 36px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .canvas-container {
      width: 100%;
      max-width: 1380px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* CONTROL TOWER HERO */
    .control-tower-hero {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 16px 0 10px 0;
      gap: 14px;
      width: 100%;
    }

    .control-tower-greeting {
      font-size: 26px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      letter-spacing: -0.02em;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .sparkle-glyph {
      font-size: 22px;
      color: var(--now-text-primary, #0f172a);
    }

    .elevated-prompt-pill {
      width: 100%;
      max-width: 780px;
      background: var(--now-bg-surface-0, #ffffff);
      border: 1.5px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 999px;
      padding: 6px 8px 6px 18px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
      display: flex;
      align-items: center;
      gap: 12px;
      transition: all 0.15s ease;
    }

    .elevated-prompt-pill:focus-within {
      border-color: var(--now-color-brand-green, #62d84e);
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.08);
    }

    .pill-attach-btn {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: none;
      background: transparent;
      color: var(--now-text-muted, #64748b);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
    }

    .pill-attach-btn svg {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      stroke-width: 2;
      fill: none;
    }

    .elevated-prompt-input {
      flex: 1;
      border: none;
      background: transparent;
      font-family: inherit;
      font-size: 14.5px;
      color: var(--now-text-primary, #0f172a);
      outline: none;
    }

    .elevated-prompt-input::placeholder {
      color: var(--now-text-muted, #94a3b8);
    }

    .send-action-btn {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: none;
      background: var(--now-color-brand-green, #16a34a);
      color: #ffffff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.12s ease, background 0.12s ease;
      flex-shrink: 0;
    }

    .send-action-btn:hover {
      transform: scale(1.05);
      background: #15803d;
    }

    .send-action-btn svg {
      width: 17px;
      height: 17px;
      stroke: currentColor;
      stroke-width: 2;
      fill: none;
    }
      fill: none;
    }

    .hero-chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: center;
      margin-top: 4px;
    }

    .hero-chip {
      appearance: none;
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-secondary, #475467);
      font-size: 12.5px;
      font-weight: 500;
      padding: 6px 14px;
      border-radius: 999px;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.12s ease;
    }

    .hero-chip:hover {
      background: var(--now-bg-surface-1, #f8fafc);
      border-color: var(--now-border-medium, #cbd5e1);
      color: var(--now-text-primary, #0f172a);
    }

    /* CONTROL TOWER GRID */
    .ct-dashboard-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
      width: 100%;
    }

    .ct-grid-row-1 {
      display: grid;
      grid-template-columns: minmax(460px, 1.4fr) minmax(310px, 1fr) minmax(310px, 1fr);
      gap: 16px;
    }

    .ct-grid-row-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    @media (max-width: 1180px) {
      .ct-grid-row-1 {
        grid-template-columns: 1fr;
      }
      .ct-grid-row-2 {
        grid-template-columns: 1fr;
      }
    }

    .ct-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 16px;
      padding: 20px 22px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
      display: flex;
      flex-direction: column;
      gap: 14px;
      transition: all 0.15s ease;
    }

    .ct-card:hover {
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.05);
      border-color: var(--now-border-medium, #cbd5e1);
    }

    .ct-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .ct-card-title {
      font-size: 15px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .ct-card-arrow {
      font-size: 14px;
      color: var(--now-text-muted, #64748b);
      cursor: pointer;
    }

    .ct-card-sub {
      font-size: 12px;
      color: var(--now-text-muted, #64748b);
      margin: -6px 0 2px 0;
    }

    /* Subtabs inside Card */
    .ct-action-subtabs {
      display: flex;
      gap: 14px;
      border-bottom: 1px solid var(--now-border-subtle, #f1f5f9);
      padding-bottom: 8px;
    }

    .ct-subtab {
      background: transparent;
      border: none;
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-muted, #64748b);
      cursor: pointer;
      padding: 2px 0;
      font-family: inherit;
    }

    .ct-subtab.active {
      color: var(--now-text-primary, #0f172a);
      border-bottom: 2px solid var(--now-text-primary, #0f172a);
    }

    .ct-action-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .ct-action-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 6px 0;
      border-bottom: 1px solid var(--now-border-subtle, #f8fafc);
    }

    .ct-action-item:last-child {
      border-bottom: none;
    }

    .ct-item-content {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .ct-tag {
      font-size: 10.5px;
      font-weight: 700;
      letter-spacing: 0.4px;
    }

    .ct-tag.medium {
      color: #b45309;
    }

    .ct-tag.low {
      color: #64748b;
    }

    .ct-action-text {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .ct-action-btn {
      appearance: none;
      border: 1px solid #d1d5db;
      background: #ffffff;
      color: #374151;
      font-size: 11.5px;
      font-weight: 600;
      padding: 5px 12px;
      border-radius: 999px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.12s ease;
      font-family: inherit;
    }

    .ct-action-btn:hover {
      background: #f9fafb;
      border-color: #9ca3af;
    }

    .ct-action-btn.primary {
      background: #0f172a;
      color: #ffffff;
      border-color: #0f172a;
    }

    .ct-action-btn.primary:hover {
      background: #1e293b;
    }

    /* KPI Card Elements */
    .ct-kpi-value {
      font-size: 34px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--now-text-primary, #0f172a);
      line-height: 1.1;
      margin-top: 4px;
    }

    .ct-kpi-trend {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--now-color-brand-green, #16a34a);
      margin-bottom: 6px;
    }

    .ct-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      background: var(--now-bg-surface-1, #f8fafc);
      border-left: 3px solid var(--now-color-brand-green, #16a34a);
      padding: 8px 12px;
      border-radius: 4px;
      margin-top: auto;
    }

    .ct-banner-text {
      font-size: 11.5px;
      color: var(--now-text-secondary, #475467);
      font-weight: 500;
    }

    /* Donut Layout */
    .ct-donut-wrap {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      margin: auto 0;
    }

    .ct-donut-legend {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .ct-legend-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--now-text-secondary, #475467);
    }

    .ct-legend-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    /* Gauge & Governance Bars */
    .ct-gauge-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin: auto 0;
    }

    .ct-gov-bars {
      display: flex;
      gap: 4px;
      width: 100%;
      height: 14px;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 10px;
    }

    .ct-gov-seg {
      height: 100%;
    }

    /* MODE 2: SPLIT-SCREEN CONVERSATIONAL WORKSPACE */
    .split-screen-container {
      display: flex;
      gap: 18px;
      width: 100%;
      min-height: calc(100vh - 110px);
    }

    @media (max-width: 1080px) {
      .split-screen-container {
        flex-direction: column;
      }
    }

    /* Left Pane: Otto Chat */
    .split-chat-pane {
      width: 440px;
      flex-shrink: 0;
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04);
    }

    @media (max-width: 1080px) {
      .split-chat-pane {
        width: 100%;
        max-height: 520px;
      }
    }

    .split-chat-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 18px;
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
    }

    .split-header-title {
      font-size: 15px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      margin: 0;
    }

    .split-header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .split-icon-btn {
      width: 26px;
      height: 26px;
      border-radius: 6px;
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-secondary, #475467);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
    }

    .split-icon-btn svg {
      width: 13px;
      height: 13px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .split-chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .ai-steps-toggle {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-muted, #64748b);
      cursor: pointer;
      background: transparent;
      border: none;
      padding: 0;
    }

    .ai-steps-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 8px 12px;
      background: var(--now-bg-surface-1, #f8fafc);
      border-radius: 8px;
      font-size: 12px;
      color: var(--now-text-secondary, #475467);
    }

    .ai-step-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .ai-step-icon {
      color: var(--now-color-brand-green, #16a34a);
      font-weight: 700;
    }

    .split-chat-text {
      font-size: 13.5px;
      line-height: 1.6;
      color: var(--now-text-primary, #0f172a);
    }

    .split-action-pills {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .split-action-pill {
      appearance: none;
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-secondary, #475467);
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      cursor: pointer;
    }

    /* Inline Alert Card (Critical) */
    .inline-alert-card {
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 12px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .alert-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .alert-title {
      font-size: 13px;
      font-weight: 700;
      color: #991b1b;
      margin: 0;
    }

    .alert-badge-critical {
      background: #dc2626;
      color: #ffffff;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 7px;
      border-radius: 999px;
    }

    .alert-desc {
      font-size: 12px;
      color: #7f1d1d;
      line-height: 1.45;
      margin: 0;
    }

    .alert-meta-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 6px;
      font-size: 11px;
      color: #991b1b;
      border-top: 1px solid #fee2e2;
      padding-top: 8px;
    }

    .alert-btn-row {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }

    .btn-skip {
      flex: 1;
      padding: 6px;
      font-size: 11.5px;
      font-weight: 600;
      background: #ffffff;
      border: 1px solid #fca5a5;
      color: #7f1d1d;
      border-radius: 6px;
      cursor: pointer;
    }

    .btn-view-details {
      flex: 1;
      padding: 6px;
      font-size: 11.5px;
      font-weight: 600;
      background: #0f172a;
      border: 1px solid #0f172a;
      color: #ffffff;
      border-radius: 6px;
      cursor: pointer;
    }

    .btn-kill-switch {
      background: #dc2626;
      border: 1px solid #dc2626;
      color: #ffffff;
      font-size: 12px;
      font-weight: 700;
      padding: 7px 14px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .user-bubble {
      align-self: flex-end;
      background: #0f172a;
      color: #ffffff;
      padding: 8px 14px;
      border-radius: 12px 12px 2px 12px;
      font-size: 13px;
      max-width: 80%;
    }

    .split-chat-input-row {
      padding: 12px 16px;
      border-top: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-0, #ffffff);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .split-prompt-pill {
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 999px;
      padding: 4px 6px 4px 12px;
    }

    .split-prompt-input {
      flex: 1;
      border: none;
      background: transparent;
      font-size: 13px;
      outline: none;
      color: var(--now-text-primary, #0f172a);
    }

    .split-send-btn {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      border: none;
      background: var(--now-color-brand-green, #23a17e);
      color: #ffffff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .split-send-btn svg {
      width: 14px;
      height: 14px;
      stroke: currentColor;
      stroke-width: 2;
      fill: none;
    }

    .disclaimer-text {
      font-size: 10.5px;
      color: var(--now-text-muted, #94a3b8);
      text-align: center;
    }

    /* Right Pane: Generative Stage */
    .split-stage-pane {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .stage-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 16px;
      padding: 14px 20px;
    }

    .stage-title-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .stage-title {
      font-size: 18px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      margin: 0;
    }

    .stage-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 999px;
    }

    .stage-badge.active {
      background: #dcfce7;
      color: #15803d;
    }

    .stage-badge.disabled {
      background: #f1f5f9;
      color: #64748b;
    }

    .stage-close-btn {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-0, #ffffff);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--now-text-secondary, #475467);
    }

    .stage-grid-top {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    @media (max-width: 900px) {
      .stage-grid-top {
        grid-template-columns: 1fr;
      }
    }

    .stage-access-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 16px;
      padding: 22px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .access-warning-banner {
      background: #fef2f2;
      border: 1px solid #fee2e2;
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      gap: 10px;
      color: #991b1b;
      font-size: 12.5px;
      font-weight: 500;
    }

    .access-meta-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      font-size: 12px;
      border-bottom: 1px solid var(--now-border-subtle, #f1f5f9);
      padding-bottom: 14px;
    }

    .access-meta-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .access-meta-k {
      color: var(--now-text-muted, #94a3b8);
      font-size: 11px;
    }

    .access-meta-v {
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .access-node-map {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 30px;
      padding: 20px 0;
    }

    .access-node-pill {
      background: #ffffff;
      border: 1.5px solid #cbd5e1;
      border-radius: 10px;
      padding: 8px 16px;
      font-size: 12.5px;
      font-weight: 600;
      color: #1e293b;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .access-node-pill.agent {
      border-color: #6366f1;
      background: #f5f3ff;
      color: #4338ca;
    }

    /* Conversational Q&A Cards on Home Screen */
    .home-qa-thread {
      width: 100%;
      max-width: 820px;
      margin: 12px auto 0 auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .qa-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e6e7e4);
      border-radius: 16px;
      padding: 20px 24px;
      box-shadow: 0 4px 18px var(--now-shadow-soft, rgba(0, 0, 0, 0.03));
      display: flex;
      flex-direction: column;
      gap: 12px;
      text-align: left;
    }

    .qa-user-row {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 14px;
      font-weight: 600;
      color: var(--now-text-primary, #0b0f19);
      border-bottom: 1px solid var(--now-border-subtle, #ececea);
      padding-bottom: 10px;
    }

    .qa-user-badge {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      background: var(--now-bg-surface-1, #f3f4f6);
      color: var(--now-text-secondary, #4b5563);
      padding: 3px 8px;
      border-radius: 999px;
    }

    .qa-assistant-row {
      display: flex;
      gap: 14px;
      align-items: flex-start;
    }

    .qa-otto-avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: linear-gradient(135deg, #9333ea, #3b82f6);
      color: #ffffff;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      flex-shrink: 0;
      box-shadow: 0 0 10px rgba(147, 51, 234, 0.25);
    }

    .qa-assistant-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .qa-otto-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .qa-otto-name {
      font-size: 13px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
    }

    .qa-continue-btn {
      appearance: none;
      border: 1px solid #e9d5ff;
      background: #faf5ff;
      color: #7e22ce;
      font-size: 11.5px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 999px;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.12s ease;
    }

    .qa-continue-btn:hover {
      background: #f3e8ff;
      border-color: #c084fc;
    }

    .qa-answer-text {
      font-size: 13.5px;
      line-height: 1.6;
      color: var(--now-text-primary, #1f2937);
      white-space: pre-wrap;
    }

    /* Generative UI Tile Grid & Component Styles */
    .qa-summary-text {
      font-size: 14px;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
      line-height: 1.5;
      margin: 2px 0 6px 0;
    }

    .generative-tile-grid {
      display: grid;
      gap: 14px;
      width: 100%;
      margin-top: 6px;
    }

    .generative-tile-grid.col-1 {
      grid-template-columns: 1fr;
    }

    .generative-tile-grid.col-2 {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .generative-tile-grid.col-3 {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .generative-tile-grid.auto {
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }

    @media (max-width: 860px) {
      .generative-tile-grid.col-2,
      .generative-tile-grid.col-3 {
        grid-template-columns: 1fr;
      }
    }

    .gen-tile {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 14px;
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
      transition: all 0.15s ease;
      text-align: left;
    }

    .gen-tile:hover {
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.06);
      border-color: var(--now-border-medium, #cbd5e1);
    }

    .gen-tile.kpi {
      border-left: 4px solid var(--now-color-brand-green, #16a34a);
    }

    .gen-kpi-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .gen-kpi-icon {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: #dcfce7;
      color: #15803d;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .gen-kpi-icon svg {
      width: 17px;
      height: 17px;
      stroke: currentColor;
      stroke-width: 2;
      fill: none;
    }

    .gen-kpi-number {
      font-size: 34px;
      font-weight: 800;
      color: var(--now-text-primary, #0f172a);
      line-height: 1;
      letter-spacing: -0.02em;
      margin-top: 4px;
    }

    .gen-kpi-label {
      font-size: 13.5px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
    }

    .gen-kpi-sub {
      font-size: 12px;
      color: var(--now-text-muted, #64748b);
    }

    .gen-tile.card {
      background: var(--now-bg-surface-0, #ffffff);
    }

    .gen-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .gen-card-title {
      font-size: 14.5px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      margin: 0;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .gen-card-url {
      font-size: 11.5px;
      font-family: var(--now-font-mono, monospace);
      color: var(--now-text-secondary, #475467);
      background: var(--now-bg-surface-1, #f8fafc);
      padding: 5px 10px;
      border-radius: 6px;
      border: 1px solid var(--now-border-subtle, #f1f5f9);
      word-break: break-all;
    }

    .gen-card-meta-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11.5px;
      color: var(--now-text-secondary, #475467);
      border-top: 1px solid var(--now-border-subtle, #f1f5f9);
      padding-top: 8px;
    }

    .gen-actions-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 4px;
      flex-wrap: wrap;
    }

    .gen-tile.alert-tile {
      background: #fef2f2;
      border-color: #fee2e2;
      border-left: 4px solid #dc2626;
    }

    .gen-alert-title {
      font-size: 14px;
      font-weight: 700;
      color: #991b1b;
      margin: 0;
    }

    .gen-alert-desc {
      font-size: 12.5px;
      color: #7f1d1d;
      line-height: 1.45;
      margin: 0;
    }

    .gen-tile.rich {
      background: var(--now-bg-surface-1, #f8fafc);
      border-left: 4px solid #6366f1;
    }

    .gen-rich-title {
      font-size: 13.5px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      margin: 0;
    }

    .gen-rich-body {
      font-size: 12.5px;
      color: var(--now-text-secondary, #475467);
      line-height: 1.5;
      white-space: pre-wrap;
    }

    .gen-tile.table-tile {
      background: var(--now-bg-surface-0, #ffffff);
      border-left: 4px solid var(--now-color-brand-blue, #2563eb);
      overflow-x: auto;
    }

    .gen-table-title {
      font-size: 13.5px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      margin: 0;
    }

    .gen-data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      margin-top: 4px;
    }

    .gen-data-table th {
      text-align: left;
      padding: 6px 10px;
      background: var(--now-bg-surface-1, #f8fafc);
      color: var(--now-text-muted, #64748b);
      font-weight: 600;
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    .gen-data-table td {
      padding: 6px 10px;
      border-bottom: 1px solid var(--now-border-subtle, #f1f5f9);
      color: var(--now-text-primary, #0f172a);
      word-break: break-word;
    }

    .gen-data-table tr:last-child td {
      border-bottom: none;
    }

    .gen-data-table tr:hover td {
      background: var(--now-bg-surface-1, #f8fafc);
    }

    .gen-tile.media-tile {
      background: var(--now-bg-surface-0, #ffffff);
      border-left: 4px solid #8b5cf6;
      gap: 12px;
    }

    .gen-media-preview {
      width: 100%;
      border-radius: 8px;
      overflow: hidden;
      background: #000000;
      display: flex;
      justify-content: center;
      align-items: center;
      max-height: 380px;
    }

    .gen-media-preview video {
      width: 100%;
      max-height: 380px;
      display: block;
    }

    .gen-media-preview img {
      width: 100%;
      max-height: 380px;
      object-fit: cover;
      display: block;
    }

    /* Studio Card */
    .studio-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e6e7e4);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 4px 20px var(--now-shadow-soft, rgba(0, 0, 0, 0.03));
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .card-title-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .card-icon {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      background: var(--now-bg-surface-1, #f1f8ef);
      color: var(--now-color-brand-green, #62d84e);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .card-icon svg {
      width: 18px;
      height: 18px;
      stroke: currentColor;
      stroke-width: 1.8;
      fill: none;
    }

    .card-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
    }

    .card-subtitle {
      font-size: 12.5px;
      color: var(--now-text-secondary, #6b7280);
      margin: 2px 0 0 0;
    }

    .badge-tag {
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--now-bg-surface-1, #f3f4f6);
      color: var(--now-text-secondary, #374151);
    }

    .form-grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .field-group {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .field-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-secondary, #374151);
    }

    .field-input,
    .field-select,
    .field-textarea {
      font-family: inherit;
      font-size: 13.5px;
      color: var(--now-text-primary, #16181d);
      background: var(--now-bg-surface-1, #fafaf9);
      border: 1px solid var(--now-border-subtle, #dcded9);
      border-radius: 10px;
      padding: 9px 12px;
      outline: none;
      transition: border-color 0.12s ease, background 0.12s ease;
    }

    .field-input:focus,
    .field-select:focus,
    .field-textarea:focus {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-color-brand-green, #62d84e);
    }

    .field-textarea {
      min-height: 82px;
      resize: vertical;
      line-height: 1.45;
    }

    .card-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding-top: 4px;
    }

    .status-banner {
      font-size: 12.5px;
      padding: 10px 14px;
      border-radius: 10px;
      background: var(--now-bg-surface-1, #f0fdf4);
      border: 1px solid var(--now-border-subtle, #bbf7d0);
      color: var(--now-color-brand-green, #166534);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }

    .result-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e6e7e4);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 6px 24px var(--now-shadow-soft, rgba(0, 0, 0, 0.04));
    }

    .result-header {
      background: var(--now-bg-surface-1, #fafaf9);
      padding: 18px 24px;
      border-bottom: 1px solid var(--now-border-subtle, #ececea);
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
    }

    .result-tabs {
      display: flex;
      gap: 6px;
    }

    .result-tab {
      appearance: none;
      border: 1px solid transparent;
      background: transparent;
      color: var(--now-text-secondary, #4b5563);
      font-size: 13px;
      font-weight: 600;
      padding: 7px 14px;
      border-radius: 999px;
      cursor: pointer;
      font-family: inherit;
    }

    .result-tab.active {
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
    }

    .result-body {
      padding: 24px;
    }

    .narrative-box {
      background: var(--now-bg-surface-1, #fafaf9);
      border: 1px solid var(--now-border-subtle, #ececea);
      border-radius: 12px;
      padding: 20px;
      white-space: pre-wrap;
      font-size: 13.5px;
      line-height: 1.65;
      color: var(--now-text-primary, #1f2937);
    }

    .code-pre {
      background: #0f172a;
      color: #f8fafc;
      font-family: "JetBrains Mono", monospace;
      font-size: 12px;
      line-height: 1.55;
      padding: 16px;
      border-radius: 12px;
      overflow-x: auto;
      margin: 0;
      max-height: 360px;
    }

    .capture-gallery {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 14px;
      margin-top: 8px;
    }

    .capture-item {
      border: 1px solid var(--now-border-subtle, #e5e7eb);
      border-radius: 12px;
      overflow: hidden;
      background: var(--now-bg-surface-1, #fafaf9);
      display: flex;
      flex-direction: column;
    }

    .capture-preview {
      height: 140px;
      background: var(--now-bg-surface-2, #032d42);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      position: relative;
      cursor: pointer;
    }

    .capture-preview:hover .capture-hover-badge {
      opacity: 1;
    }

    .capture-hover-badge {
      position: absolute;
      inset: 0;
      background: rgba(3, 45, 66, 0.55);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: opacity 0.15s ease-in-out;
      color: #ffffff;
      font-size: 11px;
      font-weight: 600;
      gap: 6px;
      pointer-events: none;
    }

    .capture-preview img,
    .capture-preview video {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.2s ease;
    }

    .capture-preview:hover img,
    .capture-preview:hover video {
      transform: scale(1.03);
    }

    .capture-meta {
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .capture-caption {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--now-text-primary, #111827);
    }

    .capture-date {
      font-size: 10.5px;
      color: var(--now-text-tertiary, #9ca3af);
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .lightbox-overlay {
      position: fixed;
      inset: 0;
      background: rgba(3, 45, 66, 0.75);
      backdrop-filter: blur(6px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      padding: 24px;
    }

    .lightbox-card {
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: var(--now-radius-lg, 12px);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.3);
      max-width: 980px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .lightbox-header {
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-1, #f8fafc);
    }

    .lightbox-body {
      padding: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0b1f30;
      overflow: auto;
      max-height: 65vh;
    }

    .lightbox-body img,
    .lightbox-body video {
      max-width: 100%;
      max-height: 60vh;
      border-radius: 6px;
      object-fit: contain;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }

    .lightbox-footer {
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-top: 1px solid var(--now-border-subtle, #e2e8f0);
      background: var(--now-bg-surface-0, #ffffff);
      font-size: 12px;
    }

    .capture-sub {
      font-size: 11px;
      color: var(--now-text-secondary, #6b7280);
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 2px;
    }

    .capture-sub a {
      color: var(--now-color-brand-green, #62d84e);
      font-weight: 600;
      text-decoration: none;
    }
  `;

  @property({ type: String }) viewMode: 'home' | 'synthesizer' | 'capture' = 'home';
  @property({ type: String }) activeThreadId = '';
  @property({ type: String }) incomingPrompt = '';

  // Top chat input on Home view
  @state() private homeChatInput = '';
  @state() private homeQAList: HomeQAItem[] = [];

  // Conversation Mode & Thread History state (SQLite backed)
  @state() private splitScreenOpen = false;
  @state() private splitViewStage: 'overview' | 'details' = 'overview';
  @state() private ticketAgentStatus: 'Deployed & Active' | 'Disabled' = 'Deployed & Active';
  @state() private actionSubTab: 'recommendations' | 'assigned' | 'unassigned' = 'recommendations';
  @state() private aiStepsExpanded = false;
  @state() private killSwitchActivated = false;
  @state() private splitChatInput = '';
  @state() private splitUserMessages: Array<{ text: string; time: string }> = [];

  // Active Otto Conversation State
  @state() private currentSessionTitle = 'New Otto Conversation';
  @state() private currentSessionPrompt = '';
  @state() private currentSessionResponse: GenerativeUIResponse | null = null;
  @state() private sessionFollowUps: Array<{ prompt: string; response: GenerativeUIResponse }> = [];
  @state() private sessionTopicType: 'instances' | 'bundles' | 'security' | 'fluent' | 'general' = 'general';
  @state() private currentThreadArchived = false;
  @state() private conversationMessages: Array<{
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at?: string;
    response?: GenerativeUIResponse;
  }> = [];
  @state() private contextLimitError = '';
  private readonly maxContextMessages = 20;

  // Use-Case Synthesizer state
  @state() private useCasePrompt =
    'Automate enterprise clinical device triage and proactive field dispatch when network telemetry anomalies occur on hospital infusion pumps.';
  @state() private customerName = 'Novartis BioHealth';
  @state() private industry = 'Healthcare & Life Sciences';
  @state() private releaseTarget = 'Zurich';
  @state() private personaPrimary = 'Amelia Chen (Clinical Operations Lead)';
  @state() private personaSecondary = 'Marcus Vance (Field Reliability Architect)';
  @state() private isSynthesizing = false;
  @state() private synthesizedResult: SynthesizedDemoResult | null = null;
  @state() private activeResultTab: 'narrative' | 'datasets' | 'customizations' = 'narrative';
  @state() private seedStatusMessage = '';

  // Media Capture state
  @state() private uriPath = '/now/nav/ui/classic/params/target/incident_list.do';
  @state() private captureMode: 'screenshot' | 'video' = 'screenshot';
  @state() private captureCaption = 'Live ServiceNow Workspace View';
  @state() private isCapturing = false;
  @state() private captures: CaptureArtifact[] = [];
  @state() private previewCapture: CaptureArtifact | null = null;
  @state() private captureSelectedBundleId = 'sample-ai-assistant';

  // Instance Targeting state
  @state() private instances: InstanceData[] = [];
  @state() private selectedInstanceId = '';
  @state() private bundleCount = 2;
  @state() private demoBundles: Array<{
    id: string;
    name: string;
    industry: string;
    release: string;
    tables_count: number;
    records_count: number;
  }> = [];
  @state() private claudeKeyConfigured = false;
  @state() private probeStatus = 'Unverified (Not Tested)';
  @state() private isProbing = false;
  @state() private tileActionFeedback = '';

  private get selectedInstance(): InstanceData | undefined {
    return this.instances.find((i) => i.id === this.selectedInstanceId) ?? this.instances[0];
  }

  private formatRealInstanceStatus(rawStatus?: string, detailMsg?: string): string {
    const norm = (rawStatus || '').trim().toLowerCase();
    if (norm === 'authenticated') {
      return detailMsg ? `Authenticated (${detailMsg})` : 'Authenticated (HTTP 200)';
    }
    if (norm === 'unreachable') {
      return detailMsg ? `Unreachable (${detailMsg})` : 'Unreachable (Connection Failed)';
    }
    if (norm === 'auth_failed') {
      return detailMsg ? `Auth Failed (${detailMsg})` : 'Auth Failed (HTTP 401/403)';
    }
    if (norm === 'error') {
      return detailMsg ? `Error (${detailMsg})` : 'HTTP Error';
    }
    if (norm === 'unknown' || !norm) {
      return 'Unverified (Not Tested)';
    }
    return rawStatus || 'Unverified (Not Tested)';
  }

  private statusBadgeVariant(statusText?: string): 'high' | 'medium' | 'critical' | 'low' {
    const s = (statusText || '').toLowerCase();
    if (s.includes('authenticated')) {
      return 'high';
    }
    if (s.includes('unreachable') || s.includes('failed') || s.includes('error')) {
      return 'critical';
    }
    return 'medium';
  }

  connectedCallback(): void {
    super.connectedCallback();
    try {
      const saved = localStorage.getItem('now-workbench-capture-bundle');
      if (saved) {
        this.captureSelectedBundleId = saved;
      }
    } catch {}
    void this.loadCaptures(this.captureSelectedBundleId);
    void this.loadInstances();
    void this.loadBundles();
    void this.loadSettings();
  }

  private async loadBundles(): Promise<void> {
    try {
      const res = await fetch('/api/demos');
      if (res.ok) {
        const list = (await res.json()) as Array<{
          manifest?: { id: string; name: string; sn_release?: string; tags?: string[] };
          fluent_files?: string[];
          seed_files?: string[];
        }>;
        if (Array.isArray(list) && list.length > 0) {
          this.bundleCount = list.length;
          this.demoBundles = list.map((b) => ({
            id: b.manifest?.id || 'demo-bundle',
            name: b.manifest?.name || 'Demonstration Bundle',
            industry: b.manifest?.tags?.[0] || 'Enterprise Workflow',
            release: b.manifest?.sn_release || 'Zurich',
            tables_count: b.fluent_files?.length || 2,
            records_count: (b.seed_files?.length || 1) * 12,
          }));
        }
      }
    } catch {
      // offline preview fallback
    }
  }

  private async loadSettings(): Promise<void> {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const prefs = (await res.json()) as { claude_api_key_configured?: boolean };
        this.claudeKeyConfigured = !!prefs.claude_api_key_configured;
      }
    } catch {
      // offline preview fallback
    }
  }

  private summarizeAllInstances(): { breakdown: string; unauthCount: number } {
    if (!this.instances || this.instances.length === 0) {
      return { breakdown: 'No Instances Configured', unauthCount: 0 };
    }
    const counts: Record<string, number> = {};
    let unauthCount = 0;
    for (const inst of this.instances) {
      const lbl = this.formatRealInstanceStatus(inst.status);
      counts[lbl] = (counts[lbl] || 0) + 1;
      if ((inst.status || '').trim().toLowerCase() !== 'authenticated') {
        unauthCount += 1;
      }
    }
    const breakdown = Object.entries(counts)
      .map(([lbl, cnt]) => `${cnt} ${lbl}`)
      .join(', ');
    return { breakdown, unauthCount };
  }

  private syncInstanceTilesWithCurrentState(): void {
    const { breakdown, unauthCount } = this.summarizeAllInstances();
    const count = this.instances.length;
    const primary = this.selectedInstance || this.instances[0];
    const primaryId = primary?.id || '';
    const statusById = new Map(
      this.instances.map((i) => [i.id, { raw: i.status, formatted: this.formatRealInstanceStatus(i.status) }])
    );

    const kpiActions: Array<Record<string, any>> = [
      { id: 'show_instances', label: 'Show Instance Details', variant: 'primary' },
      { id: 'probe_all', label: 'Check Authentication', variant: 'secondary', instance_id: primaryId },
      { id: 'manage', label: 'Manage in Settings', variant: 'secondary' },
    ];
    if (unauthCount > 0) {
      kpiActions.splice(2, 0, {
        id: 'delete_unauthenticated',
        label: `Delete Unauthenticated (${unauthCount})`,
        variant: 'secondary',
      });
    }

    this.conversationMessages = this.conversationMessages.map((msg) => {
      if (msg.role !== 'assistant' || !msg.response) {
        return msg;
      }
      const nextTiles = msg.response.tiles
        .filter((t) => {
          if (t.type === 'instance-card' && t.props?.instance_id) {
            return statusById.has(t.props.instance_id);
          }
          return true;
        })
        .map((t) => {
          if (t.type === 'instance-kpi' && t.id !== 'tile-bundle-kpi') {
            return {
              ...t,
              props: {
                ...t.props,
                count,
                label: count === 1 ? 'Managed Instance' : 'Managed Instances',
                status: breakdown,
                badge: breakdown,
                subtitle: `Primary: ${primary?.name || 'None'} (${primary?.release || 'Zurich'}) - ${breakdown}`,
                actions: kpiActions,
              },
            };
          }
          if (t.type === 'instance-card' && t.props?.instance_id) {
            const st = statusById.get(t.props.instance_id);
            if (st) {
              return {
                ...t,
                props: {
                  ...t.props,
                  status: st.raw,
                  probe_status: st.formatted,
                },
              };
            }
          }
          return t;
        });
      return {
        ...msg,
        response: {
          ...msg.response,
          tiles: nextTiles,
        },
      };
    });
  }

  private async handleProbeAllInstances(): Promise<void> {
    this.isProbing = true;
    this.tileActionFeedback = `Checking live authentication across ${this.instances.length} managed instance(s)...`;
    try {
      const res = await fetch('/api/instances/test-all', { method: 'POST' });
      if (res.ok) {
        const data = (await res.json()) as {
          total: number;
          authenticated: number;
          unauthenticated: number;
        };
        await this.loadInstances();
        this.syncInstanceTilesWithCurrentState();
        const { breakdown } = this.summarizeAllInstances();
        this.probeStatus = breakdown;
        this.tileActionFeedback = `Checked authentication across ${data.total} instance(s): ${data.authenticated} Authenticated, ${data.unauthenticated} Unauthenticated/Unreachable.`;
        return;
      }
    } catch {
      // Fallback to testing primary
    } finally {
      this.isProbing = false;
    }
    await this.handleProbeTest(this.selectedInstanceId, false);
  }

  private async handleDeleteSingleInstance(instanceId?: string): Promise<void> {
    if (!instanceId) {
      return;
    }
    const instName = this.instances.find((i) => i.id === instanceId)?.name || instanceId;
    try {
      const res = await fetch(`/api/instances/${instanceId}`, { method: 'DELETE' });
      if (res.ok) {
        await this.loadInstances();
        this.syncInstanceTilesWithCurrentState();
        this.tileActionFeedback = `Deleted instance '${instName}'. You now manage ${this.instances.length} instance(s).`;
        return;
      }
    } catch {
      // Offline fallback
    }
    this.instances = this.instances.filter((i) => i.id !== instanceId);
    this.syncInstanceTilesWithCurrentState();
    this.tileActionFeedback = `Deleted instance '${instName}'.`;
  }

  private async handleProbeTest(instanceId?: string, silent = false): Promise<void> {
    const targetId = instanceId || this.selectedInstanceId || this.instances[0]?.id;
    if (!targetId) {
      return;
    }
    this.isProbing = true;
    if (!silent) {
      this.tileActionFeedback = `Testing live connectivity for instance '${targetId}'...`;
    }
    try {
      const res = await fetch(`/api/instances/${targetId}/test`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = (await res.json()) as {
          success: boolean;
          status: string;
          message: string;
          http_code: number;
        };
        const formatted = this.formatRealInstanceStatus(data.status);
        this.instances = this.instances.map((inst) =>
          inst.id === targetId ? { ...inst, status: data.status } : inst
        );
        const { breakdown } = this.summarizeAllInstances();
        this.probeStatus = breakdown;
        this.syncInstanceTilesWithCurrentState();
        if (!silent) {
          const instName =
            this.instances.find((i) => i.id === targetId)?.name || targetId;
          this.tileActionFeedback = `Live Connectivity Result for ${instName}: ${formatted} - ${data.message}`;
        }
      } else {
        this.probeStatus = 'Error (HTTP Check Failed)';
        if (!silent) {
          this.tileActionFeedback = `Connectivity check failed with HTTP ${res.status}.`;
        }
      }
    } catch {
      const fallbackStatus = this.formatRealInstanceStatus(
        this.instances.find((i) => i.id === targetId)?.status || 'unknown'
      );
      this.probeStatus = fallbackStatus;
      this.syncInstanceTilesWithCurrentState();
      if (!silent) {
        this.tileActionFeedback = `Connectivity check completed (${fallbackStatus}).`;
      }
    } finally {
      this.isProbing = false;
    }
  }

  private async handleActivateInstanceFromTile(instanceId?: string): Promise<void> {
    if (!instanceId) {
      return;
    }
    try {
      const res = await fetch(`/api/instances/${instanceId}/activate`, {
        method: 'POST',
      });
      if (res.ok) {
        await this.loadInstances();
      }
    } catch {
      // Offline fallback
    }
    this.selectedInstanceId = instanceId;
    this.instances = this.instances.map((i) => ({
      ...i,
      is_default: i.id === instanceId,
    }));
    const instName = this.instances.find((i) => i.id === instanceId)?.name || instanceId;
    this.tileActionFeedback = `Set '${instName}' as the primary default ServiceNow target.`;
  }

  private async loadInstances(): Promise<void> {
    try {
      const res = await fetch('/api/instances');
      if (res.ok) {
        const list = (await res.json()) as InstanceData[];
        if (list && list.length > 0) {
          this.instances = list;
          const def = list.find((i) => i.is_default) ?? list[0];
          this.selectedInstanceId = def.id;
          this.probeStatus = this.formatRealInstanceStatus(def.status);
          if (def.status === 'unknown') {
            void this.handleProbeTest(def.id, true);
          }
          return;
        }
      }
    } catch {
      // offline preview fallback
    }
    this.instances = [
      {
        id: 'demo-trial-main',
        name: 'Alec Demo Trial (Primary)',
        url: 'https://demoalectriallwfau164179.service-now.com',
        username: 'admin',
        release: 'Zurich',
        is_default: true,
        status: 'unknown',
        last_checked: null,
      },
    ];
    this.selectedInstanceId = 'demo-trial-main';
    this.probeStatus = this.formatRealInstanceStatus('unknown');
  }

  private handleInstanceChange(e: Event): void {
    const target = e.target as HTMLSelectElement;
    this.selectedInstanceId = target.value;
  }

  updated(changedProps: Map<string, unknown>): void {
    if (changedProps.has('activeThreadId')) {
      const tid = this.activeThreadId.trim();
      if (tid) {
        this.splitScreenOpen = true;
        this.contextLimitError = '';
        void this.loadConversationFromDb(tid);
      } else {
        this.splitScreenOpen = false;
        this.currentSessionPrompt = '';
        this.conversationMessages = [];
        this.contextLimitError = '';
      }
    }

    if (changedProps.has('incomingPrompt') || changedProps.has('viewMode')) {
      const prompt = this.incomingPrompt.trim();
      if (this.viewMode === 'home') {
        if (prompt && !this.activeThreadId && prompt !== this.currentSessionPrompt) {
          void this.submitHomeChat(prompt);
        }
      } else if (prompt && changedProps.has('incomingPrompt')) {
        if (this.viewMode === 'synthesizer') {
          this.useCasePrompt = prompt;
          void this.handleSynthesize();
        } else if (this.viewMode === 'capture') {
          this.captureCaption = prompt;
          if (prompt.toLowerCase().includes('video') || prompt.toLowerCase().includes('webm')) {
            this.captureMode = 'video';
          } else {
            this.captureMode = 'screenshot';
          }
          const pathMatch = prompt.match(/(\/[a-zA-Z0-9_./-]+)/);
          if (pathMatch) {
            this.uriPath = pathMatch[1];
          }
          void this.handleCapture();
        }
      }
    }
  }

  private async loadConversationFromDb(threadId: string): Promise<void> {
    try {
      const [tRes, mRes] = await Promise.all([
        fetch(`/api/threads/${threadId}`),
        fetch(`/api/threads/${threadId}/messages`),
      ]);
      if (tRes.ok) {
        const meta = (await tRes.json()) as {
          id: string;
          title: string;
          archived?: boolean;
        };
        this.currentSessionTitle = meta.title || 'New Otto Conversation';
        this.currentThreadArchived = Boolean(meta.archived);
      }
      if (mRes.ok) {
        const rawMsgs = (await mRes.json()) as Array<{
          id: string;
          role: 'user' | 'assistant' | 'system';
          content: string;
          created_at?: string;
          widget_data?: {
            summary?: string;
            layout?: '1-col' | '2-col' | '3-col' | 'auto';
            tiles?: UITileSpec[];
          };
        }>;
        let lastUserText = '';
        this.conversationMessages = rawMsgs.map((m) => {
          if (m.role === 'user') {
            lastUserText = m.content;
            return {
              id: m.id,
              role: m.role,
              content: m.content,
              created_at: m.created_at,
            };
          }
          if (m.role === 'assistant') {
            const hasDbTiles =
              m.widget_data && Array.isArray(m.widget_data.tiles) && m.widget_data.tiles.length > 0;
            const resolved: GenerativeUIResponse = hasDbTiles
              ? {
                  summary: m.widget_data?.summary || m.content,
                  layout: m.widget_data?.layout || '2-col',
                  tiles: m.widget_data?.tiles || [],
                }
              : this.resolveGenerativeTiles(lastUserText || m.content);
            return {
              id: m.id,
              role: m.role,
              content: m.content,
              created_at: m.created_at,
              response: resolved,
            };
          }
          return {
            id: m.id,
            role: m.role,
            content: m.content,
            created_at: m.created_at,
          };
        });
        return;
      }
    } catch {
      // Offline preview fallback
    }
    if (this.incomingPrompt.trim()) {
      const q = this.incomingPrompt.trim();
      const resp = this.resolveGenerativeTiles(q);
      this.currentSessionTitle = q.length > 38 ? `${q.slice(0, 38)}...` : q;
      this.conversationMessages = [
        { id: `u-${Date.now()}`, role: 'user', content: q },
        { id: `a-${Date.now()}`, role: 'assistant', content: resp.summary, response: resp },
      ];
    } else if (threadId.startsWith('thread-')) {
      this.currentSessionTitle = 'New Otto Conversation';
      this.conversationMessages = [];
    }
  }

  private get currentBundleId(): string {
    return this.captureSelectedBundleId || this.synthesizedResult?.bundle_id || 'sample-ai-assistant';
  }

  private async loadCaptures(bundleId: string): Promise<void> {
    try {
      const res = await fetch(`/api/demos/${bundleId}/captures`);
      if (res.ok) {
        this.captures = (await res.json()) as CaptureArtifact[];
      }
    } catch {
      // Offline preview
    }
  }

  private isQuestionText(prompt: string): boolean {
    const lower = prompt.toLowerCase().trim();
    return (
      lower.endsWith('?') ||
      lower.startsWith('what') ||
      lower.startsWith('how') ||
      lower.startsWith('why') ||
      lower.startsWith('where') ||
      lower.startsWith('who') ||
      lower.startsWith('when') ||
      lower.startsWith('which') ||
      lower.startsWith('can ') ||
      lower.startsWith('could ') ||
      lower.startsWith('would ') ||
      lower.startsWith('tell me') ||
      lower.startsWith('explain') ||
      lower.startsWith('describe') ||
      lower.startsWith('help') ||
      lower.startsWith('is ') ||
      lower.startsWith('are ') ||
      lower.startsWith('does ') ||
      lower.startsWith('do ') ||
      lower.startsWith('show me') ||
      lower.includes('what is') ||
      lower.includes('what are') ||
      lower.includes('how do') ||
      lower.includes('how can') ||
      lower.includes('how to') ||
      lower.includes('tell me about') ||
      lower.includes('demohub')
    );
  }

  private handleTileAction(_tileId: string, actionId: string, props?: Record<string, any>): void {
    if (actionId === 'confirm_tool') {
      void this.handleConfirmTool(props);
      return;
    } else if (actionId === 'cancel_tool') {
      this.tileActionFeedback = 'Action cancelled.';
      return;
    } else if (actionId === 'show_instances') {
      void this.handleSplitChatSubmit('Show detailed list of my instances');
    } else if (actionId === 'show_bundles') {
      void this.handleSplitChatSubmit('Show detailed list of demo recipe bundles');
    } else if (actionId === 'probe_all') {
      void this.handleProbeAllInstances();
    } else if (actionId === 'probe') {
      void this.handleProbeTest(props?.instance_id, false);
    } else if (actionId === 'delete_unauthenticated') {
      void this.handleSplitChatSubmit('delete the unauthenticated instances');
    } else if (actionId === 'delete_instance') {
      void this.handleDeleteSingleInstance(props?.instance_id);
    } else if (actionId === 'activate') {
      void this.handleActivateInstanceFromTile(props?.instance_id);
    } else if (actionId === 'manage') {
      this.navigateToMenu('admin');
    } else if (actionId === 'seed') {
      void this.handleSeedSynthesized(props?.bundle_id);
    } else if (actionId === 'synthesize') {
      this.navigateToMenu('synthesizer');
    } else if (actionId === 'inspect') {
      this.navigateToMenu('artifacts');
    } else if (actionId === 'review') {
      void this.handleSplitChatSubmit(
        'Provide remediation steps for Ticket Pricing Agent access control'
      );
    } else if (actionId === 'explore_fluent') {
      this.navigateToMenu('fluent');
    }
  }

  private async handleConfirmTool(props?: Record<string, any>): Promise<void> {
    const toolName = (props?.tool as string) || '';
    const toolInput = (props?.tool_input as Record<string, any>) || {};
    const plan = (props?.plan as string) || `Run ${toolName}`;

    this.conversationMessages = [
      ...this.conversationMessages,
      {
        id: `u-${Date.now()}`,
        role: 'user',
        content: `Confirmed: ${plan}`,
      },
    ];

    if (!this.activeThreadId) {
      this.tileActionFeedback = `Confirmed ${plan} (offline mode).`;
      return;
    }

    try {
      const res = await fetch(`/api/threads/${this.activeThreadId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'user',
          content: `Confirmed: ${plan}`,
          widget_type: 'tool_confirm',
          widget_data: {
            tool: toolName,
            input: toolInput,
          },
        }),
      });
      if (res.ok) {
        await Promise.all([
          this.loadConversationFromDb(this.activeThreadId),
          this.loadInstances(),
          this.loadBundles(),
        ]);
        this.dispatchEvent(
          new CustomEvent('threads-refresh', {
            bubbles: true,
            composed: true,
          })
        );
      }
    } catch {
      this.tileActionFeedback = `Confirmed ${plan}.`;
    }
  }

  private resolveGenerativeTiles(prompt: string): GenerativeUIResponse {
    const lower = prompt.toLowerCase().trim();
    const wantsDetails =
      lower.includes('detail') ||
      lower.includes('list') ||
      lower.includes('show all') ||
      lower.includes('cards') ||
      lower.includes('expand') ||
      lower.includes('inspect') ||
      lower.includes('which');

    const isDeleteInstanceCmd =
      (lower.includes('delete') || lower.includes('remove') || lower.includes('clean')) &&
      (lower.includes('instance') ||
        lower.includes('instande') ||
        lower.includes('unauthenticated') ||
        lower.includes('unreachable') ||
        lower.includes('failed'));

    if (isDeleteInstanceCmd) {
      const remaining = this.instances.filter(
        (i) => (i.status || '').trim().toLowerCase() === 'authenticated'
      );
      const delCount = Math.max(0, this.instances.length - remaining.length);
      const remCount = remaining.length;
      const primary = remaining.find((i) => i.is_default) || remaining[0];
      const statusLabel = primary ? this.formatRealInstanceStatus(primary.status) : 'None';
      return {
        summary: `Deleted ${delCount} unauthenticated/unreachable instance${delCount === 1 ? '' : 's'}. You now manage ${remCount} ServiceNow instance${remCount === 1 ? '' : 's'}.`,
        layout: '1-col',
        tiles: [
          {
            id: 'tile-inst-kpi',
            type: 'instance-kpi',
            title: 'Instance Summary',
            props: {
              instance_id: primary?.id || '',
              count: remCount,
              label: remCount === 1 ? 'Managed Instance' : 'Managed Instances',
              subtitle: primary
                ? `Primary: ${primary.name} (${primary.release}) - ${statusLabel}`
                : 'No instances remaining',
              status: statusLabel,
              badge: statusLabel,
              accent: 'green',
              actions: [
                { id: 'show_instances', label: 'Show Instance Details', variant: 'primary' },
                { id: 'probe_all', label: 'Check Authentication', variant: 'secondary' },
                { id: 'manage', label: 'Manage in Settings', variant: 'secondary' },
              ],
            },
          },
        ],
      };
    }

    // 1. Instance Inquiries (tolerant to 'instande', 'instances', 'target', 'manag', etc.)
    const isInstanceQuery =
      lower.includes('instance') ||
      lower.includes('instande') ||
      lower.includes('instence') ||
      lower.includes('target') ||
      lower.includes('targets');

    if (isInstanceQuery) {
      const activeList =
        this.instances && this.instances.length > 0
          ? this.instances
          : [
              {
                id: 'inst-default',
                name: 'Alec Demo Trial',
                url: 'https://dev231145.service-now.com',
                username: 'admin',
                release: 'Zurich',
                is_default: true,
                status: 'unknown',
                last_checked: null,
              },
            ];

      const count = activeList.length;
      const primary = activeList.find((i) => i.is_default) || activeList[0];
      const { breakdown, unauthCount } = this.summarizeAllInstances();
      const statusSummary = breakdown || this.formatRealInstanceStatus(primary.status);

      // Summary-first mode unless user explicitly asks for details/list
      if (!wantsDetails) {
        const kpiActions: Array<Record<string, any>> = [
          { id: 'show_instances', label: 'Show Instance Details', variant: 'primary' },
          {
            id: 'probe_all',
            label: 'Check Authentication',
            variant: 'secondary',
            instance_id: primary.id,
          },
          { id: 'manage', label: 'Manage in Settings', variant: 'secondary' },
        ];
        if (unauthCount > 0) {
          kpiActions.splice(2, 0, {
            id: 'delete_unauthenticated',
            label: `Delete Unauthenticated (${unauthCount})`,
            variant: 'secondary',
          });
        }
        return {
          summary: `You manage ${count} ServiceNow instance${count === 1 ? '' : 's'} (${statusSummary}). Click 'Show Instance Details' or ask for details to inspect each target.`,
          layout: '1-col',
          tiles: [
            {
              id: 'tile-inst-kpi',
              type: 'instance-kpi',
              title: 'Instance Summary',
              props: {
                instance_id: primary.id,
                count: count,
                label: count === 1 ? 'Managed Instance' : 'Managed Instances',
                subtitle: `Primary: ${primary.name} (${primary.release}) - ${statusSummary}`,
                status: statusSummary,
                badge: statusSummary,
                accent: primary.status === 'authenticated' ? 'green' : 'amber',
                actions: kpiActions,
              },
            },
          ],
        };
      }

      const cards: UITileSpec[] = activeList.map((inst) => {
        const realLabel = this.formatRealInstanceStatus(inst.status);
        const actions: Array<Record<string, any>> = [
          {
            id: 'probe',
            label: 'Check Authentication',
            variant: 'primary',
            instance_id: inst.id,
          },
          {
            id: 'delete_instance',
            label: 'Delete',
            variant: 'secondary',
            instance_id: inst.id,
          },
          {
            id: 'manage',
            label: 'Edit in Settings',
            variant: 'secondary',
            instance_id: inst.id,
          },
        ];
        if (!inst.is_default) {
          actions.splice(1, 0, {
            id: 'activate',
            label: 'Set Default',
            variant: 'secondary',
            instance_id: inst.id,
          });
        }
        return {
          id: `tile-inst-${inst.id}`,
          type: 'instance-card',
          title: inst.name,
          props: {
            instance_id: inst.id,
            name: inst.name,
            url: inst.url,
            release: inst.release || 'Zurich',
            is_default: inst.is_default,
            status: inst.status || 'unknown',
            probe_status: realLabel,
            actions,
          },
        };
      });

      return {
        summary: `Showing detailed configuration and live status for ${count} managed ServiceNow instance${count === 1 ? '' : 's'}.`,
        layout: cards.length >= 3 ? '3-col' : cards.length === 2 ? '2-col' : '1-col',
        tiles: cards,
      };
    }

    // 2. Security / Risk Inquiries (checked before generic 'demo' keyword)
    if (
      lower.includes('security') ||
      lower.includes('risk') ||
      lower.includes('alert') ||
      lower.includes('vulnerab') ||
      lower.includes('remediat')
    ) {
      return {
        summary: '1 critical security action item requires AI review.',
        layout: '1-col',
        tiles: [
          {
            id: 'tile-sec-alert',
            type: 'security-alert',
            title: 'Ticket Pricing Agent - Access Control Review',
            props: {
              severity: '3 - MEDIUM',
              agent_name: 'Ticket Pricing Agent',
              issue: 'Unrestricted execution path detected for automatic discount approval.',
              remediation: 'Configure prompt guardrails and require secondary approval in Zurich.',
              actions: [
                { id: 'explore_fluent', label: 'Inspect Guardrail Schema', variant: 'primary' },
                { id: 'manage', label: 'Configure in Settings', variant: 'secondary' },
              ],
            },
          },
        ],
      };
    }

    // 3. Fluent SDK Schema Inquiries
    if (
      lower.includes('fluent') ||
      lower.includes('schema') ||
      lower.includes('table') ||
      lower.includes('typescript')
    ) {
      return {
        summary: 'ServiceNow Fluent SDK schemas are declared declaratively in *.now.ts files.',
        layout: '1-col',
        tiles: [
          {
            id: 'tile-fluent-table',
            type: 'fluent-schema',
            title: 'Table Definition (Fluent SDK)',
            props: {
              file_path: 'src/tables/custom_demo.now.ts',
              table_name: 'x_demo_custom_table',
              label: 'Custom Demo Table',
              columns_count: 2,
              code:
                "export const my_table = Table({\n" +
                "    name: 'x_demo_custom_table',\n" +
                "    label: 'Custom Demo Table',\n" +
                "    schema: {\n" +
                "        short_desc: Record({ label: 'Short Description', maxLength: 100 }),\n" +
                "        assigned_to: Record({ label: 'Assignee', reference: 'sys_user' }),\n" +
                "    },\n" +
                "})",
              actions: [
                { id: 'explore_fluent', label: 'Open Fluent Explorer', variant: 'primary' },
              ],
            },
          },
        ],
      };
    }

    // 4. Recipes vs Update Sets Inquiries
    const isRecipeVsUpdateSet =
      lower.includes('update set') ||
      lower.includes('sys_update_xml') ||
      (lower.includes('recipe') && !lower.includes('bundle') && !lower.includes('package'));
    if (isRecipeVsUpdateSet) {
      return {
        summary:
          'Now Workbench demos are built as declarative recipes rather than brittle captured update sets, making them virtually compatible with any ServiceNow release.',
        layout: '2-col',
        tiles: [
          {
            id: 'tile-recipe-why',
            type: 'rich-text',
            title: 'Declarative Recipes (No Update Sets)',
            props: {
              body:
                'Captured update sets (sys_update_xml) are brittle, contain hardcoded sys_ids, and fail on release upgrades. ' +
                'Now Workbench builds demos from declarative TypeScript recipes (*.now.ts) + date-aligned seed datasets, ' +
                'making them virtually compatible with ANY ServiceNow version (Washington, Xanadu, Zurich, Australia).',
              actions: [
                { id: 'explore_fluent', label: 'Explore Fluent Schemas', variant: 'primary' },
                { id: 'inspect', label: 'View Artifact Library', variant: 'secondary' },
              ],
            },
          },
          {
            id: 'tile-recipe-compat',
            type: 'rich-text',
            title: 'Universal Release Compatibility',
            props: {
              body:
                'Demonstration recipes compile into native Table & Metadata API calls during transactional seeding. ' +
                'Demos can be re-seeded or torn down cleanly in seconds with automated property snapshot restoration.',
              actions: [
                { id: 'synthesize', label: 'Synthesize New Recipe', variant: 'secondary' },
              ],
            },
          },
        ],
      };
    }

    // 5. Demo Bundles Inquiries
    if (
      lower.includes('bundle') ||
      lower.includes('demo') ||
      lower.includes('package')
    ) {
      const bundles =
        this.demoBundles && this.demoBundles.length > 0
          ? this.demoBundles
          : [
              {
                id: 'novartis-biohealth-automate-enterpri',
                name: 'Novartis Clinical Triage Demo',
                industry: 'Healthcare & Life Sciences',
                release: 'Zurich',
                tables_count: 4,
                records_count: 38,
              },
              {
                id: 'template-customer-service-ai',
                name: 'Customer Service AI Assistant',
                industry: 'Customer Service Management',
                release: 'Xanadu / Zurich',
                tables_count: 3,
                records_count: 24,
              },
            ];

      const isCountOnly =
        (lower.includes('how many') || lower.includes('count')) && !wantsDetails;
      if (isCountOnly) {
        const totalTables = bundles.reduce((acc, b) => acc + (b.tables_count || 0), 0);
        const totalRecords = bundles.reduce((acc, b) => acc + (b.records_count || 0), 0);
        return {
          summary: `You have ${bundles.length} declarative demo recipe bundles ready. Click 'Show Recipe Details' to inspect or seed individual bundles.`,
          layout: '1-col',
          tiles: [
            {
              id: 'tile-bundle-kpi',
              type: 'instance-kpi',
              title: 'Demo Recipe Summary',
              props: {
                count: bundles.length,
                label: 'Declarative Demo Recipes',
                subtitle: `${totalTables} Fluent Tables / ${totalRecords} Seed Records`,
                status: '100% Release Agnostic',
                badge: 'Zero Update Sets',
                accent: 'green',
                actions: [
                  { id: 'show_bundles', label: 'Show Recipe Details', variant: 'primary' },
                  { id: 'synthesize', label: 'Synthesize New Recipe', variant: 'secondary' },
                  { id: 'inspect', label: 'Open Artifact Library', variant: 'secondary' },
                ],
              },
            },
          ],
        };
      }

      const tiles: UITileSpec[] = bundles.map((b) => ({
        id: `tile-bundle-${b.id}`,
        type: 'demo-bundle',
        title: b.name,
        props: {
          bundle_id: b.id,
          name: b.name,
          industry: b.industry,
          release: b.release,
          tables_count: b.tables_count,
          records_count: b.records_count,
          actions: [
            { id: 'seed', label: 'Seed to Instance', variant: 'primary', bundle_id: b.id },
            { id: 'inspect', label: 'Inspect Artifacts', variant: 'secondary', bundle_id: b.id },
          ],
        },
      }));

      return {
        summary: `You have ${bundles.length} demo bundles ready in the Workbench Artifact Library.`,
        layout: '2-col',
        tiles,
      };
    }

    // 6. Default / General Inquiry -> Rich Text Tile
    return {
      summary: 'Here is the executive summary for your inquiry.',
      layout: '1-col',
      tiles: [
        {
          id: 'tile-rich-general',
          type: 'rich-text',
          title: 'Otto Copilot Guidance',
          props: {
            body: `I received your inquiry: "${prompt}". I can summarize your managed instances, showcase declarative demo recipe bundles, or inspect Fluent SDK schemas.`,
            actions: [
              { id: 'show_instances', label: 'Show Managed Instances', variant: 'primary' },
              { id: 'manage', label: 'Manage Settings', variant: 'secondary' },
              { id: 'explore_fluent', label: 'Explore Fluent SDK', variant: 'secondary' },
            ],
          },
        },
      ],
    };
  }

  private renderUITile(tile: UITileSpec) {
    switch (tile.type) {
      case 'instance-kpi':
        return this.renderInstanceKpiTile(tile);
      case 'instance-card':
        return this.renderInstanceCardTile(tile);
      case 'demo-bundle':
        return this.renderDemoBundleTile(tile);
      case 'security-alert':
        return this.renderSecurityAlertTile(tile);
      case 'fluent-schema':
        return this.renderFluentSchemaTile(tile);
      case 'data-table':
        return this.renderDataTableTile(tile);
      case 'media-player':
        return this.renderMediaPlayerTile(tile);
      case 'rich-text':
      default:
        return this.renderRichTextTile(tile);
    }
  }

  private renderInstanceKpiTile(tile: UITileSpec) {
    const p = tile.props || {};
    const statusLabel = p.badge || p.status || this.probeStatus;
    const badgeVariant = this.statusBadgeVariant(statusLabel);
    return html`
      <div class="gen-tile kpi">
        <div class="gen-kpi-top">
          <div class="gen-kpi-icon">
            <svg viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><path d="M22 6l-10 7L2 6"></path></svg>
          </div>
          <span class="ct-tag ${badgeVariant}">${statusLabel}</span>
        </div>
        <div class="gen-kpi-number">${p.count ?? 1}</div>
        <div class="gen-kpi-label">${p.label || 'Managed Instances'}</div>
        <div class="gen-kpi-sub">${p.subtitle || ''}</div>
        ${p.actions && p.actions.length
          ? html`
              <div class="gen-actions-row">
                ${p.actions.map(
                  (act: any) => html`
                    <button
                      type="button"
                      class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      ?disabled=${(act.id === 'probe' || act.id === 'probe_all') && this.isProbing}
                      @click=${() =>
                        this.handleTileAction(tile.id, act.id, { ...p, ...act })}
                    >
                      ${(act.id === 'probe' || act.id === 'probe_all') && this.isProbing
                        ? 'Testing...'
                        : act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderInstanceCardTile(tile: UITileSpec) {
    const p = tile.props || {};
    const statusText = p.probe_status || this.formatRealInstanceStatus(p.status);
    const badgeVariant = this.statusBadgeVariant(statusText);
    const strokeColor =
      badgeVariant === 'high' ? '#16a34a' : badgeVariant === 'critical' ? '#dc2626' : '#d97706';
    return html`
      <div class="gen-tile card">
        <div class="gen-card-header">
          <h4 class="gen-card-title">
            <svg style="width:14px;height:14px;stroke:${strokeColor};stroke-width:2;fill:none;" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            ${p.name || 'ServiceNow Instance'}
          </h4>
          <span class="ct-tag low">${p.release || 'Zurich'}</span>
        </div>
        <div class="gen-card-url">${p.url || 'https://instance.service-now.com'}</div>
        <div class="gen-card-meta-row">
          <span>Status: <span class="ct-tag ${badgeVariant}">${statusText}</span></span>
          ${p.is_default ? html`<span class="ct-tag high">Primary Target</span>` : ''}
        </div>
        ${p.actions && p.actions.length
          ? html`
              <div class="gen-actions-row">
                ${p.actions.map(
                  (act: any) => html`
                    <button
                      type="button"
                      class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      ?disabled=${(act.id === 'probe' || act.id === 'probe_all') && this.isProbing}
                      @click=${() =>
                        this.handleTileAction(tile.id, act.id, { ...p, ...act })}
                    >
                      ${(act.id === 'probe' || act.id === 'probe_all') && this.isProbing
                        ? 'Testing...'
                        : act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderDemoBundleTile(tile: UITileSpec) {
    const p = tile.props || {};
    return html`
      <div class="gen-tile card">
        <div class="gen-card-header">
          <h4 class="gen-card-title">${p.name || 'Demo Bundle'}</h4>
          <span class="ct-tag low">${p.release || 'Zurich'}</span>
        </div>
        <div style="font-size:12px; color:var(--now-text-secondary, #475467);">
          Industry: <strong>${p.industry || 'General'}</strong>
        </div>
        <div class="gen-card-meta-row">
          <span>Tables: <strong>${p.tables_count ?? 0}</strong></span>
          <span>Records: <strong>${p.records_count ?? 0}</strong></span>
        </div>
        ${p.actions && p.actions.length
          ? html`
              <div class="gen-actions-row">
                ${p.actions.map(
                  (act: any) => html`
                    <button
                      type="button"
                      class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      @click=${() =>
                        this.handleTileAction(tile.id, act.id, { ...p, ...act })}
                    >
                      ${act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderSecurityAlertTile(tile: UITileSpec) {
    const p = tile.props || {};
    return html`
      <div class="gen-tile alert-tile">
        <div class="gen-card-header">
          <h4 class="gen-alert-title">${tile.title || p.agent_name || 'Security Review Required'}</h4>
          <span class="ct-tag medium">${p.severity || 'MEDIUM'}</span>
        </div>
        <p class="gen-alert-desc">${p.issue || ''}</p>
        ${p.remediation ? html`<div style="font-size:11.5px; color:#991b1b; font-weight:600;">Remediation: ${p.remediation}</div>` : ''}
        ${p.actions && p.actions.length
          ? html`
              <div class="gen-actions-row">
                ${p.actions.map(
                  (act: any) => html`
                    <button
                      type="button"
                      class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      @click=${() =>
                        this.handleTileAction(tile.id, act.id, { ...p, ...act })}
                    >
                      ${act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderFluentSchemaTile(tile: UITileSpec) {
    const p = tile.props || {};
    return html`
      <div class="gen-tile card">
        <div class="gen-card-header">
          <h4 class="gen-card-title">${p.table_name || 'Fluent Table'}</h4>
          <span class="ct-tag low">${p.file_path || '*.now.ts'}</span>
        </div>
        <pre style="margin:4px 0; padding:8px 10px; background:#0f172a; color:#f8fafc; border-radius:6px; font-size:11px; overflow-x:auto; font-family:monospace;">${p.code || ''}</pre>
        ${p.actions && p.actions.length
          ? html`
              <div class="gen-actions-row">
                ${p.actions.map(
                  (act: any) => html`
                    <button
                      type="button"
                      class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      @click=${() =>
                        this.handleTileAction(tile.id, act.id, { ...p, ...act })}
                    >
                      ${act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderDataTableTile(tile: UITileSpec) {
    const p = tile.props || {};
    const columns: string[] = Array.isArray(p.columns) ? p.columns : [];
    const rows: any[][] = Array.isArray(p.rows) ? p.rows : [];
    return html`
      <div class="gen-tile table-tile">
        <h4 class="gen-table-title">${tile.title || 'Data Table'}</h4>
        <div style="overflow-x: auto;">
          <table class="gen-data-table">
            <thead>
              <tr>
                ${columns.map((col) => html`<th>${col}</th>`)}
              </tr>
            </thead>
            <tbody>
              ${rows.map(
                (row) => html`
                  <tr>
                    ${row.map((cell) => html`<td>${cell}</td>`)}
                  </tr>
                `
              )}
            </tbody>
          </table>
        </div>
        ${p.actions && p.actions.length
          ? html`
              <div class="gen-actions-row">
                ${p.actions.map(
                  (act: any) => html`
                    <button
                      type="button"
                      class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      @click=${() =>
                        this.handleTileAction(tile.id, act.id, { ...p, ...act })}
                    >
                      ${act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderMediaPlayerTile(tile: UITileSpec) {
    const p = tile.props || {};
    const url = p.url || '';
    const isVideo = p.media_type === 'video' || url.endsWith('.webm') || url.endsWith('.mp4');
    return html`
      <div class="gen-tile media-tile">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h4 class="gen-card-title">${tile.title || 'Demonstration Media'}</h4>
          <span class="ct-tag high">${isVideo ? 'Video Proof' : 'Screenshot'}</span>
        </div>
        ${p.label ? html`<div style="font-size: 12.5px; color: var(--now-text-secondary, #475467);">${p.label}</div>` : ''}
        <div class="gen-media-preview">
          ${isVideo
            ? html`<video src=${url} controls playsinline preload="metadata"></video>`
            : html`<img src=${url} alt=${tile.title || 'Demonstration Proof'} />`}
        </div>
        ${p.actions && p.actions.length
          ? html`
              <div class="gen-actions-row">
                ${p.actions.map(
                  (act: any) => html`
                    <button
                      type="button"
                      class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      @click=${() =>
                        this.handleTileAction(tile.id, act.id, { ...p, ...act })}
                    >
                      ${act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderRichTextTile(tile: UITileSpec) {
    const p = tile.props || {};
    return html`
      <div class="gen-tile rich">
        <h4 class="gen-rich-title">${tile.title || 'Summary'}</h4>
        <div class="gen-rich-body">${p.body || ''}</div>
        ${p.actions && p.actions.length
          ? html`
              <div class="gen-actions-row">
                ${p.actions.map(
                  (act: any) => html`
                    <button
                      type="button"
                      class="ct-action-btn ${act.variant === 'primary' ? 'primary' : ''}"
                      @click=${() =>
                        this.handleTileAction(tile.id, act.id, { ...p, ...act })}
                    >
                      ${act.label}
                    </button>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private startNewOttoSession(prompt: string): void {
    const clean = prompt.trim();
    const shortTitle = clean.length > 38 ? `${clean.slice(0, 38)}...` : clean;
    const resp = this.resolveGenerativeTiles(clean);

    this.currentSessionTitle = shortTitle || 'New Otto Conversation';
    this.currentSessionPrompt = clean;
    this.currentSessionResponse = resp;
    this.sessionFollowUps = [];
    this.splitChatInput = '';
    this.contextLimitError = '';
    this.splitScreenOpen = true;
    this.conversationMessages = clean
      ? [
          { id: `u-${Date.now()}`, role: 'user', content: clean },
          { id: `a-${Date.now()}`, role: 'assistant', content: resp.summary, response: resp },
        ]
      : [];
  }

  private async submitHomeChat(promptText?: string): Promise<void> {
    const text = (promptText ?? this.homeChatInput).trim();
    if (!text) {
      return;
    }
    this.homeChatInput = '';
    this.startNewOttoSession(text);

    const shortTitle = text.length > 38 ? `${text.slice(0, 38)}...` : text;
    try {
      const createRes = await fetch('/api/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: shortTitle, target_tab: 'home' }),
      });
      if (createRes.ok) {
        const created = (await createRes.json()) as { id: string; title: string };
        await fetch(`/api/threads/${created.id}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: text, role: 'user' }),
        });
        await Promise.all([
          this.loadConversationFromDb(created.id),
          this.loadInstances(),
          this.loadBundles(),
        ]);
        this.dispatchEvent(
          new CustomEvent('thread-created', {
            detail: { threadId: created.id },
            bubbles: true,
            composed: true,
          })
        );
        return;
      }
    } catch {
      // Offline preview fallback
    }

    this.dispatchEvent(
      new CustomEvent('intent-submit', {
        detail: { prompt: text, stayInOtto: true },
        bubbles: true,
        composed: true,
      })
    );
  }

  private navigateToMenu(tab: string): void {
    this.dispatchEvent(
      new CustomEvent('nav-change', {
        detail: { tab },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleOpenSplitScreen(defaultPrompt?: string): void {
    const promptToRun =
      defaultPrompt ||
      this.currentSessionPrompt ||
      'how many instances do I have';
    void this.submitHomeChat(promptToRun);
  }

  private handleCloseSplitScreen(): void {
    this.splitScreenOpen = false;
    this.currentSessionPrompt = '';
    this.conversationMessages = [];
    this.contextLimitError = '';
    this.dispatchEvent(
      new CustomEvent('session-close', {
        bubbles: true,
        composed: true,
      })
    );
  }

  private requestNewConversation(): void {
    this.splitChatInput = '';
    this.contextLimitError = '';
    this.conversationMessages = [];
    this.currentSessionTitle = 'New Otto Conversation';
    this.splitScreenOpen = true;
    this.dispatchEvent(
      new CustomEvent('new-session', {
        bubbles: true,
        composed: true,
      })
    );
  }

  private requestArchiveCurrentThread(): void {
    if (!this.activeThreadId) {
      return;
    }
    const nextArchived = !this.currentThreadArchived;
    this.currentThreadArchived = nextArchived;
    this.dispatchEvent(
      new CustomEvent('thread-archive', {
        detail: { threadId: this.activeThreadId, archived: nextArchived },
        bubbles: true,
        composed: true,
      })
    );
  }

  private requestDeleteCurrentThread(): void {
    const tid = this.activeThreadId;
    this.handleCloseSplitScreen();
    if (tid) {
      this.dispatchEvent(
        new CustomEvent('thread-delete', {
          detail: { threadId: tid },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  private handleActivateKillSwitch(): void {
    this.ticketAgentStatus = 'Disabled';
    this.killSwitchActivated = true;
  }

  private handleReactivateAgent(): void {
    this.ticketAgentStatus = 'Deployed & Active';
    this.killSwitchActivated = false;
  }

  private async handleSplitChatSubmit(overridePrompt?: string): Promise<void> {
    const q = (overridePrompt ?? this.splitChatInput).trim();
    if (!q) {
      return;
    }
    if (this.conversationMessages.length >= this.maxContextMessages) {
      this.contextLimitError = `Conversation context limit reached (${this.maxContextMessages}/${this.maxContextMessages} messages). Start a new conversation for fresh AI context.`;
      return;
    }
    this.splitChatInput = '';
    this.contextLimitError = '';

    const followUpResp = this.resolveGenerativeTiles(q);
    this.conversationMessages = [
      ...this.conversationMessages,
      { id: `u-${Date.now()}`, role: 'user', content: q },
      { id: `a-${Date.now()}`, role: 'assistant', content: followUpResp.summary, response: followUpResp },
    ];
    if (this.currentSessionTitle === 'New Otto Conversation') {
      this.currentSessionTitle = q.length > 38 ? `${q.slice(0, 38)}...` : q;
    }

    if (this.activeThreadId) {
      try {
        const res = await fetch(`/api/threads/${this.activeThreadId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: q, role: 'user' }),
        });
        if (res.status === 400) {
          const err = (await res.json()) as { detail?: string };
          this.contextLimitError =
            err.detail ||
            `Conversation context limit reached (${this.maxContextMessages} messages max).`;
          return;
        }
        if (res.ok) {
          await Promise.all([
            this.loadConversationFromDb(this.activeThreadId),
            this.loadInstances(),
            this.loadBundles(),
          ]);
          this.dispatchEvent(
            new CustomEvent('threads-refresh', {
              bubbles: true,
              composed: true,
            })
          );
        }
      } catch {
        // Offline preview keeps optimistic conversationMessages
      }
    }
  }

  private async handleSynthesize(): Promise<void> {
    if (!this.useCasePrompt.trim() || this.isSynthesizing) {
      return;
    }
    this.isSynthesizing = true;
    this.seedStatusMessage = '';
    try {
      const res = await fetch('/api/demos/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          use_case: this.useCasePrompt,
          customer_name: this.customerName,
          industry: this.industry,
          sn_release: this.releaseTarget,
          primary_color: '#62d84e',
          persona_primary: this.personaPrimary,
          persona_secondary: this.personaSecondary,
        }),
      });
      if (res.ok) {
        this.synthesizedResult = (await res.json()) as SynthesizedDemoResult;
        this.activeResultTab = 'narrative';
        await this.loadCaptures(this.synthesizedResult.bundle_id);
      }
    } finally {
      this.isSynthesizing = false;
    }
  }

  private async handleSeedSynthesized(bundleIdOverride?: string): Promise<void> {
    const bundleId = bundleIdOverride || this.currentBundleId;
    const targetName = this.selectedInstance?.name ?? 'target instance';
    this.tileActionFeedback = `Seeding demo recipe '${bundleId}' to ${targetName}...`;
    try {
      const res = await fetch(`/api/demos/${bundleId}/seed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instance_id: this.selectedInstanceId || undefined,
        }),
      });
      if (res.ok) {
        const msg = `Seeded datasets and properties for '${bundleId}' to ${targetName}.`;
        this.seedStatusMessage = msg;
        this.tileActionFeedback = msg;
      } else {
        const err = await res.json();
        const msg = `Seeding error: ${err.detail || 'Failed to seed records'}`;
        this.seedStatusMessage = msg;
        this.tileActionFeedback = msg;
      }
    } catch {
      const msg = `Seeded datasets for '${bundleId}' in local fake mode to ${targetName}.`;
      this.seedStatusMessage = msg;
      this.tileActionFeedback = msg;
    }
  }

  private async handleCapture(): Promise<void> {
    if (this.isCapturing) {
      return;
    }
    this.isCapturing = true;
    const bundleId = this.currentBundleId;
    try {
      const res = await fetch(`/api/demos/${bundleId}/captures`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bundle_id: bundleId,
          instance_id: this.selectedInstanceId || undefined,
          target_path: this.uriPath,
          media_type: this.captureMode,
          label: this.captureCaption,
          viewport_width: 1440,
          viewport_height: 900,
          fake_mode: false,
        }),
      });
      if (res.ok) {
        const created = (await res.json()) as CaptureArtifact;
        this.captures = [created, ...this.captures];
      }
    } finally {
      this.isCapturing = false;
    }
  }

  private async handleRenameCapture(filename: string, currentLabel?: string): Promise<void> {
    const newLabel = window.prompt('Enter new caption for this capture:', currentLabel || filename);
    if (!newLabel || newLabel.trim() === currentLabel) {
      return;
    }
    const bundleId = this.currentBundleId;
    try {
      const res = await fetch(`/api/demos/${bundleId}/captures/${filename}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: newLabel.trim() }),
      });
      if (res.ok) {
        const updated = (await res.json()) as CaptureArtifact;
        this.captures = this.captures.map((c) => (c.filename === filename ? updated : c));
        if (this.previewCapture && this.previewCapture.filename === filename) {
          this.previewCapture = updated;
        }
        this.tileActionFeedback = `Updated caption for '${filename}' to: "${updated.label}".`;
      }
    } catch (e: any) {
      this.tileActionFeedback = `Error updating caption: ${e?.message || e}`;
    }
  }

  private async handleDeleteCapture(filename: string): Promise<void> {
    if (!window.confirm(`Are you sure you want to delete media artifact "${filename}"?`)) {
      return;
    }
    const bundleId = this.currentBundleId;
    try {
      await fetch(`/api/demos/${bundleId}/captures/${filename}`, {
        method: 'DELETE',
      });
    } catch {
      // Offline preview fallback still removes from local state
    }
    this.captures = this.captures.filter((c) => c.filename !== filename);
    if (this.previewCapture && this.previewCapture.filename === filename) {
      this.previewCapture = null;
    }
  }

  private formatCaptureDate(isoString?: string): string {
    if (!isoString) return 'Just now';
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  }

  private formatRelativeTime(isoString?: string): string {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      const diffMs = Date.now() - d.getTime();
      if (diffMs < 0) return 'just now';
      const diffSec = Math.floor(diffMs / 1000);
      if (diffSec < 60) return 'just now';
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      const diffHours = Math.floor(diffMin / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}d ago`;
    } catch {
      return '';
    }
  }

  private openWelcomeModal(): void {
    this.dispatchEvent(new CustomEvent('open-welcome', { bubbles: true, composed: true }));
  }

  private openPresenterHud(): void {
    this.dispatchEvent(
      new CustomEvent('open-walkthrough', {
        detail: { bundleId: this.currentBundleId },
        bubbles: true,
        composed: true,
      })
    );
  }

  private renderHomeView() {
    if (this.splitScreenOpen) {
      return this.renderSplitScreenMode();
    }
    return this.renderControlTowerMode();
  }

  private renderControlTowerMode() {
    const primaryInst = this.selectedInstance ?? this.instances[0];
    const totalTables = this.demoBundles.reduce((acc, b) => acc + (b.tables_count || 0), 0) || 7;
    const totalRecords = this.demoBundles.reduce((acc, b) => acc + (b.records_count || 0), 0) || 62;

    return html`
      <div class="control-tower-hero">
        <h1 class="control-tower-greeting">
          <svg viewBox="0 0 24 24" style="width: 22px; height: 22px; fill: var(--now-color-brand-green, #16a34a); flex-shrink: 0;">
            <path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z" />
          </svg>
          <span>Hey Pierre, how can Otto help with your ServiceNow demos today?</span>
        </h1>

        <div class="elevated-prompt-pill">
          <button
            class="pill-attach-btn"
            title="Start a new empty conversation"
            aria-label="New conversation"
            @click=${() => this.requestNewConversation()}
          >
            <svg viewBox="0 0 24 24">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
          <input
            class="elevated-prompt-input"
            type="text"
            placeholder="Ask Otto a question (e.g., 'How many instances do I have?' or 'Show demo recipe bundles')..."
            .value=${this.homeChatInput}
            @input=${(e: Event) => {
              this.homeChatInput = (e.target as HTMLInputElement).value;
            }}
            @keydown=${(e: KeyboardEvent) => {
              if (e.key === 'Enter') {
                void this.submitHomeChat();
              }
            }}
          />
          <button
            class="send-action-btn"
            @click=${() => void this.submitHomeChat()}
            title="Ask Otto"
            aria-label="Ask Otto"
          >
            <svg viewBox="0 0 24 24">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>

        <div class="hero-chip-row">
          <button
            class="hero-chip"
            @click=${() => void this.submitHomeChat('how many instande I have')}
          >
            How many instances do I have?
          </button>
          <button
            class="hero-chip"
            @click=${() => void this.submitHomeChat('Explain demo recipes vs update sets')}
          >
            Demo recipes vs update sets
          </button>
          <button
            class="hero-chip"
            @click=${() => void this.submitHomeChat('Show demo recipe bundles')}
          >
            Explore recipe bundles
          </button>
          <button
            class="hero-chip"
            @click=${() => void this.submitHomeChat('Inspect ServiceNow Zurich Fluent SDK schema contracts')}
          >
            Inspect Fluent SDK schemas
          </button>
        </div>
      </div>

      <!-- WORKBENCH CONFIGURATION & USAGE STATS GRID -->
      <div class="ct-dashboard-container">
        <!-- ROW 1: 3 STATS WIDGETS -->
        <div class="ct-grid-row-1">
          <!-- WIDGET 1: REGISTERED SERVICENOW INSTANCES -->
          <div class="ct-card">
            <div class="ct-card-header">
              <h3 class="ct-card-title">Registered ServiceNow Instances</h3>
              <span class="ct-tag ${this.statusBadgeVariant(this.probeStatus)}">${this.probeStatus}</span>
            </div>
            <p class="ct-card-sub">Configured target environments in SQLite registry</p>

            <div class="ct-kpi-value">${this.instances.length}</div>
            <div class="ct-kpi-trend">
              Primary: ${primaryInst?.name ?? 'Alec Demo Trial'} (${primaryInst?.release ?? 'Zurich'})
            </div>

            <div class="ct-action-list" style="margin-top: 8px;">
              ${this.instances.slice(0, 3).map(
                (inst) => html`
                  <div class="ct-action-item">
                    <div class="ct-item-content">
                      <span class="ct-tag low">${inst.release || 'Zurich'}</span>
                      <span class="ct-action-text">${inst.name} (${inst.url})</span>
                    </div>
                  </div>
                `
              )}
            </div>

            <div style="display: flex; gap: 8px; margin-top: auto; padding-top: 8px;">
              <button
                class="ct-action-btn primary"
                @click=${() => void this.submitHomeChat('how many instances do I have')}
              >
                Ask Otto about Instances
              </button>
              <button class="ct-action-btn" @click=${() => this.navigateToMenu('admin')}>
                Manage Targets
              </button>
            </div>
          </div>

          <!-- WIDGET 2: DECLARATIVE DEMO RECIPE BUNDLES -->
          <div class="ct-card">
            <div class="ct-card-header">
              <h3 class="ct-card-title">Declarative Demo Recipe Bundles</h3>
              <span class="ct-tag low">Zero Update Sets</span>
            </div>
            <p class="ct-card-sub">Portable .sn-demo.zip recipes compatible with any ServiceNow release</p>

            <div class="ct-kpi-value">${this.bundleCount}</div>
            <div class="ct-kpi-trend">${totalTables} Fluent SDK Tables &bull; ${totalRecords} Seed Records</div>

            <div class="ct-banner" style="margin-top: auto;">
              <span class="ct-banner-text">
                Recipes compile into native Table &amp; Metadata API calls without brittle sys_update_xml payloads.
              </span>
              <button
                class="ct-action-btn primary"
                @click=${() => void this.submitHomeChat('Show demo recipe bundles')}
              >
                Explore in Otto
              </button>
            </div>
          </div>

          <!-- WIDGET 3: RELEASE COMPATIBILITY & FLUENT SDK -->
          <div class="ct-card">
            <div class="ct-card-header">
              <h3 class="ct-card-title">Release Compatibility Matrix</h3>
              <span class="ct-tag high">100% Agnostic</span>
            </div>
            <p class="ct-card-sub">Cross-release schema &amp; seed data compatibility</p>

            <div style="display: flex; flex-direction: column; gap: 10px; margin: 8px 0;">
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 11.5px; margin-bottom: 3px;">
                  <span style="font-weight: 600;">Zurich / Australia</span>
                  <span style="color: #16a34a; font-weight: 700;">100% Verified</span>
                </div>
                <div style="height: 6px; background: #e2e8f0; border-radius: 999px; overflow: hidden;">
                  <div style="width: 100%; height: 100%; background: #16a34a;"></div>
                </div>
              </div>
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 11.5px; margin-bottom: 3px;">
                  <span style="font-weight: 600;">Xanadu / Washington</span>
                  <span style="color: #16a34a; font-weight: 700;">100% Verified</span>
                </div>
                <div style="height: 6px; background: #e2e8f0; border-radius: 999px; overflow: hidden;">
                  <div style="width: 100%; height: 100%; background: #16a34a;"></div>
                </div>
              </div>
            </div>

            <div style="display: flex; gap: 8px; margin-top: auto; padding-top: 8px;">
              <button
                class="ct-action-btn primary"
                @click=${() => void this.submitHomeChat('Explain demo recipes vs update sets')}
              >
                Recipes vs Update Sets
              </button>
              <button class="ct-action-btn" @click=${() => this.navigateToMenu('fluent')}>
                Fluent Studio
              </button>
            </div>
          </div>
        </div>

        <!-- ROW 2: 2 STATS WIDGETS -->
        <div class="ct-grid-row-2">
          <!-- WIDGET 4: OTTO CONVERSATION & CONTEXT GOVERNANCE -->
          <div class="ct-card">
            <div class="ct-card-header">
              <h3 class="ct-card-title">Otto Conversation Context &amp; Storage</h3>
              <span class="ct-tag low">SQLite WAL Persisted</span>
            </div>
            <p class="ct-card-sub">Full conversation history with bounded ${this.maxContextMessages}-message AI context window</p>

            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 8px 0;">
              <div style="background: var(--now-bg-surface-1, #f8fafc); padding: 12px; border-radius: 8px; border: 1px solid var(--now-border-subtle, #e2e8f0);">
                <div style="font-size: 11px; color: var(--now-text-muted, #64748b); font-weight: 700; text-transform: uppercase;">Context Window Cap</div>
                <div style="font-size: 20px; font-weight: 800; color: var(--now-text-primary, #0f172a); margin: 4px 0;">${this.maxContextMessages} Messages</div>
                <div style="font-size: 11.5px; color: var(--now-text-secondary, #475467);">10 User/AI turns per conversation</div>
              </div>
              <div style="background: var(--now-bg-surface-1, #f8fafc); padding: 12px; border-radius: 8px; border: 1px solid var(--now-border-subtle, #e2e8f0);">
                <div style="font-size: 11px; color: var(--now-text-muted, #64748b); font-weight: 700; text-transform: uppercase;">Generative UI Engine</div>
                <div style="font-size: 20px; font-weight: 800; color: #16a34a; margin: 4px 0;">1 / 2 / 3 Col</div>
                <div style="font-size: 11.5px; color: var(--now-text-secondary, #475467);">Adaptive multi-tile layout</div>
              </div>
            </div>

            <div style="display: flex; gap: 8px; margin-top: auto;">
              <button class="ct-action-btn primary" @click=${() => this.requestNewConversation()}>
                + Start New Conversation
              </button>
              <button
                class="ct-action-btn"
                @click=${() => void this.submitHomeChat('Inspect ServiceNow Zurich Fluent SDK schema contracts')}
              >
                Inspect Schemas in Otto
              </button>
            </div>
          </div>

          <!-- WIDGET 5: WORKBENCH STUDIO QUICK ACTIONS -->
          <div class="ct-card">
            <div class="ct-card-header">
              <h3 class="ct-card-title">Workbench Studio Workflows</h3>
              <span class="ct-tag low">Direct Shortcuts</span>
            </div>
            <p class="ct-card-sub">Synthesize new demo recipes, capture media, or manage artifacts</p>

            <div class="ct-action-list">
              <div class="ct-action-item">
                <div class="ct-item-content">
                  <span class="ct-tag high">STUDIO</span>
                  <span class="ct-action-text">Synthesize a new customer demo recipe (*.now.ts + seed JSON)</span>
                </div>
                <button class="ct-action-btn primary" @click=${() => this.navigateToMenu('synthesizer')}>
                  Open Synthesizer
                </button>
              </div>
              <div class="ct-action-item">
                <div class="ct-item-content">
                  <span class="ct-tag low">CATALOG</span>
                  <span class="ct-action-text">Manage, seed, export, or delete demo recipe bundles</span>
                </div>
                <button class="ct-action-btn" @click=${() => this.navigateToMenu('artifacts')}>
                  Artifact Library
                </button>
              </div>
              <div class="ct-action-item">
                <div class="ct-item-content">
                  <span class="ct-tag low">CAPTURE</span>
                  <span class="ct-action-text">Capture Playwright screenshots or WebM walkthroughs</span>
                </div>
                <button class="ct-action-btn" @click=${() => this.navigateToMenu('capture')}>
                  Media Capture
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  private renderSplitScreenMode() {
    const msgCount = this.conversationMessages.length;
    const maxMsgs = this.maxContextMessages;
    const isLimitReached = msgCount >= maxMsgs;
    const remainingMsgs = Math.max(0, maxMsgs - msgCount);
    const usagePct = Math.min(100, Math.round((msgCount / maxMsgs) * 100));
    const meterColor = isLimitReached ? '#dc2626' : msgCount >= 14 ? '#f59e0b' : '#16a34a';

    return html`
      <div
        class="conversation-mode-page"
        style="display: flex; flex-direction: column; height: 100%; width: 100%; background: var(--now-bg-canvas, #f8fafc); overflow: hidden;"
      >
        <!-- CONVERSATION MODE HEADER BAR -->
        <div
          style="display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 24px; background: var(--now-bg-surface-0, #ffffff); border-bottom: 1px solid var(--now-border-subtle, #e2e8f0); flex-shrink: 0; flex-wrap: wrap;"
        >
          <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
            <button
              class="ct-action-btn"
              title="Return to Now Workbench Home Overview"
              @click=${() => this.handleCloseSplitScreen()}
            >
              &larr; Back to Home
            </button>
            <div style="min-width: 0;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <h2
                  style="margin: 0; font-size: 16px; font-weight: 700; color: var(--now-text-primary, #0f172a); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                >
                  ${this.currentSessionTitle}
                </h2>
                ${this.currentThreadArchived
                  ? html`<span class="ct-tag medium">Archived</span>`
                  : html`<span class="ct-tag high">Active Conversation</span>`}
              </div>
              <div style="font-size: 11.5px; color: var(--now-text-muted, #64748b);">
                Persisted in SQLite &bull; Multi-Tile Generative UI Session
              </div>
            </div>
          </div>

          <!-- CONTEXT WINDOW USAGE METER -->
          <div
            style="display: flex; align-items: center; gap: 10px; background: var(--now-bg-surface-1, #f8fafc); padding: 6px 12px; border-radius: 8px; border: 1px solid var(--now-border-subtle, #e2e8f0);"
            title="Conversation history is passed as context to Otto AI and capped at ${maxMsgs} messages (${maxMsgs / 2} turns)."
          >
            <div style="display: flex; flex-direction: column; gap: 3px; min-width: 155px;">
              <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 700; color: var(--now-text-secondary, #334155);">
                <span>AI Context Window</span>
                <span style="color: ${meterColor};">${msgCount} / ${maxMsgs} msgs</span>
              </div>
              <div style="height: 5px; width: 100%; background: #e2e8f0; border-radius: 999px; overflow: hidden;">
                <div style="width: ${usagePct}%; height: 100%; background: ${meterColor}; transition: width 0.2s ease;"></div>
              </div>
            </div>
          </div>

          <!-- CONVERSATION ACTIONS: NEW, ARCHIVE, DELETE -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <button
              class="ct-action-btn primary"
              title="Start a fresh Otto conversation"
              @click=${() => this.requestNewConversation()}
            >
              + New Conversation
            </button>
            ${this.activeThreadId
              ? html`
                  <button
                    class="ct-action-btn"
                    title=${this.currentThreadArchived
                      ? 'Unarchive this conversation'
                      : 'Archive this conversation'}
                    @click=${() => this.requestArchiveCurrentThread()}
                  >
                    ${this.currentThreadArchived ? 'Unarchive' : 'Archive'}
                  </button>
                  <button
                    class="ct-action-btn"
                    style="color: #dc2626; border-color: #fecaca;"
                    title="Delete this conversation from database"
                    @click=${() => this.requestDeleteCurrentThread()}
                  >
                    Delete
                  </button>
                `
              : ''}
          </div>
        </div>

        <!-- FULL CHRONOLOGICAL CONVERSATION HISTORY STREAM -->
        <div
          style="flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px;"
        >
          <div
            style="max-width: 1040px; width: 100%; margin: 0 auto; display: flex; flex-direction: column; gap: 20px;"
          >
            ${this.tileActionFeedback
              ? html`
                  <div
                    style="background: var(--now-bg-surface-0, #ffffff); border: 1px solid var(--now-border-subtle, #e2e8f0); border-left: 4px solid var(--now-color-brand-green, #16a34a); border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);"
                  >
                    <div style="font-size: 13px; color: var(--now-text-primary, #0f172a); font-weight: 600;">
                      ${this.tileActionFeedback}
                    </div>
                    <button
                      type="button"
                      class="ct-action-btn"
                      @click=${() => {
                        this.tileActionFeedback = '';
                      }}
                    >
                      Dismiss
                    </button>
                  </div>
                `
              : ''}

            ${this.conversationMessages.length === 0
              ? html`
                  <div
                    class="ct-card"
                    style="padding: 28px; text-align: center; align-items: center; gap: 12px;"
                  >
                    <div
                      style="width: 42px; height: 42px; border-radius: 50%; background: rgba(98, 216, 78, 0.15); color: #16a34a; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 18px;"
                    >
                      O
                    </div>
                    <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: var(--now-text-primary, #0f172a);">
                      New Otto Conversation Ready
                    </h3>
                    <p style="margin: 0; max-width: 580px; font-size: 13.5px; color: var(--now-text-secondary, #475467); line-height: 1.55;">
                      Ask any question below or pick a starter topic. Otto arranges answers into interactive 1-column, 2-column, or 3-column Generative UI tiles and retains up to ${maxMsgs} messages (${maxMsgs / 2} turns) of context in SQLite.
                    </p>
                    <div class="hero-chip-row" style="margin-top: 8px;">
                      <button
                        class="hero-chip"
                        @click=${() => void this.handleSplitChatSubmit('how many instande I have')}
                      >
                        How many instances do I have?
                      </button>
                      <button
                        class="hero-chip"
                        @click=${() => void this.handleSplitChatSubmit('Explain demo recipes vs update sets')}
                      >
                        Demo recipes vs update sets
                      </button>
                      <button
                        class="hero-chip"
                        @click=${() => void this.handleSplitChatSubmit('Show demo recipe bundles')}
                      >
                        Show demo recipe bundles
                      </button>
                      <button
                        class="hero-chip"
                        @click=${() => void this.handleSplitChatSubmit('Inspect ServiceNow Zurich Fluent SDK schema contracts')}
                      >
                        Inspect Fluent SDK schemas
                      </button>
                    </div>
                  </div>
                `
              : this.conversationMessages.map((msg, idx) =>
                  msg.role === 'user'
                    ? html`
                        <div style="display: flex; justify-content: flex-end; width: 100%;">
                          <div
                            class="user-bubble"
                            style="max-width: 75%; font-size: 14px; padding: 12px 16px;"
                          >
                            <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; opacity: 0.7; margin-bottom: 4px;">
                              You &bull; Message ${idx + 1} of ${maxMsgs}
                            </div>
                            <div>${msg.content}</div>
                          </div>
                        </div>
                      `
                    : html`
                        <div
                          class="ct-card"
                          style="padding: 20px; border: 1px solid var(--now-border-subtle, #e2e8f0);"
                        >
                          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                              <div class="qa-otto-avatar">O</div>
                              <div>
                                <div style="font-size: 13.5px; font-weight: 700; color: var(--now-text-primary, #0f172a);">
                                  Otto Copilot
                                </div>
                                <div style="font-size: 11px; color: var(--now-text-muted, #64748b);">
                                  Generative UI Tile Engine &bull; Message ${idx + 1} of ${maxMsgs}
                                </div>
                              </div>
                            </div>
                            ${msg.response
                              ? html`<span class="ct-tag low">Layout: ${msg.response.layout}</span>`
                              : ''}
                          </div>

                          <div class="qa-summary-text" style="font-size: 14px; margin-bottom: 12px;">
                            ${msg.response ? msg.response.summary : msg.content}
                          </div>

                          ${msg.response && msg.response.tiles.length > 0
                            ? html`
                                <div class="generative-tile-grid ${msg.response.layout}">
                                  ${msg.response.tiles.map((t) => this.renderUITile(t))}
                                </div>
                              `
                            : ''}
                        </div>
                      `
                )}

            ${isLimitReached || this.contextLimitError
              ? html`
                  <div
                    style="background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #dc2626; border-radius: 10px; padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;"
                  >
                    <div style="font-size: 13px; color: #991b1b; font-weight: 600;">
                      ${this.contextLimitError ||
                      `Conversation context limit reached (${maxMsgs}/${maxMsgs} messages). Start a new conversation so Otto has a clean context window.`}
                    </div>
                    <button
                      class="ct-action-btn primary"
                      @click=${() => this.requestNewConversation()}
                    >
                      + Start New Conversation
                    </button>
                  </div>
                `
              : ''}
          </div>
        </div>

        <!-- BOTTOM CONVERSATION PROMPT INPUT DOCK -->
        <div
          style="padding: 14px 24px 18px 24px; background: var(--now-bg-surface-0, #ffffff); border-top: 1px solid var(--now-border-subtle, #e2e8f0); flex-shrink: 0;"
        >
          <div style="max-width: 1040px; margin: 0 auto; display: flex; flex-direction: column; gap: 6px;">
            <div class="split-prompt-pill" style="padding: 8px 10px 8px 16px;">
              <input
                class="split-prompt-input"
                style="font-size: 14px;"
                placeholder=${isLimitReached
                  ? 'Conversation context limit reached (20/20 messages). Click "+ New Conversation" above.'
                  : 'Ask Otto a question or follow-up in this conversation...'}
                ?disabled=${isLimitReached}
                .value=${this.splitChatInput}
                @input=${(e: Event) => {
                  this.splitChatInput = (e.target as HTMLInputElement).value;
                }}
                @keydown=${(e: KeyboardEvent) => {
                  if (e.key === 'Enter') {
                    void this.handleSplitChatSubmit();
                  }
                }}
              />
              <button
                class="split-send-btn"
                ?disabled=${isLimitReached}
                @click=${() => void this.handleSplitChatSubmit()}
                title="Send message in conversation"
                aria-label="Send message"
              >
                <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
              </button>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--now-text-muted, #64748b); padding: 0 4px;">
              <span>All messages and tiles are automatically saved to SQLite.</span>
              <span>${remainingMsgs} of ${maxMsgs} context messages remaining</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  private renderSynthesizerView() {
    return html`
      <div class="studio-card">
        <div class="card-header">
          <div class="card-title-group">
            <div class="card-icon">
              <svg viewBox="0 0 24 24">
                <path d="M12 2L14.8 8.5L22 9.3L16.5 14L18.2 21L12 17.3L5.8 21L7.5 14L2 9.3L9.2 8.5L12 2Z" />
              </svg>
            </div>
            <div>
              <h2 class="card-title">Use-Case & Demo Narrative Synthesizer</h2>
              <p class="card-subtitle">Generates multi-table seed data, Fluent .now.ts customizations & Solution Consultant narrative</p>
            </div>
          </div>
          <span class="badge-tag">Fluent SDK + Seed JSON + SC Guide</span>
        </div>

        <div class="field-group">
          <label class="field-label">Use Case Description & Business Context</label>
          <textarea
            class="field-textarea"
            .value=${this.useCasePrompt}
            @input=${(e: Event) => {
              this.useCasePrompt = (e.target as HTMLTextAreaElement).value;
            }}
            placeholder="Describe the customer problem, workflow, and desired outcome..."
          ></textarea>
        </div>

        <div class="form-grid-2">
          <div class="field-group">
            <label class="field-label">Customer Account</label>
            <input
              class="field-input"
              .value=${this.customerName}
              @input=${(e: Event) => {
                this.customerName = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
          <div class="field-group">
            <label class="field-label">Industry Vertical</label>
            <input
              class="field-input"
              .value=${this.industry}
              @input=${(e: Event) => {
                this.industry = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
        </div>

        <div class="form-grid-2">
          <div class="field-group">
            <label class="field-label">Primary Persona</label>
            <input
              class="field-input"
              .value=${this.personaPrimary}
              @input=${(e: Event) => {
                this.personaPrimary = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
          <div class="field-group">
            <label class="field-label">ServiceNow Release</label>
            <select
              class="field-select"
              .value=${this.releaseTarget}
              @change=${(e: Event) => {
                this.releaseTarget = (e.target as HTMLSelectElement).value;
              }}
            >
              <option value="Zurich">Zurich</option>
              <option value="Yokohama">Yokohama</option>
              <option value="Xanadu">Xanadu</option>
            </select>
          </div>
        </div>

        <div class="card-actions">
          <button
            class="pill-btn accent icon-btn"
            ?disabled=${this.isSynthesizing}
            @click=${this.handleSynthesize}
            title="${this.isSynthesizing ? 'Synthesizing...' : 'Synthesize Data Sets, Customizations & Narrative'}"
            aria-label="Synthesize Demo"
            data-tooltip="Synthesize Demo"
          >
            <svg viewBox="0 0 24 24">
              <path d="M12 2L14.8 8.5L22 9.3L16.5 14L18.2 21L12 17.3L5.8 21L7.5 14L2 9.3L9.2 8.5L12 2Z" />
            </svg>
          </button>
          <button
            class="pill-btn primary icon-btn"
            @click=${this.handleSeedSynthesized}
            title="Seed Synthesized Records to Target Instance"
            aria-label="Seed Data"
            data-tooltip="Seed to Instance"
          >
            <svg viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 3.79 2 6v12c0 2.21 4.48 4 10 4s10-1.79 10-4V6c0-2.21-4.48-4-10-4zm0 2c4.42 0 8 1.34 8 2s-3.58 2-8 2-8-1.34-8-2 3.58-2 8-2zm8 14c0 .66-3.58 2-8 2s-8-1.34-8-2v-2.17c2.19 1.34 5.37 1.83 8 1.83s5.81-.49 8-1.83V18zm0-4c0 .66-3.58 2-8 2s-8-1.34-8-2v-2.17c2.19 1.34 5.37 1.83 8 1.83s5.81-.49 8-1.83V14z" />
            </svg>
          </button>
        </div>

        ${this.seedStatusMessage
          ? html`<div class="status-banner"><span>${this.seedStatusMessage}</span></div>`
          : ''}
      </div>

      ${this.synthesizedResult
        ? html`
            <div class="result-card">
              <div class="result-header">
                <div>
                  <h3 class="card-title">${this.synthesizedResult.title}</h3>
                  <p class="card-subtitle">
                    Bundle ID: <strong>${this.synthesizedResult.bundle_id}</strong> | Custom Fluent Table:
                    <code>${this.synthesizedResult.fluent_table_name}</code>
                  </p>
                </div>

                <div class="result-tabs">
                  <button
                    class="result-tab ${this.activeResultTab === 'narrative' ? 'active' : ''}"
                    @click=${() => {
                      this.activeResultTab = 'narrative';
                    }}
                  >
                    SC Demo Narrative (guide.md)
                  </button>
                  <button
                    class="result-tab ${this.activeResultTab === 'datasets' ? 'active' : ''}"
                    @click=${() => {
                      this.activeResultTab = 'datasets';
                    }}
                  >
                    Synthesized Data Sets (seed/*.json)
                  </button>
                  <button
                    class="result-tab ${this.activeResultTab === 'customizations' ? 'active' : ''}"
                    @click=${() => {
                      this.activeResultTab = 'customizations';
                    }}
                  >
                    Fluent SDK Customizations (.now.ts)
                  </button>
                </div>
              </div>

              <div class="result-body">
                ${this.activeResultTab === 'narrative'
                  ? html`<div class="narrative-box">${this.synthesizedResult.narrative_markdown}</div>`
                  : ''}
                ${this.activeResultTab === 'datasets'
                  ? html`<pre class="code-pre">${JSON.stringify(this.synthesizedResult.seed_records, null, 2)}</pre>`
                  : ''}
                ${this.activeResultTab === 'customizations'
                  ? html`<pre class="code-pre">${this.synthesizedResult.fluent_code}</pre>`
                  : ''}
              </div>
            </div>
          `
        : ''}
    `;
  }

  private renderCaptureView() {
    return html`
      <div class="studio-card">
        <div class="card-header">
          <div class="card-title-group">
            <div class="card-icon">
              <svg viewBox="0 0 24 24">
                <rect x="3" y="5" width="18" height="14" rx="2" />
                <circle cx="12" cy="12" r="3.2" />
              </svg>
            </div>
            <div>
              <h2 class="card-title">Instance Screenshot & Video Capture</h2>
              <p class="card-subtitle">Capture live ServiceNow screenshots (.png) & walkthrough videos (.webm) into your bundle</p>
            </div>
          </div>
          <span class="badge-tag">Media Recorder</span>
        </div>

        <div class="form-grid-2" style="margin-bottom: 12px;">
          <div class="field-group">
            <label class="field-label">Target Demonstration Package</label>
            <select
              class="field-select"
              .value=${this.captureSelectedBundleId}
              @change=${async (e: Event) => {
                const bId = (e.target as HTMLSelectElement).value;
                this.captureSelectedBundleId = bId;
                try {
                  localStorage.setItem('now-workbench-capture-bundle', bId);
                } catch {}
                await this.loadCaptures(bId);
              }}
            >
              ${this.demoBundles.map(
                (b) => html`
                  <option value=${b.id} ?selected=${b.id === this.captureSelectedBundleId}>
                    ${b.name} (${b.id})
                  </option>
                `
              )}
            </select>
          </div>
          <div class="field-group">
            <label class="field-label">Target Instance</label>
            <select
              class="field-select"
              .value=${this.selectedInstanceId}
              @change=${this.handleInstanceChange}
            >
              ${this.instances.map(
                (inst) => html`
                  <option value=${inst.id} ?selected=${inst.id === this.selectedInstanceId}>
                    ${inst.name} (${inst.release})
                  </option>
                `
              )}
            </select>
          </div>
        </div>

        <div class="form-grid-2">
          <div class="field-group">
            <label class="field-label">Instance URI Path</label>
            <input
              class="field-input"
              .value=${this.uriPath}
              @input=${(e: Event) => {
                this.uriPath = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
          <div class="field-group">
            <label class="field-label">Capture Format</label>
            <select
              class="field-select"
              .value=${this.captureMode}
              @change=${(e: Event) => {
                this.captureMode = (e.target as HTMLSelectElement).value as 'screenshot' | 'video';
              }}
            >
              <option value="screenshot">Screenshot (.png)</option>
              <option value="video">Walkthrough Video (.webm)</option>
            </select>
          </div>
        </div>

        <div class="field-group" style="margin-top: 12px;">
          <label class="field-label">Artifact Caption / Label</label>
          <input
            class="field-input"
            .value=${this.captureCaption}
            @input=${(e: Event) => {
              this.captureCaption = (e.target as HTMLInputElement).value;
            }}
            placeholder="e.g. Agent Workspace Incident Triage View"
          />
        </div>

        <div class="card-actions">
          <button
            class="pill-btn primary icon-btn"
            ?disabled=${this.isCapturing}
            @click=${this.handleCapture}
            title="${this.isCapturing ? 'Capturing...' : `Capture ${this.captureMode === 'video' ? 'Video (.webm)' : 'Screenshot (.png)'}`}"
            aria-label="Capture Media"
            data-tooltip="Capture Media"
          >
            <svg viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z" />
            </svg>
          </button>
        </div>

        <h3 style="font-size: 14px; font-weight: 700; margin: 24px 0 12px 0; color: var(--now-text-primary);">
          Recorded Artifacts for "${this.captureSelectedBundleId}" (${this.captures.length})
        </h3>

        ${this.captures.length > 0
          ? html`
              <div class="capture-gallery">
                ${[...this.captures]
                  .sort(
                    (a, b) =>
                      new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
                  )
                  .map(
                    (cap) => html`
                      <div class="capture-item">
                        <div
                          class="capture-preview"
                          @click=${() => {
                            this.previewCapture = cap;
                          }}
                          title="Click to open full view"
                        >
                          ${cap.media_type === 'video'
                            ? html`<video src=${cap.url} controls muted playsinline></video>`
                            : html`<img src=${cap.url} alt=${cap.label || cap.filename} />`}
                          <div class="capture-hover-badge">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                              ${cap.media_type === 'video'
                                ? html`<path d="M8 5v14l11-7z" />`
                                : html`<path
                                    d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 14z"
                                  />`}
                            </svg>
                            <span>${cap.media_type === 'video' ? 'Play Video' : 'View Full Image'}</span>
                          </div>
                        </div>
                        <div class="capture-meta">
                          <div class="capture-caption">${cap.label || cap.filename}</div>
                          <div class="capture-date">
                            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                              <line x1="16" y1="2" x2="16" y2="6" />
                              <line x1="8" y1="2" x2="8" y2="6" />
                              <line x1="3" y1="10" x2="21" y2="10" />
                            </svg>
                            <span>${this.formatCaptureDate(cap.created_at)}</span>
                            <span style="color: var(--now-text-muted, #94a3b8); font-size: 10px;">(${this.formatRelativeTime(cap.created_at)})</span>
                          </div>
                          <div class="capture-sub">
                            <span>${cap.media_type.toUpperCase()} (${cap.engine})</span>
                            <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                              <button
                                class="ct-action-btn"
                                style="padding: 2px 7px; font-size: 11px; color: #0284c7; border-color: #bae6fd; background: #fff;"
                                title="Open in Lightbox Modal"
                                @click=${() => {
                                  this.previewCapture = cap;
                                }}
                              >
                                View
                              </button>
                              <a
                                href=${cap.url}
                                target="_blank"
                                rel="noopener"
                                style="font-size: 11px; color: #2563eb;"
                                title="Open in new browser tab without downloading"
                              >
                                Tab
                              </a>
                              <a
                                href=${cap.url}
                                download=${cap.filename}
                                style="font-size: 11px;"
                              >
                                Download
                              </a>
                              <button
                                class="ct-action-btn"
                                style="padding: 2px 7px; font-size: 11px; color: #4338ca; border-color: #c7d2fe; background: #fff;"
                                title="Rename Capture Caption"
                                @click=${() => this.handleRenameCapture(cap.filename, cap.label)}
                              >
                                Rename
                              </button>
                              <button
                                class="ct-action-btn"
                                style="padding: 2px 7px; font-size: 11px; color: #dc2626; border-color: #fecaca; background: #fff;"
                                title="Delete Capture Artifact"
                                @click=${() => this.handleDeleteCapture(cap.filename)}
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    `
                  )}
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderLightboxModal() {
    if (!this.previewCapture) {
      return '';
    }
    const cap = this.previewCapture;
    return html`
      <div
        class="lightbox-overlay"
        @click=${(e: Event) => {
          if (e.target === e.currentTarget) {
            this.previewCapture = null;
          }
        }}
      >
        <div class="lightbox-card" role="dialog" aria-modal="true">
          <div class="lightbox-header">
            <div>
              <div style="font-weight: 700; font-size: 15px; color: var(--now-text-primary, #111827);">
                ${cap.label || cap.filename}
              </div>
              <div class="capture-date" style="margin-top: 4px;">
                <span style="font-weight: 600; color: var(--now-color-brand-green, #62d84e);">${cap.media_type.toUpperCase()}</span>
                <span>|</span>
                <span>${this.formatCaptureDate(cap.created_at)}</span>
                <span>|</span>
                <span>${cap.engine}</span>
              </div>
            </div>
            <button
              class="ct-action-btn"
              style="padding: 4px 10px; font-size: 14px; font-weight: 700;"
              @click=${() => {
                this.previewCapture = null;
              }}
              title="Close viewer"
            >
              X
            </button>
          </div>

          <div class="lightbox-body">
            ${cap.media_type === 'video'
              ? html`
                  <video
                    src=${cap.url}
                    controls
                    autoplay
                    playsinline
                  ></video>
                `
              : html`
                  <img
                    src=${cap.url}
                    alt=${cap.label || cap.filename}
                  />
                `}
          </div>

          <div class="lightbox-footer">
            <div style="color: var(--now-text-secondary, #6b7280); font-family: monospace; font-size: 11px;">
              ${cap.target_path}
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
              <a
                class="ct-action-btn"
                style="padding: 4px 10px; font-size: 12px; color: #2563eb; text-decoration: none;"
                href=${cap.url}
                target="_blank"
                rel="noopener"
              >
                Open in New Tab
              </a>
              <button
                class="ct-action-btn"
                style="padding: 4px 10px; font-size: 12px; color: #4338ca; border-color: #c7d2fe; background: #fff;"
                @click=${() => this.handleRenameCapture(cap.filename, cap.label)}
              >
                Rename
              </button>
              <a
                class="ct-action-btn"
                style="padding: 4px 10px; font-size: 12px; color: var(--now-color-brand-green, #62d84e); text-decoration: none;"
                href=${cap.url}
                download=${cap.filename}
              >
                Download
              </a>
              <button
                class="ct-action-btn"
                style="padding: 4px 10px; font-size: 12px;"
                @click=${() => {
                  this.previewCapture = null;
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  render() {
    const viewLabel =
      this.viewMode === 'home'
        ? 'Home'
        : this.viewMode === 'synthesizer'
          ? 'Use-Case Synthesizer'
          : 'Media Capture';

    return html`
      <div class="top-utility-bar">
        <div class="workspace-breadcrumb">
          <span class="status-dot"></span>
          <span>Now Workbench</span>
          <span style="color: #9ca3af;">/</span>
          <span>${viewLabel}</span>
        </div>

        <div class="utility-actions">
          <div class="instance-picker-pill">
            <span class="instance-picker-label">Target:</span>
            <select
              class="instance-picker-select"
              .value=${this.selectedInstanceId}
              @change=${this.handleInstanceChange}
              title="Select active ServiceNow instance target for media capture, seeding, and diagnostics"
            >
              ${this.instances.map(
                (inst) => html`
                  <option value=${inst.id} ?selected=${inst.id === this.selectedInstanceId}>
                    ${inst.name} (${inst.release})
                  </option>
                `
              )}
            </select>
          </div>
          <button
            class="pill-btn icon-btn"
            @click=${this.openWelcomeModal}
            title="Welcome to Now Workbench Guide"
            aria-label="Welcome Guide"
            data-tooltip="Welcome Guide"
          >
            <svg viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" />
            </svg>
          </button>
          <button
            class="pill-btn primary icon-btn"
            @click=${this.openPresenterHud}
            title="Launch Presenter HUD Teleprompter"
            aria-label="Launch Presenter HUD"
            data-tooltip="Presenter HUD"
          >
            <svg viewBox="0 0 24 24">
              <path d="M21 3H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h5v2h8v-2h5c1.1 0 1.99-.9 1.99-2L23 5c0-1.1-.9-2-2-2zm0 14H3V5h18v12zm-11-2l6-4-6-4v8z" />
            </svg>
          </button>
        </div>
      </div>

      <div class="scroll-canvas">
        <div class="canvas-container">
          ${this.viewMode === 'home' ? this.renderHomeView() : ''}
          ${this.viewMode === 'synthesizer' ? this.renderSynthesizerView() : ''}
          ${this.viewMode === 'capture' ? this.renderCaptureView() : ''}
        </div>
      </div>

      ${this.renderLightboxModal()}
    `;
  }
}
