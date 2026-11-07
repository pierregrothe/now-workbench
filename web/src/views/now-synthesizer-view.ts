// web/src/views/now-synthesizer-view.ts
// Use-Case Synthesizer view: dynamic domain synthesis, code preview, and 1-click seeding.
// Author: Pierre Grothe
// Date: 2026-10-31

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { DemoPipelineController } from '../controllers/demo-pipeline-controller.js';
import { workbenchStore } from '../context/workbench-context.js';
import { workspaceStyles } from '../styles/workspace-styles.js';
import { synthesizerViewStyles } from './now-synthesizer-view-styles.js';
import { StoreController } from '../controllers/store-controller.js';
import './now-workspace-bar.js';

@customElement('now-synthesizer-view')
export class NowSynthesizerView extends LitElement {
  private pipeline = new DemoPipelineController(this);

  private readonly store = new StoreController(this);
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

  static styles = [workspaceStyles, synthesizerViewStyles];

  connectedCallback(): void {
    super.connectedCallback();
    workbenchStore.loadInstances();
  }


  private async handleSynthesize(): Promise<void> {
    await this.pipeline.synthesize({
      prompt: this.useCasePrompt,
      customerName: this.customerName,
      industry: this.industry,
      instanceId: this.store.state.selectedInstanceId,
      personas: [this.personaPrimary, this.personaSecondary],
    });
  }

  private async handleSeed(): Promise<void> {
    await this.pipeline.seedDemo(undefined, this.store.state.selectedInstanceId);
  }


  render() {
    const res = this.pipeline.synthesizedResult;

    return html`
      <now-workspace-bar crumb="Use-Case Synthesizer" show-load-error></now-workspace-bar>

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
              ${this.pipeline.error
                ? html`<div class="badge error form-alert" role="alert">${this.pipeline.error}</div>`
                : ''}
            </div>

            <div class="card">
              ${res
                ? html`
                    <div class="result-head">
                      <div>
                        <h3 class="result-title">${res.title || res.customer_name}</h3>
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
                      ? html`<div class="badge seed-status ${this.pipeline.seedFailed ? 'error' : this.pipeline.isSeeding ? 'info' : 'success'}">${this.pipeline.seedStatusMessage}</div>`
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
                      ? html`<div class="narrative">${res.narrative_markdown}</div>`
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
                      <p class="empty-title">No Synthesized Bundle Yet</p>
                      <p class="empty-hint">Configure your use-case objective on the left and synthesize a full declarative bundle.</p>
                    </div>
                  `}
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
