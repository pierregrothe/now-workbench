import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

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
  static styles = css`
    :host {
      display: block;
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .backdrop {
      position: fixed;
      inset: 0;
      background: rgba(15, 20, 25, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2000;
      padding: 24px;
    }

    .modal {
      width: 920px;
      max-width: 96vw;
      height: 600px;
      max-height: 90vh;
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: 16px;
      box-shadow: 0 24px 64px rgba(0, 0, 0, 0.22);
      display: grid;
      grid-template-columns: 320px 1fr;
      overflow: hidden;
      position: relative;
    }

    .modal-sidebar {
      background: var(--now-bg-surface-0, #ffffff);
      padding: 36px 24px 28px 28px;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--now-border-subtle, #ececeb);
    }

    .new-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      align-self: flex-start;
      background: #dbeafe;
      color: #1d4ed8;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 999px;
      margin-bottom: 14px;
    }

    .new-pill svg {
      width: 13px;
      height: 13px;
      fill: currentColor;
    }

    .modal-heading {
      font-size: 24px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      line-height: 1.25;
      letter-spacing: -0.02em;
      margin: 0 0 28px 0;
    }

    .tab-list {
      display: flex;
      flex-direction: column;
      gap: 2px;
      flex: 1;
    }

    .tab-btn {
      appearance: none;
      border: none;
      border-left: 4px solid transparent;
      background: transparent;
      text-align: left;
      padding: 13px 16px;
      font-size: 14.5px;
      font-weight: 400;
      color: var(--now-text-secondary, #2c2e33);
      cursor: pointer;
      transition: background 0.12s ease, color 0.12s ease;
      font-family: inherit;
    }

    .tab-btn:hover {
      background: var(--now-bg-surface-1, #f6f6f5);
    }

    .tab-btn.active {
      border-left-color: var(--now-color-brand-green, #62d84e);
      background: var(--now-bg-surface-1, #f1f2f1);
      font-weight: 600;
      color: var(--now-text-primary, #0b0f19);
    }

    .sidebar-footer {
      padding-top: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .enter-btn {
      position: relative;
      appearance: none;
      border: 1px solid var(--now-color-brand-green, #62d84e);
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      font-size: 13px;
      font-weight: 600;
      padding: 9px 18px;
      border-radius: 999px;
      cursor: pointer;
      transition: background 0.12s ease;
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .enter-btn.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      border-radius: 50%;
    }

    .enter-btn.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .enter-btn:hover {
      opacity: 0.9;
    }

    .modal-body {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--now-bg-surface-0, #ffffff);
    }

    .visual-stage {
      flex: 1;
      background: var(--now-bg-canvas, #f2f2ef);
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 28px 36px 0 36px;
      overflow: hidden;
    }

    .close-icon-btn {
      position: absolute;
      top: 16px;
      right: 16px;
      width: 32px;
      height: 32px;
      border-radius: 999px;
      border: none;
      background: var(--now-bg-surface-0, rgba(255, 255, 255, 0.85));
      color: var(--now-text-secondary, #4b5563);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 5;
      transition: background 0.12s ease, color 0.12s ease;
    }

    .close-icon-btn:hover {
      background: var(--now-bg-surface-1, #ffffff);
      color: var(--now-text-primary, #0b0f19);
    }

    .close-icon-btn svg {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      stroke-width: 2;
      fill: none;
    }

    .preview-card {
      width: 100%;
      height: 100%;
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: 14px 14px 0 0;
      box-shadow: 0 8px 30px var(--now-shadow-soft, rgba(0, 0, 0, 0.06));
      padding: 24px 28px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .preview-card-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--now-border-subtle, #f0f0ee);
      padding-bottom: 14px;
    }

    .preview-brand {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
    }

    .preview-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--now-color-brand-green, #62d84e);
    }

    .preview-badge {
      font-size: 11px;
      font-weight: 600;
      color: var(--now-text-primary, #032d42);
      background: var(--now-bg-surface-1, #e8f5e9);
      padding: 3px 9px;
      border-radius: 999px;
    }

    .preview-skeleton {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 18px;
    }

    .skeleton-line {
      height: 10px;
      border-radius: 6px;
      background: var(--now-bg-surface-1, #f3f4f3);
    }

    .skeleton-line.w-70 {
      width: 70%;
    }

    .skeleton-line.w-90 {
      width: 90%;
    }

    .skeleton-line.w-55 {
      width: 55%;
    }

    .preview-cards-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: auto;
      padding-top: 16px;
    }

    .mini-tile {
      background: var(--now-bg-surface-1, #fafaf9);
      border: 1px solid var(--now-border-subtle, #ececea);
      border-radius: 8px;
      padding: 10px;
      font-size: 11px;
      font-weight: 600;
      color: var(--now-text-primary, #374151);
    }

    .mini-tile span {
      display: block;
      font-size: 10px;
      font-weight: 400;
      color: var(--now-text-secondary, #6b7280);
      margin-top: 3px;
    }

    .narrative-pane {
      border-top: 1px solid var(--now-border-subtle, #e5e5e3);
      padding: 24px 32px 24px 32px;
      background: var(--now-bg-surface-0, #ffffff);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .narrative-title {
      font-size: 20px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
      letter-spacing: -0.015em;
    }

    .narrative-desc {
      font-size: 14px;
      line-height: 1.55;
      color: var(--now-text-secondary, #374151);
      margin: 0;
    }

    .modal-nav-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--now-border-subtle, #f0f0ee);
      gap: 12px;
    }

    .dont-show-checkbox {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 12.5px;
      color: var(--now-text-secondary, #475467);
      cursor: pointer;
      user-select: none;
    }

    .dont-show-checkbox input[type="checkbox"] {
      width: 16px;
      height: 16px;
      accent-color: var(--now-color-brand-green, #23a17e);
      cursor: pointer;
    }

    .nav-buttons-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .pill-btn {
      appearance: none;
      border: 1px solid var(--now-border-medium, #cbd5e1);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #0f172a);
      font-size: 13px;
      font-weight: 600;
      padding: 7px 18px;
      border-radius: 999px;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.12s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .pill-btn:hover {
      background: var(--now-bg-surface-1, #f8fafc);
      border-color: var(--now-border-subtle, #94a3b8);
    }

    .pill-btn.primary {
      background: var(--now-color-brand-green, #23a17e);
      color: #ffffff;
      border-color: var(--now-color-brand-green, #23a17e);
    }

    .pill-btn.primary:hover {
      background: var(--now-color-brand-green-hover, #1b8567);
      border-color: var(--now-color-brand-green-hover, #1b8567);
    }

    .pill-btn.secondary {
      background: var(--now-bg-surface-1, #f1f5f9);
      border-color: var(--now-border-subtle, #e2e8f0);
      color: var(--now-text-secondary, #475467);
    }

    .step-counter {
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-muted, #64748b);
    }
  `;

  @property({ type: Boolean }) open = false;
  @state() private activeSectionId = 'overview';
  @state() private dontShowAgain = false;

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

  private handleCheckboxChange(e: Event): void {
    const checked = (e.target as HTMLInputElement).checked;
    this.dontShowAgain = checked;
    localStorage.setItem('now-workbench-show-welcome', checked ? 'false' : 'true');
    void fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ show_welcome_on_startup: !checked }),
    }).catch(() => {
      // offline fallback
    });
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
                    @change=${this.handleCheckboxChange}
                  />
                  <span>Don't show this welcome guide on startup</span>
                </label>

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
