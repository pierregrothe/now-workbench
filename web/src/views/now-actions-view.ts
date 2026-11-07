// web/src/views/now-actions-view.ts
// The Actions screen: every capability of the workbench as a form, results shown as tiles.
// Author: Pierre Grothe
// Date: 2026-11-07
//
// ADR-026: the catalog is the same tool registry Otto uses, served by /api/actions for the
// signed-in person, so whatever Otto can do a person can do here by hand, under the same
// rules. Otto can open this screen with an action pre-filled (store.pendingAction).

import { LitElement, html, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { workbenchStore } from '../context/workbench-context.js';
import { workspaceStyles } from '../styles/workspace-styles.js';
import type { UITileSpec } from '../tiles/now-tile-renderer.js';
import { actionsViewStyles } from './now-actions-view-styles.js';
import '../tiles/now-tile-renderer.js';
import './now-workspace-bar.js';

interface FieldSchema {
  type?: string;
  enum?: string[];
  description?: string;
  items?: { type?: string };
}

/** A list of plain values is typed as comma-separated text, not JSON. */
const isTextList = (s?: FieldSchema): boolean => s?.type === 'array' && s.items?.type === 'string';

interface ActionInfo {
  name: string;
  description: string;
  category: string;
  destructive: boolean;
  properties: Record<string, FieldSchema>;
  required: string[];
}

interface ActionResult {
  ok: boolean;
  summary: string;
  pending: boolean;
  tiles: UITileSpec[];
}

/** 'list_instances' -> 'List instances'. */
const label = (name: string): string => {
  const words = name.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
};

@customElement('now-actions-view')
export class NowActionsView extends LitElement {
  static styles = [workspaceStyles, actionsViewStyles];

  /** Action to select (from the URL '#actions/<name>'). */
  @property() actionName = '';

  @state() private actions: ActionInfo[] = [];
  @state() private loadError = '';
  @state() private query = '';
  @state() private selected: ActionInfo | null = null;
  @state() private values: Record<string, unknown> = {};
  @state() private running = false;
  @state() private result: ActionResult | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  protected willUpdate(changed: PropertyValues<this>): void {
    if (changed.has('actionName') && this.actions.length) this.selectByName(this.actionName);
  }

  private async load(): Promise<void> {
    try {
      const res = await fetch('/api/actions');
      if (!res.ok) {
        this.loadError = `Could not load actions (HTTP ${res.status}).`;
        return;
      }
      this.actions = (await res.json()) as ActionInfo[];
      this.selectByName(this.actionName);
    } catch (e) {
      this.loadError = `Could not load actions: ${e instanceof Error ? e.message : String(e)}`;
    }
  }

  /** Select an action; arguments Otto pre-filled for it are taken once from the store. */
  private selectByName(name: string): void {
    const action = this.actions.find((a) => a.name === name);
    if (!action) return;
    const pending = workbenchStore.state.pendingAction;
    const prefill = pending && pending.name === name ? pending.args : {};
    if (pending) workbenchStore.setState({ pendingAction: null });
    this.select(action, prefill);
  }

  private select(action: ActionInfo, prefill: Record<string, unknown> = {}): void {
    this.selected = action;
    this.values = { ...prefill };
    this.result = null;
    // On a phone the form sits above the list (ADR-030); bring it into view.
    void this.updateComplete.then(() =>
      this.renderRoot.querySelector('.panel')?.scrollIntoView({ block: 'nearest' }),
    );
  }

  private setValue(key: string, value: unknown): void {
    const next = { ...this.values };
    if (value === '' || value === undefined) delete next[key];
    else next[key] = value;
    this.values = next;
  }

  /** Arguments as the schema wants them: JSON for objects and arrays, numbers for integers. */
  private args(): Record<string, unknown> {
    const out: Record<string, unknown> = {};
    for (const [key, raw] of Object.entries(this.values)) {
      const schema = this.selected?.properties[key];
      const type = schema?.type;
      if (isTextList(schema) && typeof raw === 'string') {
        out[key] = raw.split(',').map((v) => v.trim()).filter(Boolean);
      } else if ((type === 'object' || type === 'array') && typeof raw === 'string') out[key] = JSON.parse(raw);
      else if (type === 'integer' && typeof raw === 'string') out[key] = Number(raw);
      else out[key] = raw;
    }
    return out;
  }

  private async run(confirmed = false): Promise<void> {
    if (!this.selected) return;
    this.running = true;
    try {
      const res = await fetch(`/api/actions/${encodeURIComponent(this.selected.name)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ args: this.args(), confirmed }),
      });
      const body = await res.json();
      this.result = res.ok
        ? (body as ActionResult)
        : { ok: false, pending: false, tiles: [], summary: String(body?.detail ?? `HTTP ${res.status}`) };
      if (res.ok && !this.result.pending) {
        // What an action changed shows everywhere, as after Otto acts.
        void workbenchStore.loadInstances();
        void workbenchStore.loadBundles();
      }
    } catch (e) {
      this.result = { ok: false, pending: false, tiles: [], summary: e instanceof Error ? e.message : String(e) };
    } finally {
      this.running = false;
    }
  }

  private renderField(key: string, schema: FieldSchema, required: boolean) {
    const value = this.values[key];
    const hint = schema.description ? html`<span class="hint">${schema.description}</span>` : '';
    const name = html`${label(key)}${required ? ' *' : ''}`;
    if (schema.type === 'boolean') {
      return html`<label class="field check"
        ><input type="checkbox" .checked=${Boolean(value)} @change=${(e: Event) => this.setValue(key, (e.target as HTMLInputElement).checked)} />${name}</label
      >`;
    }
    if (schema.enum) {
      return html`<label class="field">${name}
        <select @change=${(e: Event) => this.setValue(key, (e.target as HTMLSelectElement).value)}>
          <option value="" ?selected=${value === undefined}>--</option>
          ${schema.enum.map((opt) => html`<option value=${opt} ?selected=${value === opt}>${opt}</option>`)}
        </select>${hint}</label
      >`;
    }
    if (isTextList(schema)) {
      const text = Array.isArray(value) ? value.join(', ') : String(value ?? '');
      return html`<label class="field">${name}
        <input type="text" placeholder="one, two, three" .value=${text} @input=${(e: Event) => this.setValue(key, (e.target as HTMLInputElement).value)} />${hint ||
        html`<span class="hint">Separate several with commas.</span>`}</label
      >`;
    }
    if (schema.type === 'object' || schema.type === 'array') {
      const text = typeof value === 'string' ? value : value === undefined ? '' : JSON.stringify(value);
      return html`<label class="field">${name}
        <textarea placeholder=${schema.type === 'array' ? '[ ... ]' : '{ ... }'} .value=${text} @input=${(e: Event) => this.setValue(key, (e.target as HTMLTextAreaElement).value)}></textarea>${hint}</label
      >`;
    }
    return html`<label class="field">${name}
      <input
        type=${schema.type === 'integer' ? 'number' : 'text'}
        .value=${value === undefined ? '' : String(value)}
        @input=${(e: Event) => this.setValue(key, (e.target as HTMLInputElement).value)}
      />${hint}</label
    >`;
  }

  private renderCatalog() {
    const q = this.query.trim().toLowerCase();
    const shown = this.actions.filter(
      (a) => !q || a.name.includes(q.replace(/ /g, '_')) || a.description.toLowerCase().includes(q)
    );
    const categories = [...new Set(shown.map((a) => a.category))];
    return html`<div class="catalog">
      <input class="search" type="search" placeholder="Search actions" aria-label="Search actions" .value=${this.query} @input=${(e: Event) => (this.query = (e.target as HTMLInputElement).value)} />
      ${categories.map(
        (cat) => html`<div class="category">${cat}</div>
          ${shown
            .filter((a) => a.category === cat)
            .map(
              (a) => html`<button class="action-item ${this.selected?.name === a.name ? 'active' : ''}" @click=${() => this.select(a)}>
                <span>${label(a.name)}</span>${a.destructive ? html`<span class="confirm-tag">confirm</span>` : ''}
              </button>`
            )}`
      )}
    </div>`;
  }

  private renderResult() {
    const r = this.result;
    if (!r) return '';
    const kind = r.pending ? 'pending' : r.ok ? '' : 'error';
    return html`
      <div class="result ${kind}" role=${r.ok ? 'status' : 'alert'}>${r.summary}</div>
      ${r.pending
        ? html`<div class="run-row">
            <button class="btn" ?disabled=${this.running} @click=${() => this.run(true)}>Confirm</button>
            <button class="btn secondary" @click=${() => (this.result = null)}>Cancel</button>
          </div>`
        : html`<div class="tiles">
            ${r.tiles.map((t) => html`<now-tile-renderer .tile=${t}></now-tile-renderer>`)}
          </div>`}
    `;
  }

  render() {
    const a = this.selected;
    return html`
      <now-workspace-bar crumb="Actions"></now-workspace-bar>
      ${this.loadError ? html`<div class="badge error" role="alert" style="margin:12px 36px;display:block;">${this.loadError}</div>` : ''}
      <div class="actions-layout ${a ? 'picked' : ''}">
        ${this.renderCatalog()}
        <section class="panel" aria-label="Action">
          ${a
            ? html`<h2>${label(a.name)}</h2>
                <p class="desc">${a.description}</p>
                ${Object.keys(a.properties).length
                  ? html`<div class="fields">
                      ${Object.entries(a.properties).map(([k, s]) => this.renderField(k, s, a.required.includes(k)))}
                    </div>`
                  : ''}
                <div class="run-row">
                  <button class="btn" ?disabled=${this.running} @click=${() => this.run(false)}>
                    ${this.running ? 'Running...' : a.destructive ? 'Review' : 'Run'}
                  </button>
                </div>
                ${this.renderResult()}`
            : html`<p class="empty">Pick an action on the left, or ask Otto to do it for you.</p>`}
        </section>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-actions-view': NowActionsView;
  }
}
