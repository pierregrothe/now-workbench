// web/src/controllers/mobile-nav-controller.ts
// Phone layout state: the navigation rail becomes a drawer on phone-sized screens.
// Author: Pierre Grothe
// Date: 2026-11-07
import type { ReactiveController, ReactiveControllerHost } from 'lit';

/** Phone layout: narrow (portrait phones) or short (landscape phones). */
export const PHONE_QUERY = '(max-width: 768px), (max-height: 500px)';

/** Events after which an open drawer closes: the person picked somewhere to go. */
const CLOSING_EVENTS = ['nav-change', 'thread-select', 'new-session'] as const;

/**
 * Tracks whether the viewport is phone-sized and whether the navigation drawer is open.
 * The drawer closes on navigation, on Escape, and when the viewport grows past a phone.
 */
export class MobileNavController implements ReactiveController {
  phone = false;
  open = false;
  private readonly media: MediaQueryList | null =
    typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(PHONE_QUERY) : null;

  constructor(private readonly host: ReactiveControllerHost & HTMLElement) {
    host.addController(this);
    this.phone = this.media?.matches ?? false;
  }

  hostConnected(): void {
    this.media?.addEventListener('change', this.onMedia);
    window.addEventListener('keydown', this.onKey);
    for (const name of CLOSING_EVENTS) this.host.addEventListener(name, this.close);
  }

  hostDisconnected(): void {
    this.media?.removeEventListener('change', this.onMedia);
    window.removeEventListener('keydown', this.onKey);
    for (const name of CLOSING_EVENTS) this.host.removeEventListener(name, this.close);
  }

  toggle = (): void => {
    this.open = !this.open;
    this.host.requestUpdate();
  };

  close = (): void => {
    if (!this.open) return;
    this.open = false;
    this.host.requestUpdate();
  };

  private onMedia = (e: MediaQueryListEvent): void => {
    this.phone = e.matches;
    this.open = false;
    this.host.requestUpdate();
  };

  private onKey = (e: KeyboardEvent): void => {
    if (e.key === 'Escape') this.close();
  };
}
