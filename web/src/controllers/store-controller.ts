// web/src/controllers/store-controller.ts
// ReactiveController that keeps a component in sync with the shared workbench store.
// Author: Pierre Grothe
// Date: 2026-11-07
//
// ADR-024: components never subscribe to the store by hand. The controller subscribes when
// the host connects, re-renders it on every change and unsubscribes when it disconnects, so
// a forgotten unsubscribe cannot leave a listener behind.

import type { ReactiveController, ReactiveControllerHost } from 'lit';
import { workbenchStore, type WorkbenchState } from '../context/workbench-context.js';

export class StoreController implements ReactiveController {
  private readonly host: ReactiveControllerHost;
  private unsubscribe?: () => void;

  /** The store's state as of the last change (read it in render). */
  state: Readonly<WorkbenchState> = workbenchStore.state;

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {
    this.unsubscribe = workbenchStore.subscribe((state) => {
      this.state = state;
      this.host.requestUpdate();
    });
  }

  hostDisconnected(): void {
    this.unsubscribe?.();
    this.unsubscribe = undefined;
  }
}
