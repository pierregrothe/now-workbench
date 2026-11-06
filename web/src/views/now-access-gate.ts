// web/src/views/now-access-gate.ts
// Full-screen gate: the forced first-run setup dialog, or a no-access page.
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { ottoGlyph } from '../icons.js';

export type GateMode = 'setup' | 'denied' | 'error';

@customElement('now-access-gate')
export class NowAccessGate extends LitElement {
  @property({ type: String }) mode: GateMode = 'setup';
  @property({ type: String }) email = '';
  @property({ type: String }) message = '';
  @state() private code = '';
  @state() private busy = false;
  @state() private error = '';

  static styles = css`
    :host {
      position: fixed;
      inset: 0;
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(22, 24, 29, 0.55);
      font-family: inherit;
    }
    .dialog {
      width: min(440px, calc(100vw - 32px));
      background: #ffffff;
      border-radius: 20px;
      padding: 28px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
    }
    h1 {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 20px;
      font-weight: 600;
      margin: 0 0 8px;
    }
    p {
      font-size: 13.5px;
      color: #4b5563;
      line-height: 1.5;
      margin: 0 0 14px;
    }
    code {
      background: #f3f1ed;
      border-radius: 6px;
      padding: 1px 6px;
      font-size: 12.5px;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 12.5px;
      font-weight: 600;
    }
    input {
      border: 1px solid rgba(0, 0, 0, 0.16);
      border-radius: 10px;
      padding: 10px 12px;
      font: inherit;
      font-size: 16px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    button {
      margin-top: 16px;
      width: 100%;
      border: none;
      border-radius: 999px;
      padding: 11px;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
      background: #1a4d63;
      color: #ffffff;
    }
    button:disabled {
      opacity: 0.55;
      cursor: default;
    }
    .error {
      color: #b91c1c;
      font-size: 12.5px;
      margin-top: 10px;
    }
  `;

  private async submit(e: Event): Promise<void> {
    e.preventDefault();
    this.busy = true;
    this.error = '';
    try {
      const res = await fetch('/api/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: this.code }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error((body as { detail?: string }).detail || `Setup failed (HTTP ${res.status})`);
      }
      this.dispatchEvent(new CustomEvent('setup-complete', { bubbles: true, composed: true }));
    } catch (err) {
      this.error = (err as Error).message;
      this.code = '';
    } finally {
      this.busy = false;
    }
  }

  render() {
    if (this.mode !== 'setup') {
      return html`
        <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="gate-title">
          <h1 id="gate-title">${ottoGlyph(22)} ${this.mode === 'denied' ? 'No access yet' : 'Cannot reach the workbench'}</h1>
          <p>
            ${this.mode === 'denied'
              ? html`You are signed in as <strong>${this.email}</strong>, but this account has no role here. Ask an administrator to add you on the Team page.`
              : this.message}
          </p>
        </div>
      `;
    }
    return html`
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="gate-title" @submit=${this.submit}>
        <h1 id="gate-title">${ottoGlyph(22)} Set up this workbench</h1>
        <p>You are signed in as <strong>${this.email}</strong>. Enter the setup code from the server log to become its administrator.</p>
        <p>On the server: <code>docker logs now-workbench</code>, look for <code>FIRST-RUN SETUP CODE</code>.</p>
        <label>Setup code
          <input name="code" autocomplete="one-time-code" maxlength="12" placeholder="ABCD-EFGH" required .value=${this.code} @input=${(e: Event) => (this.code = (e.target as HTMLInputElement).value)} />
        </label>
        ${this.error ? html`<div class="error" role="alert">${this.error}</div>` : ''}
        <button type="submit" ?disabled=${this.busy || this.code.trim().length < 8}>Become administrator</button>
      </form>
    `;
  }
}
