// web/src/components/now-instance-hero-styles.ts
// Styles of <now-instance-hero>: the active instance card and its platform facts.
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const instanceHeroStyles = css`
    :host {
      display: block;
    }

    /* Hero Card for Active Instance */
    .active-hero-card {
      background: linear-gradient(135deg, #032d42 0%, #08405d 100%);
      color: #ffffff;
      border-radius: 16px;
      padding: 24px 28px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: 0 12px 32px rgba(3, 45, 66, 0.15);
      position: relative;
      overflow: hidden;
    }

    .active-hero-card::after {
      content: "";
      position: absolute;
      right: -40px;
      top: -40px;
      width: 200px;
      height: 200px;
      background: radial-gradient(circle, rgba(98, 216, 78, 0.18) 0%, transparent 70%);
      border-radius: 50%;
      pointer-events: none;
    }

    .hero-top-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .hero-badge-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .badge-target {
      background: #62d84e;
      color: #032d42;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 4px 10px;
      border-radius: 999px;
    }

    .profile-facts {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
      gap: 10px 18px;
      padding: 14px 0 4px;
      font-size: 12.5px;
      color: #e2e8f0;
    }

    .profile-fact .fact-label {
      display: block;
      font-size: 10.5px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #94a3b8;
    }

    .profile-fact .fact-value {
      font-weight: 600;
      color: #ffffff;
      word-break: break-word;
    }

    .profile-fact .fact-value.warn {
      color: #fbbf24;
    }

    .profile-empty {
      padding: 12px 0 4px;
      font-size: 12.5px;
      color: #cbd5e1;
      font-style: italic;
    }



    .badge-release.purpose-production {
      background: #b42318;
      border-color: #fda29b;
    }


    .badge-release {
      background: rgba(255, 255, 255, 0.15);
      color: #ffffff;
      font-size: 11.5px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 999px;
      border: 1px solid rgba(255, 255, 255, 0.25);
    }

    .hero-title-group h2 {
      font-size: 22px;
      font-weight: 700;
      margin: 0;
      letter-spacing: -0.02em;
      color: #ffffff;
    }

    .hero-url-row {
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: "JetBrains Mono", monospace;
      font-size: 13.5px;
      color: #cbd5e1;
      margin-top: 4px;
    }

    .hero-url-link {
      color: #93c5fd;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .hero-url-link:hover {
      text-decoration: underline;
      color: #bfdbfe;
    }

    .hero-bottom-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 14px;
      border-top: 1px solid rgba(255, 255, 255, 0.12);
      flex-wrap: wrap;
      gap: 12px;
    }

    .hero-meta-group {
      display: flex;
      align-items: center;
      gap: 20px;
      font-size: 12.5px;
      color: #e2e8f0;
    }

    .hero-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .btn-hero-test {
      position: relative;
      appearance: none;
      border: 1px solid rgba(255, 255, 255, 0.35);
      background: rgba(255, 255, 255, 0.1);
      color: #ffffff;
      font-size: 12.5px;
      font-weight: 600;
      padding: 7px 16px;
      border-radius: 999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      font-family: inherit;
    }

    .btn-hero-test.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      justify-content: center;
      border-radius: 50%;
    }

    .btn-hero-test.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .btn-hero-test:hover {
      background: rgba(255, 255, 255, 0.2);
      border-color: #ffffff;
    }

    .btn-hero-open {
      position: relative;
      appearance: none;
      border: none;
      background: #ffffff;
      color: #032d42;
      font-size: 12.5px;
      font-weight: 700;
      padding: 7px 16px;
      border-radius: 999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      text-decoration: none;
      transition: background 0.15s ease;
      font-family: inherit;
    }

    .btn-hero-open.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      justify-content: center;
      border-radius: 50%;
    }

    .btn-hero-open.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .btn-hero-open:hover {
      background: #f1f5f9;
    }
  
    /* Phones (ADR-030): badges wrap instead of running off the card. */
    @media (max-width: 768px), (max-height: 500px) {
      .active-hero-card {
        padding: 18px 16px;
      }

      .hero-badge-group {
        flex-wrap: wrap;
        gap: 6px;
      }
    }
`;
