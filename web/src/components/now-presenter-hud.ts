import { LitElement, html, css } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'

export interface RunbookStage {
  step_number: number
  title: string
  persona?: string
  instructions: string[]
  talking_points: string[]
  target_table?: string
  verification_query?: string
}

export interface DemoPersona {
  name: string
  role: string
  email: string
}

export interface RunbookGuide {
  bundle_id: string
  title: string
  narrative: string
  stages: RunbookStage[]
  personas: DemoPersona[]
}

@customElement('now-presenter-hud')
export class NowPresenterHud extends LitElement {
  static styles = css`
    :host {
      display: block;
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 1000;
      font-family: var(--now-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
      color: var(--now-text-primary, #ffffff);
    }

    .hud-card {
      background: var(--now-bg-surface, #1e242b);
      border: 1px solid var(--now-border-color, #2e3742);
      border-radius: 8px;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
      width: 440px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: all 0.2s ease-in-out;
    }

    .safe-harbor-bar {
      background: #0f1318;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding: 6px 14px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      color: #94a3b8;
    }

    .safe-harbor-tag {
      background: rgba(234, 179, 8, 0.15);
      border: 1px solid rgba(234, 179, 8, 0.4);
      color: #facc15;
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 1px 5px;
      border-radius: 3px;
      letter-spacing: 0.5px;
      white-space: nowrap;
    }

    .safe-harbor-text {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .hud-header {
      background: #181d24;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--now-border-color, #2e3742);
    }

    .hud-title-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge-presenter {
      background: #23a17e;
      color: #ffffff;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 6px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }

    .demo-title {
      font-size: 13px;
      font-weight: 600;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 220px;
    }

    .close-btn {
      position: relative;
      background: transparent;
      border: none;
      color: var(--now-text-muted, #8b9baa);
      cursor: pointer;
      padding: 0;
      width: 26px;
      height: 26px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
    }

    .close-btn svg {
      width: 15px;
      height: 15px;
      fill: currentColor;
    }

    .close-btn:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.1);
    }

    .hud-body {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 480px;
      overflow-y: auto;
    }

    .stage-indicator {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: var(--now-text-muted, #8b9baa);
    }

    .stage-title {
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      margin-top: 4px;
    }

    .persona-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(35, 161, 126, 0.12);
      border: 1px solid rgba(35, 161, 126, 0.35);
      color: #38c89b;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11.5px;
      font-weight: 600;
      margin-top: 4px;
    }

    .section-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-text-muted, #8b9baa);
      margin-bottom: 4px;
    }

    .talking-points-list {
      background: #15191f;
      border-left: 3px solid #23a17e;
      padding: 10px 12px;
      border-radius: 0 4px 4px 0;
      margin: 0;
      list-style-type: none;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .talking-points-list li {
      font-size: 12.5px;
      line-height: 1.45;
      color: #e2e8f0;
      display: flex;
      align-items: flex-start;
      gap: 6px;
    }

    .talking-points-list li::before {
      content: '';
      color: #23a17e;
      font-size: 10px;
      margin-top: 2px;
    }

    .instructions-list {
      margin: 0;
      padding-left: 18px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .instructions-list li {
      font-size: 12px;
      color: var(--now-text-secondary, #cbd5e1);
      line-height: 1.4;
    }

    .verification-status {
      font-size: 11.5px;
      padding: 8px 12px;
      border-radius: 4px;
      margin-top: 4px;
    }

    .verification-status.success {
      background: rgba(35, 161, 126, 0.15);
      color: #38c89b;
      border: 1px solid rgba(35, 161, 126, 0.3);
    }

    .verification-status.pending {
      background: rgba(234, 179, 8, 0.12);
      color: #facc15;
      border: 1px solid rgba(234, 179, 8, 0.25);
    }

    .hud-footer {
      background: #181d24;
      padding: 12px 16px;
      border-top: 1px solid var(--now-border-color, #2e3742);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .btn {
      position: relative;
      font-size: 12px;
      font-weight: 600;
      padding: 6px 14px;
      border-radius: 4px;
      cursor: pointer;
      border: none;
      transition: background 0.15s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .btn.icon-btn {
      width: 32px;
      height: 32px;
      padding: 0;
      border-radius: 6px;
    }

    .btn.icon-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }

    .btn-secondary {
      background: #2e3742;
      color: #ffffff;
    }

    .btn-secondary:hover:not(:disabled) {
      background: #3c4755;
    }

    .btn-primary {
      background: #23a17e;
      color: #ffffff;
    }

    .btn-primary:hover:not(:disabled) {
      background: #1e876a;
    }

    .btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  `

  @property({ type: String })
  bundleId = 'sample-ai-assistant'

  @property({ type: Boolean })
  visible = true

  @property({ type: Object })
  runbook: RunbookGuide | null = null

  @state()
  private currentStageIndex = 0

  @state()
  private verifying = false

  @state()
  private verificationMessage: string | null = null

  connectedCallback() {
    super.connectedCallback()
    if (this.visible && !this.runbook) {
      void this.loadRunbook()
    }
  }

  updated(changedProps: Map<string, unknown>) {
    if ((changedProps.has('visible') && this.visible) || changedProps.has('bundleId')) {
      if (this.visible) {
        void this.loadRunbook()
      }
    }
  }

  private async loadRunbook(): Promise<void> {
    const id = this.bundleId || 'sample-ai-assistant'
    try {
      const resp = await fetch(`/api/demos/${id}/runbook`)
      if (resp.ok) {
        this.runbook = (await resp.json()) as RunbookGuide
        this.currentStageIndex = 0
        this.verificationMessage = null
        return
      }
    } catch {
      // Offline preview fallback below
    }

    this.runbook = {
      bundle_id: id,
      title: 'Enterprise AI Copilot & Triage Playbook',
      narrative:
        'Demonstrates declarative Fluent SDK recipes (*.now.ts) and transactional Table API seeding without brittle update sets.',
      personas: [
        { name: 'Amelia Chen', role: 'Clinical Operations Lead', email: 'amelia.chen@example.com' },
      ],
      stages: [
        {
          step_number: 1,
          title: '1. Executive Value & Declarative Recipe Baseline',
          persona: 'Amelia Chen (Clinical Operations Lead)',
          talking_points: [
            'Highlight that this demo was deployed via declarative Fluent SDK recipes (*.now.ts), not captured update sets.',
            'Show real-time telemetry and date-aligned seed records in the workspace.',
          ],
          instructions: [
            'Open the ServiceNow Operations Workspace and review active incident metrics.',
            'Click Verify Stage below to confirm seeded records exist on the target instance.',
          ],
          target_table: 'x_snc_ai_triage_case',
        },
        {
          step_number: 2,
          title: '2. Autonomous Triage & Remediation',
          persona: 'Marcus Vance (Field Reliability Architect)',
          talking_points: [
            'Demonstrate how Otto Copilot correlates anomaly events and recommends immediate action.',
            'Emphasize 1-click snapshot rollback to restore the instance cleanly after the presentation.',
          ],
          instructions: [
            'Trigger the Otto AI agent review flow in the conversation workspace.',
            'Inspect the generated remediation plan and audit trail.',
          ],
          target_table: 'incident',
        },
      ],
    }
    this.currentStageIndex = 0
    this.verificationMessage = null
  }

  private get currentStage(): RunbookStage | null {
    if (!this.runbook || !this.runbook.stages || this.runbook.stages.length === 0) {
      return null
    }
    return this.runbook.stages[this.currentStageIndex] || null
  }

  private handleNext() {
    if (this.runbook && this.currentStageIndex < this.runbook.stages.length - 1) {
      this.currentStageIndex++
      this.verificationMessage = null
    }
  }

  private handlePrev() {
    if (this.currentStageIndex > 0) {
      this.currentStageIndex--
      this.verificationMessage = null
    }
  }

  private async verifyCurrentStage() {
    if (!this.runbook || !this.currentStage) return
    this.verifying = true
    this.verificationMessage = null
    try {
      const resp = await fetch(`/api/demos/${this.runbook.bundle_id}/runbook/verify-stage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          step_number: this.currentStage.step_number,
          fake_mode: true,
        }),
      })
      const data = await resp.json()
      this.verificationMessage = data.message || (data.success ? 'Stage state verified.' : 'Verification failed.')
    } catch (e) {
      this.verificationMessage = `Verification request error: ${e}`
    } finally {
      this.verifying = false
    }
  }

  private handleClose() {
    this.visible = false
    this.dispatchEvent(new CustomEvent('hud-close', { bubbles: true, composed: true }))
    this.dispatchEvent(new CustomEvent('close-hud', { bubbles: true, composed: true }))
  }

  render() {
    if (!this.visible || !this.runbook) {
      return html``
    }

    const stage = this.currentStage
    const totalStages = this.runbook.stages.length

    return html`
      <div class="hud-card">
        <div class="safe-harbor-bar">
          <span class="safe-harbor-tag">Safe Harbor</span>
          <span class="safe-harbor-text">Forward-looking statements subject to change. Internal SC use only.</span>
        </div>
        <div class="hud-header">
          <div class="hud-title-row">
            <span class="badge-presenter">Presenter Mode</span>
            <span class="demo-title">${this.runbook.title}</span>
          </div>
          <button class="close-btn" title="Close Presenter HUD" data-tooltip="Close" @click=${this.handleClose}>
            <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
          </button>
        </div>

        <div class="hud-body">
          <div class="stage-indicator">
            <span>Stage ${this.currentStageIndex + 1} of ${totalStages}</span>
            ${stage?.target_table ? html`<span>Table: <code>${stage.target_table}</code></span>` : ''}
          </div>

          <div class="stage-title">${stage?.title || 'Overview'}</div>

          ${stage?.persona
            ? html`
                <div class="persona-badge">
                  <span>Persona:</span>
                  <strong>${stage.persona}</strong>
                </div>
              `
            : ''}

          ${stage?.talking_points && stage.talking_points.length > 0
            ? html`
                <div>
                  <div class="section-title">Key Value Talking Points</div>
                  <ul class="talking-points-list">
                    ${stage.talking_points.map((tp) => html`<li>${tp}</li>`)}
                  </ul>
                </div>
              `
            : ''}

          ${stage?.instructions && stage.instructions.length > 0
            ? html`
                <div>
                  <div class="section-title">Actions & Steps</div>
                  <ol class="instructions-list">
                    ${stage.instructions.map((inst) => html`<li>${inst}</li>`)}
                  </ol>
                </div>
              `
            : ''}

          ${this.verificationMessage
            ? html`
                <div class="verification-status success">
                  ${this.verificationMessage}
                </div>
              `
            : ''}
        </div>

        <div class="hud-footer">
          <button
            class="btn btn-secondary icon-btn"
            ?disabled=${this.currentStageIndex === 0}
            title="Previous Stage"
            data-tooltip="Previous Stage"
            @click=${this.handlePrev}
          >
            <svg viewBox="0 0 24 24"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>
          </button>

          <button
            class="btn btn-secondary icon-btn"
            ?disabled=${this.verifying}
            title="Verify Stage State"
            data-tooltip="Verify Stage"
            @click=${this.verifyCurrentStage}
          >
            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
          </button>

          <button
            class="btn btn-primary icon-btn"
            ?disabled=${this.currentStageIndex >= totalStages - 1}
            title="Next Stage"
            data-tooltip="Next Stage"
            @click=${this.handleNext}
          >
            <svg viewBox="0 0 24 24"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>
          </button>
        </div>
      </div>
    `
  }
}
