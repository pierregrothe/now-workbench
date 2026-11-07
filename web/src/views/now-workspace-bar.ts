// web/src/views/now-workspace-bar.ts
// Top bar shared by the workspace views: breadcrumb, target-instance picker, extra actions.
// Author: Pierre Grothe
// Date: 2026-11-07
//
// ADR-024: the chat, capture-studio and synthesizer views carried copies of this markup.
// Extra buttons go in the default slot; `show-load-error` adds the store's load-error badge.

import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { workbenchStore } from '../context/workbench-context.js';
import { StoreController } from '../controllers/store-controller.js';
import { workspaceStyles } from '../styles/workspace-styles.js';

@customElement('now-workspace-bar')
export class NowWorkspaceBar extends LitElement {
  static styles = [
    workspaceStyles,
    css`
      /* workspaceStyles sizes a view's host to the full height; a bar takes its content height. */
      :host {
        display: block;
        height: auto;
        flex-shrink: 0;
      }
    `,
  ];

  /** Last breadcrumb segment (the current screen). */
  @property() crumb = '';

  /** Show the store's load error under the bar. */
  @property({ type: Boolean, attribute: 'show-load-error' }) showLoadError = false;

  private readonly store = new StoreController(this);

  private onInstanceChange(e: Event): void {
    workbenchStore.setState({ selectedInstanceId: (e.target as HTMLSelectElement).value });
  }

  render() {
    const { instances, selectedInstanceId, loadError } = this.store.state;
    return html`
      <div class="top-utility-bar">
        <div class="workspace-breadcrumb">
          <span class="status-dot"></span>
          <span>Now Workbench</span>
          <span style="color: #9ca3af;">/</span>
          <span>${this.crumb}</span>
        </div>
        <div class="utility-actions">
          <div class="instance-picker-pill">
            <span class="instance-picker-label">Target:</span>
            <select
              class="instance-picker-select"
              .value=${selectedInstanceId}
              @change=${this.onInstanceChange}
            >
              ${instances.map(
                (inst) => html`<option value=${inst.id}>${inst.name} (${inst.release})</option>`
              )}
            </select>
          </div>
          <slot></slot>
        </div>
      </div>
      ${this.showLoadError && loadError
        ? html`<div class="badge error" role="alert" style="margin:12px 24px; display:block;">${loadError}</div>`
        : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-workspace-bar': NowWorkspaceBar;
  }
}
