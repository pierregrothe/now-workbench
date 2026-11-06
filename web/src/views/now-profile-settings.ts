// web/src/views/now-profile-settings.ts
// Profile settings: picture or built-in avatar, servicenow.com email approved by a code, SMTP.
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { workbenchStore } from '../context/workbench-context.js';
import { PRESETS, presetDataUrl, renderAvatar } from '../profile/avatars.js';
import type { ProfileData } from '../profile/avatars.js';
import { profileSettingsStyles } from './profile-settings-styles.js';

interface MailSettings {
  host: string;
  port: number;
  username: string;
  from_address: string;
  starttls: boolean;
  has_password: boolean;
}

type Notice = { kind: 'ok' | 'error'; text: string } | null;

const MAX_BYTES = 2 * 1024 * 1024;
const TYPES = ['image/png', 'image/jpeg', 'image/webp'];

async function detail(res: Response, fallback: string): Promise<string> {
  const body = await res.json().catch(() => ({}));
  const d = (body as { detail?: unknown }).detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d) && d.length > 0) {
    return String((d[0] as { msg?: string }).msg ?? fallback).replace(/^Value error, /, '');
  }
  return `${fallback} (HTTP ${res.status})`;
}

@customElement('now-profile-settings')
export class NowProfileSettings extends LitElement {
  static styles = profileSettingsStyles;

  @state() private profile: ProfileData | null = null;
  @state() private name = '';
  @state() private email = '';
  @state() private code = '';
  @state() private mail: MailSettings | null = null;
  @state() private smtpPassword = '';
  @state() private avatarNotice: Notice = null;
  @state() private detailsNotice: Notice = null;
  @state() private mailNotice: Notice = null;
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const [p, m] = await Promise.all([fetch('/api/profile'), fetch('/api/profile/mail')]);
      if (!p.ok || !m.ok) throw new Error(`HTTP ${p.ok ? m.status : p.status}`);
      this.applyProfile((await p.json()) as ProfileData);
      this.mail = (await m.json()) as MailSettings;
    } catch (err) {
      this.detailsNotice = { kind: 'error', text: `Could not load your profile: ${String(err)}` };
    }
  }

  private applyProfile(profile: ProfileData): void {
    this.profile = profile;
    this.name = profile.display_name;
    this.email = profile.email;
    workbenchStore.setState({ profile });
  }

  private async call(url: string, init: RequestInit, fallback: string): Promise<Response> {
    this.busy = true;
    try {
      const res = await fetch(url, init);
      if (!res.ok) throw new Error(await detail(res, fallback));
      return res;
    } finally {
      this.busy = false;
    }
  }

  private json(method: string, body: unknown): RequestInit {
    return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  }

  private async choosePreset(id: string): Promise<void> {
    try {
      const res = await this.call('/api/profile/avatar/preset', this.json('PUT', { preset: id }), 'Could not set the avatar');
      this.applyProfile((await res.json()) as ProfileData);
      this.avatarNotice = null;
    } catch (err) {
      this.avatarNotice = { kind: 'error', text: (err as Error).message };
    }
  }

  private async onFile(e: Event): Promise<void> {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    if (!TYPES.includes(file.type)) {
      this.avatarNotice = { kind: 'error', text: 'Use a PNG, JPEG or WebP picture.' };
      return;
    }
    if (file.size > MAX_BYTES) {
      this.avatarNotice = { kind: 'error', text: 'The picture is larger than 2 MB.' };
      return;
    }
    try {
      const res = await this.call('/api/profile/avatar', { method: 'PUT', headers: { 'Content-Type': file.type }, body: file }, 'Could not upload the picture');
      this.applyProfile((await res.json()) as ProfileData);
      this.avatarNotice = { kind: 'ok', text: 'Picture updated.' };
    } catch (err) {
      this.avatarNotice = { kind: 'error', text: (err as Error).message };
    }
  }

  private async removeAvatar(): Promise<void> {
    try {
      const res = await this.call('/api/profile/avatar', { method: 'DELETE' }, 'Could not remove the picture');
      this.applyProfile((await res.json()) as ProfileData);
      this.avatarNotice = null;
    } catch (err) {
      this.avatarNotice = { kind: 'error', text: (err as Error).message };
    }
  }

  private async saveDetails(): Promise<void> {
    try {
      const res = await this.call('/api/profile', this.json('PUT', { display_name: this.name, email: this.email }), 'Could not save your profile');
      this.applyProfile((await res.json()) as ProfileData);
      this.detailsNotice = { kind: 'ok', text: 'Profile saved.' };
    } catch (err) {
      this.detailsNotice = { kind: 'error', text: (err as Error).message };
    }
  }

  private async sendCode(): Promise<void> {
    try {
      const res = await this.call('/api/profile/verification/send', { method: 'POST' }, 'Could not send the code');
      const sent = (await res.json()) as { sent_to: string };
      await this.load();
      this.detailsNotice = { kind: 'ok', text: `Code sent to ${sent.sent_to}. It is valid for 10 minutes.` };
    } catch (err) {
      this.detailsNotice = { kind: 'error', text: (err as Error).message };
    }
  }

  private async confirmCode(): Promise<void> {
    try {
      const res = await this.call('/api/profile/verification/confirm', this.json('POST', { code: this.code }), 'Could not confirm the code');
      this.code = '';
      this.applyProfile((await res.json()) as ProfileData);
      this.detailsNotice = { kind: 'ok', text: 'Email approved.' };
    } catch (err) {
      this.detailsNotice = { kind: 'error', text: (err as Error).message };
      await this.load();
    }
  }

  private async saveMail(): Promise<void> {
    const m = this.mail;
    if (!m) return;
    const body: Record<string, unknown> = { host: m.host, port: Number(m.port), username: m.username, from_address: m.from_address, starttls: m.starttls };
    if (this.smtpPassword) body.password = this.smtpPassword;
    try {
      const res = await this.call('/api/profile/mail', this.json('PUT', body), 'Could not save email delivery settings');
      this.mail = (await res.json()) as MailSettings;
      this.smtpPassword = '';
      await this.load();
      this.mailNotice = { kind: 'ok', text: 'Email delivery settings saved.' };
    } catch (err) {
      this.mailNotice = { kind: 'error', text: (err as Error).message };
    }
  }

  private setMail<K extends keyof MailSettings>(key: K, value: MailSettings[K]): void {
    if (this.mail) this.mail = { ...this.mail, [key]: value };
  }

  private notice(n: Notice) {
    return n ? html`<div class="msg ${n.kind}" role=${n.kind === 'error' ? 'alert' : 'status'}>${n.text}</div>` : '';
  }

  private renderAvatarCard() {
    const a = this.profile?.avatar;
    return html`
      <section class="card">
        <h2>Profile picture</h2>
        <p class="desc">Upload a PNG, JPEG or WebP picture (up to 2 MB), or pick a built-in avatar.</p>
        <div class="avatar-row">
          ${renderAvatar(this.profile, 72)}
          <div class="avatar-actions">
            <label class="btn primary">
              Upload picture
              <input type="file" accept="image/png,image/jpeg,image/webp" hidden @change=${this.onFile} />
            </label>
            <button class="btn" ?disabled=${this.busy || a?.kind === 'none'} @click=${this.removeAvatar}>Remove</button>
          </div>
        </div>
        <div class="grid" role="group" aria-label="Built-in avatars">
          ${PRESETS.map(
            (p) => html`<button class="preset" aria-label="Use ${p.id} avatar" aria-pressed=${a?.kind === 'preset' && a.preset === p.id ? 'true' : 'false'} @click=${() => void this.choosePreset(p.id)}><img alt="" src=${presetDataUrl(p.id)} /></button>`
          )}
        </div>
        ${this.notice(this.avatarNotice)}
      </section>
    `;
  }

  private renderDetailsCard() {
    const p = this.profile;
    const saved = p !== null && p.email === this.email && this.email !== '';
    return html`
      <section class="card">
        <h2>Your details</h2>
        <p class="desc">Approve your account with a code sent to your active servicenow.com address.</p>
        <div class="fields">
          <label class="field">Display name
            <input type="text" maxlength="80" .value=${this.name} @input=${(e: Event) => (this.name = (e.target as HTMLInputElement).value)} />
          </label>
          <label class="field">ServiceNow email
            <input type="email" placeholder="name@servicenow.com" .value=${this.email} @input=${(e: Event) => (this.email = (e.target as HTMLInputElement).value)} />
          </label>
        </div>
        <div class="row">
          <button class="btn primary" ?disabled=${this.busy} @click=${this.saveDetails}>Save profile</button>
          ${p?.email_verified ? html`<span class="chip ok">Approved</span>` : html`<span class="chip todo">Not approved</span>`}
          ${!p?.email_verified
            ? html`<button class="btn" ?disabled=${this.busy || !saved || !p?.mail_configured} @click=${this.sendCode}>Send approval code</button>`
            : ''}
        </div>
        ${!p?.email_verified && !p?.mail_configured
          ? html`<p class="hint">Set up email delivery below to send approval codes.</p>`
          : ''}
        ${!p?.email_verified && p?.verification_pending
          ? html`<div class="row">
              <input class="code-input" type="text" aria-label="Approval code" maxlength="12" placeholder="ABCD-EFGH" .value=${this.code} @input=${(e: Event) => (this.code = (e.target as HTMLInputElement).value)} />
              <button class="btn primary" ?disabled=${this.busy || this.code.trim().length < 4} @click=${this.confirmCode}>Approve</button>
            </div>`
          : ''}
        ${this.notice(this.detailsNotice)}
      </section>
    `;
  }

  private renderMailCard() {
    const m = this.mail;
    if (!m) return '';
    const input = (label: string, key: 'host' | 'username' | 'from_address', type = 'text', wide = false) => html`
      <label class="field ${wide ? 'wide' : ''}">${label}
        <input type=${type} .value=${m[key]} @input=${(e: Event) => this.setMail(key, (e.target as HTMLInputElement).value)} />
      </label>`;
    return html`
      <section class="card">
        <h2>Email delivery (SMTP)</h2>
        <p class="desc">Used only to send your approval code. The password is stored encrypted.</p>
        <div class="fields">
          ${input('SMTP host', 'host')}
          <label class="field">Port
            <input type="number" min="1" max="65535" .value=${String(m.port)} @input=${(e: Event) => this.setMail('port', Number((e.target as HTMLInputElement).value))} />
          </label>
          ${input('Username', 'username')}
          <label class="field">Password
            <input type="password" autocomplete="off" placeholder=${m.has_password ? '(saved - leave blank to keep)' : ''} .value=${this.smtpPassword} @input=${(e: Event) => (this.smtpPassword = (e.target as HTMLInputElement).value)} />
          </label>
          ${input('Send from address', 'from_address', 'email')}
          <label class="field">
            <span>Encryption</span>
            <span><input type="checkbox" .checked=${m.starttls} @change=${(e: Event) => this.setMail('starttls', (e.target as HTMLInputElement).checked)} /> Use STARTTLS (port 465 uses SSL)</span>
          </label>
        </div>
        <div class="row"><button class="btn primary" ?disabled=${this.busy} @click=${this.saveMail}>Save email settings</button></div>
        ${this.notice(this.mailNotice)}
      </section>
    `;
  }

  render() {
    return html`${this.renderAvatarCard()}${this.renderDetailsCard()}${this.renderMailCard()}`;
  }
}
