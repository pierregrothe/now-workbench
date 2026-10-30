/**
 * Smart Floating Tooltip Manager
 *
 * Automatically positions tooltips for any element with [data-tooltip],
 * checking viewport boundaries and dynamically shifting or flipping them
 * so they never render outside the window (especially at the top or edges).
 */

class SmartTooltipManager {
  private tooltipEl: HTMLDivElement | null = null;
  private currentTarget: HTMLElement | null = null;
  private hideTimeout: number | null = null;
  private originalTitle: string | null = null;

  init(): void {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }

    if (!this.tooltipEl) {
      this.createTooltipElement();
    }

    document.addEventListener('pointerover', this.handlePointerOver, true);
    document.addEventListener('pointerout', this.handlePointerOut, true);
    document.addEventListener('focusin', this.handleFocusIn, true);
    document.addEventListener('focusout', this.handleFocusOut, true);
    window.addEventListener('scroll', this.handleScroll, true);
    window.addEventListener('resize', this.hideTooltip);
  }

  private createTooltipElement(): void {
    const el = document.createElement('div');
    el.className = 'now-smart-tooltip';
    el.setAttribute('role', 'tooltip');
    el.setAttribute('aria-hidden', 'true');
    el.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      z-index: 100000;
      pointer-events: none;
      opacity: 0;
      visibility: hidden;
      transform: scale(0.95);
      transition: opacity 0.12s ease, transform 0.12s ease;
      background: var(--now-text-primary, #032d42);
      color: var(--now-bg-surface-0, #ffffff);
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.35;
      white-space: nowrap;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.28);
      border: 1px solid var(--now-border-medium, rgba(255, 255, 255, 0.15));
      max-width: 280px;
      text-overflow: ellipsis;
      overflow: hidden;
    `;
    document.body.appendChild(el);
    this.tooltipEl = el;
  }

  private findTooltipTarget(event: Event): HTMLElement | null {
    const path = event.composedPath ? event.composedPath() : [];
    for (const node of path) {
      if (node instanceof HTMLElement && node.hasAttribute('data-tooltip')) {
        const text = node.getAttribute('data-tooltip')?.trim();
        if (text) {
          return node;
        }
      }
    }
    return null;
  }

  private handlePointerOver = (event: PointerEvent): void => {
    const target = this.findTooltipTarget(event);
    if (!target) return;
    if (this.currentTarget === target) return;

    this.showTooltip(target);
  };

  private handlePointerOut = (event: PointerEvent): void => {
    if (!this.currentTarget) return;
    const target = this.findTooltipTarget(event);
    if (target === this.currentTarget) {
      this.hideTooltip();
    }
  };

  private handleFocusIn = (event: FocusEvent): void => {
    const target = this.findTooltipTarget(event);
    if (target) {
      this.showTooltip(target);
    }
  };

  private handleFocusOut = (): void => {
    this.hideTooltip();
  };

  private handleScroll = (): void => {
    if (this.currentTarget) {
      this.updatePosition();
    }
  };

  private showTooltip(target: HTMLElement): void {
    if (this.hideTimeout) {
      window.clearTimeout(this.hideTimeout);
      this.hideTimeout = null;
    }

    this.currentTarget = target;
    const text = target.getAttribute('data-tooltip') || '';
    if (!text || !this.tooltipEl) return;

    // Suppress native title tooltip while hovering
    if (target.hasAttribute('title')) {
      this.originalTitle = target.getAttribute('title');
      target.removeAttribute('title');
    }

    this.tooltipEl.textContent = text;
    this.tooltipEl.style.visibility = 'visible';

    // Position after rendering content
    this.updatePosition();

    this.tooltipEl.style.opacity = '1';
    this.tooltipEl.style.transform = 'scale(1)';
    this.tooltipEl.setAttribute('aria-hidden', 'false');
  }

  private updatePosition(): void {
    if (!this.currentTarget || !this.tooltipEl) return;

    const targetRect = this.currentTarget.getBoundingClientRect();
    const tipRect = this.tooltipEl.getBoundingClientRect();

    const padding = 8;
    const offset = 7;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Check if target is still in viewport
    if (
      targetRect.bottom < 0 ||
      targetRect.top > viewportHeight ||
      targetRect.right < 0 ||
      targetRect.left > viewportWidth
    ) {
      this.hideTooltip();
      return;
    }

    // Determine vertical placement:
    // Default is ABOVE the element.
    // If placing above would render outside top boundary (< padding),
    // shift/flip to BELOW the element.
    let top: number;
    const fitsAbove = targetRect.top - tipRect.height - offset >= padding;
    const fitsBelow = targetRect.bottom + offset + tipRect.height <= viewportHeight - padding;

    if (!fitsAbove && fitsBelow) {
      // Flip to below
      top = targetRect.bottom + offset;
      this.tooltipEl.setAttribute('data-placement', 'bottom');
    } else if (fitsAbove) {
      // Normal placement above
      top = targetRect.top - tipRect.height - offset;
      this.tooltipEl.setAttribute('data-placement', 'top');
    } else {
      // Fits neither cleanly; clamp inside viewport
      top = Math.max(padding, Math.min(targetRect.bottom + offset, viewportHeight - tipRect.height - padding));
      this.tooltipEl.setAttribute('data-placement', 'clamped');
    }

    // Determine horizontal placement:
    // Default is centered over the element.
    let left = targetRect.left + (targetRect.width - tipRect.width) / 2;

    // Boundary check for horizontal overflow:
    if (left < padding) {
      left = padding;
    } else if (left + tipRect.width > viewportWidth - padding) {
      left = viewportWidth - tipRect.width - padding;
    }

    this.tooltipEl.style.top = `${Math.round(top)}px`;
    this.tooltipEl.style.left = `${Math.round(left)}px`;
  }

  private hideTooltip = (): void => {
    if (this.originalTitle && this.currentTarget) {
      this.currentTarget.setAttribute('title', this.originalTitle);
      this.originalTitle = null;
    }

    if (this.tooltipEl) {
      this.tooltipEl.style.opacity = '0';
      this.tooltipEl.style.transform = 'scale(0.95)';
      this.tooltipEl.setAttribute('aria-hidden', 'true');
      this.hideTimeout = window.setTimeout(() => {
        if (this.tooltipEl && !this.currentTarget) {
          this.tooltipEl.style.visibility = 'hidden';
        }
      }, 120);
    }
    this.currentTarget = null;
  };
}

export const smartTooltip = new SmartTooltipManager();
