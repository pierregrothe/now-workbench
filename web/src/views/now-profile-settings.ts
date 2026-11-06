// web/src/views/now-profile-settings.ts
// Profile settings: who is signed in (Cloudflare Access), roles, display name and avatar.
// Author: Pierre Grothe
// Date: 2026-11-06
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { workbenchStore } from '../context/workbench-context.js';
import { PRESETS, ROLE_LABELS, presetDataUrl, renderAvatar } from '../profile/avatars.js';
import type { ProfileData } from '../profile/avatars.js';
import { profileSettingsStyles } from './profile-settings-styles.js';

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
  @state() private avatarNotice: Notice = null;
  @state() private detailsNotice: Notice = null;
  @state() private busy = false;

  connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load(): Promise<void> {
    try {
      const res = await fetch('/api/profile');
      if (!res.ok) throw new Error(await detail(res, 'Could not load your profile'));
      this.applyProfile((await res.json()) as ProfileData);
    } catch (err) {
      this.detailsNotice = { kind: 'error', text: (err as Error).message };
    }
  }

  private applyProfile(profile: ProfileData): void {
    this.profile = profile;
    this.name = profile.display_name;
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

  private async saveName(): Promise<void> {
    try {
      const res = await this.call('/api/profile', this.json('PUT', { display_name: this.name }), 'Could not save your profile');
      this.applyProfile((await res.json()) as ProfileData);
      this.detailsNotice = { kind: 'ok', text: 'Profile saved.' };
    } catch (err) {
      this.detailsNotice = { kind: 'error', text: (err as Error).message };
    }
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
    return html`
      <section class="card">
        <h2>Your account</h2>
        <p class="desc">
          ${p?.auth_mode === 'cloudflare'
            ? 'Signed in through Cloudflare Access with your Apple or Google account.'
            : 'Local mode: the workbench is only reachable from this machine, so there is no sign-in.'}
        </p>
        <div class="fields">
          <label class="field">Display name
            <input type="text" maxlength="80" .value=${this.name} @input=${(e: Event) => (this.name = (e.target as HTMLInputElement).value)} />
          </label>
          <label class="field">Email
            <input type="email" readonly aria-readonly="true" .value=${p?.email ?? ''} />
          </label>
        </div>
        <div class="row">
          <span class="hint">Roles</span>
          ${(p?.roles ?? []).map((r) => html`<span class="chip ok">${ROLE_LABELS[r] ?? r}</span>`)}
        </div>
        <div class="row"><button class="btn primary" ?disabled=${this.busy} @click=${this.saveName}>Save profile</button></div>
        ${this.notice(this.detailsNotice)}
      </section>
    `;
  }

  render() {
    return html`${this.renderAvatarCard()}${this.renderDetailsCard()}`;
  }
}
