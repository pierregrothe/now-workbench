// web/src/views/now-synthesizer-view.ts
// Use-Case Synthesizer view: dynamic domain synthesis, code preview, and 1-click seeding.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { DemoPipelineController } from '../controllers/demo-pipeline-controller.js';
import { workbenchStore } from '../context/workbench-context.js';
import type { WorkbenchState } from '../context/workbench-context.js';
import { workspaceStyles } from '../styles/workspace-styles.js';

@customElement('now-synthesizer-view')
export class NowSynthesizerView extends LitElement {
  private pipeline = new DemoPipelineController(this);
  private unsubscribeStore?: () => void;

  @state() private currentStoreState: WorkbenchState = workbenchStore.state;
  @state() private useCasePrompt =
    'Build an Enterprise Clinical Trial Patient Adverse Event Tracking application with strict HIPAA auditing, safety review workflows, and automatic FDA medwatch escalation.';
  @state() private customerName = 'Novartis BioHealth';
  @state() private industry = 'Healthcare & Life Sciences';
  @state() private personaPrimary = 'Amelia Chen (Clinical Operations Lead)';
  @state() private personaSecondary = 'Marcus Vance (Field Reliability Architect)';

  @property({ type: String })
  set incomingPrompt(val: string) {
    if (val && val.trim()) {
      this.useCasePrompt = val;
    }
  }

  static styles = [
    workspaceStyles,
    css`
      .synth-grid {
        display: grid;
        grid-template-columns: 420px 1fr;
        gap: 24px;
        align-items: start;
      }

      .form-group {
        margin-bottom: 16px;
      }

      .form-label {
        display: block;
        font-size: 12px;
        font-weight: 600;
        color: var(--now-text-secondary, #4b5563);
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .text-input, .select-input, .textarea-input {
        width: 100%;
        box-sizing: border-box;
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid var(--now-border-subtle, #d1d5db);
        background: var(--now-bg-surface-0, #ffffff);
        color: var(--now-text-primary, #111827);
        font-size: 13px;
        font-family: inherit;
      }

      .textarea-input {
        min-height: 110px;
        resize: vertical;
        line-height: 1.45;
      }

      .action-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 20px;
      }

      .primary-action-btn {
        padding: 10px 20px;
        background: var(--now-color-primary, #032d42);
        color: #ffffff;
        font-weight: 700;
        font-size: 13px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        transition: background 0.15s ease;
      }

      .primary-action-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .tabs-bar {
        display: flex;
        gap: 4px;
        border-bottom: 1px solid var(--now-border-subtle, #e5e7eb);
        margin-bottom: 16px;
      }

      .tab-item {
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 600;
        color: var(--now-text-secondary, #6b7280);
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        cursor: pointer;
      }

      .tab-item.active {
        color: var(--now-color-primary, #032d42);
        border-bottom-color: var(--now-color-primary, #032d42);
      }

      .code-preview {
        background: #0f172a;
        color: #f8fafc;
        border-radius: 8px;
        padding: 16px;
        font-family: monospace;
        font-size: 12px;
        overflow-x: auto;
        white-space: pre-wrap;
      }

      .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: var(--now-text-secondary, #6b7280);
      }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    this.unsubscribeStore = workbenchStore.subscribe((state) => {
      this.currentStoreState = state;
    });
    workbenchStore.loadInstances();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribeStore?.();
  }

  private async handleSynthesize(): Promise<void> {
    await this.pipeline.synthesize({
      prompt: this.useCasePrompt,
      customerName: this.customerName,
      industry: this.industry,
      instanceId: this.currentStoreState.selectedInstanceId,
      personas: [this.personaPrimary, this.personaSecondary],
    });
  }

  private async handleSeed(): Promise<void> {
    await this.pipeline.seedDemo(undefined, this.currentStoreState.selectedInstanceId);
  }

  private handleInstanceChange(e: Event): void {
    const val = (e.target as HTMLSelectElement).value;
    workbenchStore.setState({ selectedInstanceId: val });
  }

  render() {
    const res = this.pipeline.synthesizedResult;

    return html`
      <div class="top-utility-bar">
        <div class="workspace-breadcrumb">
          <span class="status-dot"></span>
          <span>Now Workbench</span>
          <span style="color: #9ca3af;">/</span>
          <span>Use-Case Synthesizer</span>
        </div>
        <div class="utility-actions">
          <div class="instance-picker-pill">
            <span class="instance-picker-label">Target:</span>
            <select
              class="instance-picker-select"
              .value=${this.currentStoreState.selectedInstanceId}
              @change=${this.handleInstanceChange}
            >
              ${this.currentStoreState.instances.map(
                (inst) => html`<option value=${inst.id}>${inst.name} (${inst.release})</option>`
              )}
            </select>
          </div>
        </div>
      </div>

      <div class="scroll-canvas">
        <div class="canvas-container">
          <h2 class="section-title">AI Use-Case Synthesizer</h2>
          <p class="section-subtitle">
            Generate production-ready ServiceNow Fluent application bundles, test personas, and seed data from natural language.
          </p>

          <div class="synth-grid">
            <div class="card">
              <div class="form-group">
                <label class="form-label">Demo Prompt / Objective</label>
                <textarea
                  class="textarea-input"
                  .value=${this.useCasePrompt}
                  @input=${(e: Event) => (this.useCasePrompt = (e.target as HTMLTextAreaElement).value)}
                ></textarea>
              </div>

              <div class="form-group">
                <label class="form-label">Customer Name</label>
                <input
                  type="text"
                  class="text-input"
                  .value=${this.customerName}
                  @input=${(e: Event) => (this.customerName = (e.target as HTMLInputElement).value)}
                />
              </div>

              <div class="form-group">
                <label class="form-label">Target Industry</label>
                <select
                  class="select-input"
                  .value=${this.industry}
                  @change=${(e: Event) => (this.industry = (e.target as HTMLSelectElement).value)}
                >
                  <option value="Healthcare & Life Sciences">Healthcare & Life Sciences</option>
                  <option value="Financial Services">Financial Services</option>
                  <option value="Telecommunications">Telecommunications</option>
                  <option value="Manufacturing">Manufacturing</option>
                  <option value="Public Sector">Public Sector</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">Primary Persona</label>
                <input
                  type="text"
                  class="text-input"
                  .value=${this.personaPrimary}
                  @input=${(e: Event) => (this.personaPrimary = (e.target as HTMLInputElement).value)}
                />
              </div>

              <div class="action-row">
                <button
                  class="primary-action-btn"
                  ?disabled=${this.pipeline.isSynthesizing}
                  @click=${this.handleSynthesize}
                >
                  ${this.pipeline.isSynthesizing ? 'Synthesizing Bundle...' : 'Synthesize Demo Bundle'}
                </button>
              </div>
            </div>

            <div class="card">
              ${res
                ? html`
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                      <div>
                        <h3 style="margin:0 0 4px 0; font-size:16px;">${res.title || res.customer_name}</h3>
                        <span class="badge info">${res.fluent_table_name}</span>
                      </div>
                      <button
                        class="primary-action-btn"
                        ?disabled=${this.pipeline.isSeeding}
                        @click=${this.handleSeed}
                      >
                        ${this.pipeline.isSeeding ? 'Seeding...' : '1-Click Seed Target'}
                      </button>
                    </div>

                    ${this.pipeline.seedStatusMessage
                      ? html`<div class="badge success" style="margin-bottom:12px; display:block;">${this.pipeline.seedStatusMessage}</div>`
                      : ''}

                    <div class="tabs-bar">
                      <button
                        class="tab-item ${this.pipeline.activeResultTab === 'narrative' ? 'active' : ''}"
                        @click=${() => this.pipeline.setResultTab('narrative')}
                      >
                        Narrative & Story
                      </button>
                      <button
                        class="tab-item ${this.pipeline.activeResultTab === 'datasets' ? 'active' : ''}"
                        @click=${() => this.pipeline.setResultTab('datasets')}
                      >
                        Seed Records (${res.seed_records?.length ?? 0})
                      </button>
                      <button
                        class="tab-item ${this.pipeline.activeResultTab === 'customizations' ? 'active' : ''}"
                        @click=${() => this.pipeline.setResultTab('customizations')}
                      >
                        Fluent Code
                      </button>
                    </div>

                    ${this.pipeline.activeResultTab === 'narrative'
                      ? html`<div style="font-size:13px; line-height:1.6; white-space:pre-wrap;">${res.narrative_markdown}</div>`
                      : ''}
                    ${this.pipeline.activeResultTab === 'datasets'
                      ? html`<pre class="code-preview">${JSON.stringify(res.seed_records, null, 2)}</pre>`
                      : ''}
                    ${this.pipeline.activeResultTab === 'customizations'
                      ? html`<pre class="code-preview">${res.fluent_code}</pre>`
                      : ''}
                  `
                : html`
                    <div class="empty-state">
                      <p style="font-size: 15px; font-weight: 600; margin-bottom: 8px;">No Synthesized Bundle Yet</p>
                      <p style="font-size: 13px;">Configure your use-case objective on the left and synthesize a full declarative bundle.</p>
                    </div>
                  `}
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
