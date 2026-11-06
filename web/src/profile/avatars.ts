// web/src/profile/avatars.ts
// Built-in generic avatars (inline SVG) and a helper that renders any profile avatar.
// Author: Pierre Grothe
// Date: 2026-11-06
import { html } from 'lit';
import type { TemplateResult } from 'lit';

export interface ProfileData {
  email: string;
  display_name: string;
  roles: string[];
  auth_mode: 'cloudflare' | 'local';
  avatar: { kind: 'none' | 'preset' | 'upload'; preset: string | null; url: string | null };
}

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrator',
  solution_consultant: 'Solution Consultant',
};

export const roleSummary = (profile: ProfileData | null): string =>
  profile ? profile.roles.map((r) => ROLE_LABELS[r] ?? r).join(' - ') : '';

export const isAdmin = (profile: ProfileData | null): boolean =>
  profile?.roles.includes('admin') ?? false;

interface Preset {
  id: string;
  bg: string;
  glyph: string;
}

const W = 'fill="#ffffff"';
const S = 'fill="none" stroke="#ffffff" stroke-width="4" stroke-linecap="round"';

// Ids must match PRESET_AVATARS in src/now_workbench/profile/avatars.py (a test compares them).
export const PRESETS: Preset[] = [
  { id: 'sun', bg: '#f59e0b', glyph: `<circle cx="32" cy="32" r="11" ${W}/><path d="M32 8v8M32 48v8M8 32h8M48 32h8M15 15l6 6M43 43l6 6M49 15l-6 6M21 43l-6 6" ${S}/>` },
  { id: 'leaf', bg: '#16a34a', glyph: `<path d="M14 46C14 24 28 14 50 14c0 22-10 36-32 36z" ${W}/><path d="M16 48L36 28" stroke="#16a34a" stroke-width="3" stroke-linecap="round"/>` },
  { id: 'wave', bg: '#0ea5e9', glyph: `<path d="M10 26q7-8 14 0t14 0 14 0M10 38q7-8 14 0t14 0 14 0" ${S}/>` },
  { id: 'peak', bg: '#6366f1', glyph: `<path d="M8 50L26 18l10 16 6-8 14 24z" ${W}/>` },
  { id: 'moon', bg: '#1e3a8a', glyph: `<path d="M40 12a22 22 0 1 0 12 30A18 18 0 0 1 40 12z" ${W}/>` },
  { id: 'spark', bg: '#db2777', glyph: `<path d="M32 8l6 18 18 6-18 6-6 18-6-18-18-6 18-6z" ${W}/>` },
  { id: 'cube', bg: '#0d9488', glyph: `<path d="M32 10l20 11v22L32 54 12 43V21z" ${W}/><path d="M12 21l20 11 20-11M32 32v22" stroke="#0d9488" stroke-width="3" fill="none"/>` },
  { id: 'bloom', bg: '#e11d48', glyph: `<circle cx="32" cy="18" r="9" ${W}/><circle cx="46" cy="29" r="9" ${W}/><circle cx="41" cy="45" r="9" ${W}/><circle cx="23" cy="45" r="9" ${W}/><circle cx="18" cy="29" r="9" ${W}/><circle cx="32" cy="34" r="6" fill="#e11d48"/>` },
  { id: 'orbit', bg: '#7c3aed', glyph: `<circle cx="32" cy="32" r="9" ${W}/><ellipse cx="32" cy="32" rx="22" ry="9" transform="rotate(-25 32 32)" ${S}/>` },
  { id: 'fox', bg: '#ea580c', glyph: `<path d="M12 14l14 10h12l14-10 2 24-22 16-22-16z" ${W}/><circle cx="25" cy="36" r="3" fill="#ea580c"/><circle cx="39" cy="36" r="3" fill="#ea580c"/>` },
  { id: 'owl', bg: '#92400e', glyph: `<rect x="14" y="12" width="36" height="40" rx="14" ${W}/><circle cx="25" cy="29" r="6" fill="#92400e"/><circle cx="39" cy="29" r="6" fill="#92400e"/><path d="M29 38l3 5 3-5z" fill="#92400e"/>` },
  { id: 'robot', bg: '#475569', glyph: `<rect x="14" y="22" width="36" height="28" rx="8" ${W}/><path d="M32 22v-8" ${S}/><circle cx="32" cy="12" r="3" ${W}/><circle cx="25" cy="35" r="4" fill="#475569"/><circle cx="39" cy="35" r="4" fill="#475569"/>` },
];

export function presetSvg(id: string): string {
  const p = PRESETS.find((x) => x.id === id);
  if (!p) return '';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="${p.bg}"/>${p.glyph}</svg>`;
}

export const presetDataUrl = (id: string): string =>
  `data:image/svg+xml;utf8,${encodeURIComponent(presetSvg(id))}`;

export const initialsOf = (name: string): string =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join('') || '?';

/** Render the user's avatar: uploaded picture, built-in avatar, or initials. */
export function renderAvatar(profile: ProfileData | null, size = 24): TemplateResult {
  const box = `width:${size}px;height:${size}px;border-radius:50%;flex:none;overflow:hidden;`;
  const a = profile?.avatar;
  if (a?.kind === 'upload' && a.url) {
    return html`<img alt="" src=${a.url} style="${box}object-fit:cover;" />`;
  }
  if (a?.kind === 'preset' && a.preset) {
    return html`<img alt="" src=${presetDataUrl(a.preset)} style="${box}" />`;
  }
  return html`<span style="${box}display:inline-flex;align-items:center;justify-content:center;background:#c9f0c1;color:#1b4d1b;font-size:${Math.max(9, size * 0.42)}px;font-weight:700;">${initialsOf(profile?.display_name || profile?.email.split('@')[0] || '')}</span>`;
}
