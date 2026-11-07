import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { welcomeModalStyles } from './now-welcome-modal-styles.js';

interface WelcomeSection {
  id: string;
  label: string;
  title: string;
  description: string;
  badgeText: string;
  targetTab: string;
}

const SECTIONS: WelcomeSection[] = [
  {
    id: 'overview',
    label: 'Overview',
    title: 'Experience Now Workbench',
    description:
      'Now Workbench, our newly reimagined Solution Consultant & Developer experience, unifies conversational intent routing, Use-Case-to-Demo synthesis, ServiceNow Fluent SDK (.now.ts) customizations, and automated instance media capture in one intuitive workspace.',
    badgeText: 'Conversational Demo & SDK Studio',
    targetTab: 'home',
  },
  {
    id: 'conversational-ai',
    label: 'Conversational AI',
    title: 'Use-Case-to-Demo Synthesizer',
    description:
      'Describe any customer use case and industry context in natural language. Now Workbench automatically synthesizes multi-table seed datasets, Fluent SDK (.now.ts) customizations, and a tailored Solution Consultant demo narrative.',
    badgeText: 'Autonomous Use-Case Synthesis',
    targetTab: 'synthesizer',
  },
  {
    id: 'help-center',
    label: 'SC Narrative & HUD',
    title: 'Solution Consultant Demo Narrative',
    description:
      'Every synthesized use case produces a structured Solution Consultant playbook with executive value pitches, persona journeys, step-by-step UI navigation paths, and talking points to help you deliver a compelling live demo.',
    badgeText: 'Guided SC Walkthrough & Presenter HUD',
    targetTab: 'synthesizer',
  },
  {
    id: 'canvas',
    label: 'Media Capture',
    title: 'Instance Screenshot & Video Capture',
    description:
      'Capture high-resolution screenshots (.png) and walkthrough videos (.webm) of your live ServiceNow instance directly from Now Workbench directly from the workspace, and embed them straight into your portable .sn-demo.zip bundle.',
    badgeText: 'Automated Instance Media Capture',
    targetTab: 'capture',
  },
  {
    id: 'resources',
    label: 'Fluent & Bundles',
    title: 'Portable Bundles & Transactional Seeding',
    description:
      'Package your Fluent SDK customizations, seed datasets, instance captures, and SC narrative into a self-contained bundle with one-click transactional seeding and snapshot-backed instance rollback.',
    badgeText: 'Fluent SDK & Snapshot Lifecycle',
    targetTab: 'artifacts',
  },
];

@customElement('now-welcome-modal')
export class NowWelcomeModal extends LitElement {
  static styles = welcomeModalStyles;

  @property({ type: Boolean }) open = false;
  @state() private activeSectionId = 'overview';
  @state() private dontShowAgain = false;
  @state() private saveError = '';

  connectedCallback(): void {
    super.connectedCallback();
    this.dontShowAgain = localStorage.getItem('now-workbench-show-welcome') === 'false';
  }

  private close(): void {
    this.open = false;
    this.dispatchEvent(new CustomEvent('modal-close', { bubbles: true, composed: true }));
  }

  private get currentSectionIndex(): number {
    return SECTIONS.findIndex((s) => s.id === this.activeSectionId);
  }

  private handleNext(): void {
    const idx = this.currentSectionIndex;
    if (idx < SECTIONS.length - 1) {
      this.activeSectionId = SECTIONS[idx + 1].id;
    } else {
      this.openSectionTab();
    }
  }

  private handlePrevious(): void {
    const idx = this.currentSectionIndex;
    if (idx > 0) {
      this.activeSectionId = SECTIONS[idx - 1].id;
    }
  }

  private async handleCheckboxChange(e: Event): Promise<void> {
    const checked = (e.target as HTMLInputElement).checked;
    this.dontShowAgain = checked;
    localStorage.setItem('now-workbench-show-welcome', checked ? 'false' : 'true');
    this.saveError = '';
    // This browser remembers the choice either way; the account setting is saved first, and a
    // failure keeps the guide open with the reason instead of closing as if it had worked.
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ show_welcome_on_startup: !checked }),
      });
      if (!res.ok) {
        this.saveError = `Could not save this choice for your account (HTTP ${res.status}).`;
        return;
      }
    } catch (err) {
      this.saveError = `Could not save this choice for your account: ${err instanceof Error ? err.message : String(err)}`;
      return;
    }
    this.dispatchEvent(
      new CustomEvent('show-welcome-change', {
        detail: { showOnStartup: !checked },
        bubbles: true,
        composed: true,
      })
    );
  }

  private openSectionTab(): void {
    const targetTab = this.activeSection.targetTab;
    this.open = false;
    this.dispatchEvent(
      new CustomEvent('modal-navigate', {
        detail: { tab: targetTab },
        bubbles: true,
        composed: true,
      })
    );
  }

  private get activeSection(): WelcomeSection {
    return SECTIONS.find((s) => s.id === this.activeSectionId) ?? SECTIONS[0];
  }

  render() {
    if (!this.open) {
      return html``;
    }

    const current = this.activeSection;

    return html`
      <div class="backdrop" @click=${this.close}>
        <div
          class="modal"
          role="dialog"
          aria-modal="true"
          aria-label="Welcome to Now Workbench"
          @click=${(e: Event) => e.stopPropagation()}
        >
          <div class="modal-sidebar">
            <div class="new-pill">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z"/>
              </svg>
              <span>New</span>
            </div>

            <h2 class="modal-heading">Welcome to Now Workbench</h2>

            <div class="tab-list" role="tablist">
              ${SECTIONS.map(
                (section) => html`
                  <button
                    role="tab"
                    aria-selected=${this.activeSectionId === section.id}
                    class="tab-btn ${this.activeSectionId === section.id ? 'active' : ''}"
                    @click=${() => {
                      this.activeSectionId = section.id;
                    }}
                  >
                    ${section.label}
                  </button>
                `
              )}
            </div>

            <div class="sidebar-footer">
              <span class="step-counter">Step ${this.currentSectionIndex + 1} of ${SECTIONS.length}</span>
              <button
                class="pill-btn secondary"
                style="padding: 4px 10px; font-size: 11.5px;"
                @click=${this.close}
                title="Skip tour and enter workbench"
              >
                Skip Tour
              </button>
            </div>
          </div>

          <div class="modal-body">
            <div class="visual-stage">
              <button class="close-icon-btn" title="Close dialog" data-tooltip="Close" @click=${this.close}>
                <svg viewBox="0 0 24 24">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>

              <div class="preview-card">
                <div class="preview-card-top">
                  <div class="preview-brand">
                    <span class="preview-dot"></span>
                    <span>Now Workbench</span>
                  </div>
                  <span class="preview-badge">${current.badgeText}</span>
                </div>

                <div class="preview-skeleton">
                  <div class="skeleton-line w-70"></div>
                  <div class="skeleton-line w-90"></div>
                  <div class="skeleton-line w-55"></div>
                </div>

                <div class="preview-cards-row">
                  <div class="mini-tile">
                    Use-Case Synthesis
                    <span>Fluent .now.ts + Seed JSON</span>
                  </div>
                  <div class="mini-tile">
                    SC Demo Narrative
                    <span>Executive Pitch & Steps</span>
                  </div>
                  <div class="mini-tile">
                    Media Capture
                    <span>Instance PNG & WebM</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="narrative-pane">
              <h3 class="narrative-title">${current.title}</h3>
              <p class="narrative-desc">${current.description}</p>

              <div class="modal-nav-row">
                <label class="dont-show-checkbox">
                  <input
                    type="checkbox"
                    .checked=${this.dontShowAgain}
                    @change=${(e: Event) => void this.handleCheckboxChange(e)}
                  />
                  <span>Don't show this welcome guide on startup</span>
                </label>
                ${this.saveError ? html`<span class="save-error" role="alert">${this.saveError}</span>` : ''}

                <div class="nav-buttons-group">
                  ${this.currentSectionIndex > 0
                    ? html`
                        <button class="pill-btn secondary" @click=${this.handlePrevious}>
                          Back
                        </button>
                      `
                    : ''}

                  <button class="pill-btn primary" @click=${this.handleNext}>
                    ${this.currentSectionIndex === SECTIONS.length - 1 ? 'Get Started' : 'Next'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
