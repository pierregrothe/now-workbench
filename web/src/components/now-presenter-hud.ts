import { LitElement, html } from 'lit'
import { customElement, property, state } from 'lit/decorators.js'
import { presenterHudStyles } from './now-presenter-hud-styles.js'

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
  static styles = presenterHudStyles

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

  @state()
  private verificationOk = false

  @state()
  private loadError: string | null = null

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
    this.loadError = null
    try {
      const resp = await fetch(`/api/demos/${id}/runbook`)
      if (resp.ok) {
        this.runbook = (await resp.json()) as RunbookGuide
        this.currentStageIndex = 0
        this.verificationMessage = null
        return
      }
      this.runbook = null
      this.loadError =
        resp.status === 404
          ? 'No walkthrough guide for this demo'
          : `Could not load runbook: ${await this.errorDetail(resp)}`
    } catch (e) {
      this.runbook = null
      this.loadError = `Could not load runbook: ${e instanceof Error ? e.message : String(e)}`
    }
    this.currentStageIndex = 0
    this.verificationMessage = null
  }

  private async errorDetail(resp: Response): Promise<string> {
    try {
      const body = (await resp.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') return body.detail
    } catch {
      // body is not JSON; fall back to the status line
    }
    return `HTTP ${resp.status}`
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
    this.verificationOk = false
    try {
      const resp = await fetch(`/api/demos/${this.runbook.bundle_id}/runbook/verify-stage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step_number: this.currentStage.step_number }),
      })
      if (!resp.ok) {
        this.verificationMessage = `Verification failed: ${await this.errorDetail(resp)}`
        return
      }
      const data = (await resp.json()) as { success?: boolean; message?: string }
      this.verificationOk = data.success === true
      this.verificationMessage =
        data.message || (this.verificationOk ? 'Stage state verified.' : 'Verification failed.')
    } catch (e) {
      this.verificationMessage = `Verification failed: ${e instanceof Error ? e.message : String(e)}`
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
    if (this.visible && !this.runbook && this.loadError) {
      return html`
        <div class="hud-card">
          <div class="hud-body">
            <div class="verification-status pending" data-testid="hud-load-error" role="alert">
              ${this.loadError}
            </div>
          </div>
        </div>
      `
    }
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
                <div
                  class="verification-status ${this.verificationOk ? 'success' : 'pending'}"
                  data-testid="hud-verification-message"
                >
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
