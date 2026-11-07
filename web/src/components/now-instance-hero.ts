// web/src/components/now-instance-hero.ts
// The active instance card: identity, status, detected platform facts, edit and test actions.
// Author: Pierre Grothe
// Date: 2026-11-07

import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { PRESSURE_RANK, purposeLabel, type InstanceData } from './admin-instance-model.js';
import { adminSharedStyles } from './admin-shared-styles.js';
import { instanceHeroStyles } from './now-instance-hero-styles.js';

/**
 * Card for the active (default) instance. Raises `edit-instance` and `test-instance`; the
 * admin panel owns editing and connection tests (ADR-024).
 */
@customElement('now-instance-hero')
export class NowInstanceHero extends LitElement {
  static styles = [adminSharedStyles, instanceHeroStyles];

  @property({ attribute: false }) instance!: InstanceData;
  @property({ type: Boolean }) testing = false;

  private emit(name: 'edit-instance' | 'test-instance'): void {
    this.dispatchEvent(new CustomEvent(name, { detail: { instanceId: this.instance.id } }));
  }

  /** Detected platform facts for the active instance (never user-entered; ADR-014). */
  private renderProfileFacts(inst: InstanceData) {
    const profile = inst.profile;
    if (!profile) {
      return html`<div class="profile-empty" data-testid="profile-empty">
        Platform details (release, instance type, datacenter, nodes, CPU, memory) are read from
        the instance on the first successful connection test.
      </div>`;
    }
    const nodes = profile.nodes;
    const online = nodes.filter((n) => n.status === 'online').length;
    const cpus = nodes.map((n) => n.cpu_count).filter((c): c is number => c !== null);
    const heapMax = nodes.reduce((sum, n) => sum + (n.memory_max_mb ?? 0), 0);
    const heapUsed = nodes.reduce((sum, n) => sum + (n.memory_in_use_mb ?? 0), 0);
    const worst = nodes
      .map((n) => n.memory_pressure)
      .filter((p): p is string => !!p)
      .sort((a, b) => (PRESSURE_RANK[b] ?? 0) - (PRESSURE_RANK[a] ?? 0))[0];
    const facts: Array<[string, string, boolean]> = [
      ['Installation (reported)', profile.installation_name ?? '--', false],
      [
        'Instance type (reported)',
        [profile.instance_type, profile.production_property === null ? null : `production property ${profile.production_property}`]
          .filter(Boolean)
          .join(', ') || '--',
        false,
      ],
      ['Datacenter', profile.datacenter ?? '--', false],
      ['Nodes', nodes.length ? `${online}/${nodes.length} online` : '--', online < nodes.length],
      [
        'CPUs per node',
        cpus.length ? (Math.min(...cpus) === Math.max(...cpus) ? `${cpus[0]}` : `${Math.min(...cpus)}-${Math.max(...cpus)}`) : '--',
        false,
      ],
      [
        'JVM heap (all nodes)',
        heapMax ? `${Math.round(heapUsed)} / ${Math.round(heapMax)} MB (${Math.round((heapUsed / heapMax) * 100)}%)` : '--',
        false,
      ],
      ['Memory pressure (worst)', worst ?? '--', !!worst && (PRESSURE_RANK[worst] ?? 0) >= 2],
      ['Build', profile.build_date ? `${profile.build_date}` : '--', false],
      ['Database', [profile.db_product, profile.db_version].filter(Boolean).join(' ') || '--', false],
      ['Java', profile.java_version ?? '--', false],
    ];
    return html`<div class="profile-facts" data-testid="profile-facts">
      ${facts.map(
        ([label, value, warn]) => html`<div class="profile-fact">
          <span class="fact-label">${label}</span>
          <span class="fact-value ${warn ? 'warn' : ''}" title=${label === 'Build' ? profile.build_tag ?? '' : ''}
            >${value}</span
          >
        </div>`,
      )}
    </div>`;
  }

  render() {
    const activeInst = this.instance;
    return html`
          <div class="active-hero-card">
            <div class="hero-top-row">
              <div class="hero-badge-group">
                <span class="badge-target">Active Deployment Target</span>
                <span class="badge-release">
                  ${activeInst.release === 'Unknown' ? 'Release not detected' : `${activeInst.release} Family`}
                </span>
                <span
                  class="badge-release ${activeInst.purpose === 'production' ? 'purpose-production' : ''}"
                  data-testid="hero-purpose"
                  title="Purpose you declared for this instance"
                  >${purposeLabel(activeInst.purpose)}</span
                >
              </div>
              <span class="status-badge ${this.testing ? 'testing' : activeInst.status}">
                <span class="dot-indicator"></span>
                ${this.testing
                  ? 'Testing Authentication...'
                  : activeInst.status === 'authenticated'
                  ? 'Authenticated'
                  : activeInst.status.toUpperCase()}
              </span>
            </div>

            <div class="hero-title-group">
              <h2>${activeInst.name}</h2>
              <div class="hero-url-row">
                <span>Endpoint:</span>
                <a
                  class="hero-url-link"
                  href=${activeInst.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Open instance in new tab"
                >
                  ${activeInst.url} [->]
                </a>
              </div>
            </div>

            ${this.renderProfileFacts(activeInst)}

            <div class="hero-bottom-bar">
              <div class="hero-meta-group">
                <span>Service Account: <strong>${activeInst.username}</strong></span>
                <span>
                  Last Check:
                  <strong>
                    ${activeInst.last_checked
                      ? activeInst.last_checked.slice(0, 19).replace('T', ' ')
                      : 'Never'}
                  </strong>
                </span>
              </div>

              <div class="hero-actions">
                <button
                  class="btn-hero-test icon-btn"
                  title="Edit Credentials"
                  data-tooltip="Edit Credentials"
                  @click=${() => this.emit('edit-instance')}
                >
                  <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                </button>
                <button
                  class="btn-hero-test icon-btn"
                  ?disabled=${this.testing}
                  title="Test Auth Probe"
                  data-tooltip="Test Auth Probe"
                  @click=${() => this.emit('test-instance')}
                >
                  <svg viewBox="0 0 24 24"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
                </button>
                <a
                  class="btn-hero-open icon-btn"
                  href=${activeInst.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Open Instance in new tab"
                  data-tooltip="Open Instance"
                >
                  <svg viewBox="0 0 24 24"><path d="M19 19H5V5h7V3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z"/></svg>
                </a>
              </div>
            </div>
          </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-instance-hero': NowInstanceHero;
  }
}
