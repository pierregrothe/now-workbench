// web/src/context/workbench-context.ts
// Centralized state container & context protocol for Now Workbench.
// Author: Pierre Grothe
// Date: 2026-10-31

import type { ProfileData } from '../profile/avatars.js';
import type { InstanceData } from './instance-model.js';

export interface DemoBundleItem {
  id: string;
  name: string;
  release: string;
  installed?: boolean;
}

export interface WorkbenchState {
  activeTab: string;
  selectedInstanceId: string;
  instances: InstanceData[];
  selectedBundleId: string;
  bundles: DemoBundleItem[];
  themeMode: 'light' | 'dark' | 'polaris';
  claudeKeyConfigured: boolean;
  /** Why instances or bundles could not be loaded; null when the last load succeeded. */
  loadError: string | null;
  /** The local profile; null until loaded. */
  profile: ProfileData | null;
}

export type StateListener = (state: WorkbenchState) => void;

class WorkbenchStore {
  private _state: WorkbenchState = {
    activeTab: 'home',
    selectedInstanceId: '',
    instances: [],
    selectedBundleId: 'sample-ai-assistant',
    bundles: [],
    themeMode: 'polaris',
    claudeKeyConfigured: false,
    loadError: null,
    profile: null,
  };

  private _listeners = new Set<StateListener>();

  get state(): Readonly<WorkbenchState> {
    return this._state;
  }

  setState(partial: Partial<WorkbenchState>): void {
    this._state = { ...this._state, ...partial };
    this.notify();
  }

  subscribe(listener: StateListener): () => void {
    this._listeners.add(listener);
    listener(this._state);
    return () => {
      this._listeners.delete(listener);
    };
  }

  private notify(): void {
    for (const listener of this._listeners) {
      try {
        listener(this._state);
      } catch (err) {
        console.error('Error notifying workbench store listener:', err);
      }
    }
  }

  async loadInstances(): Promise<void> {
    try {
      const res = await fetch('/api/instances');
      if (!res.ok) {
        this.setState({ loadError: `Could not load instances (HTTP ${res.status}).` });
        return;
      }
      const data = await res.json();
      const list: InstanceData[] = Array.isArray(data) ? data : [];
      const currentSelected = this._state.selectedInstanceId;
      const defaultInst = list.find((i) => i.is_default) || list[0];
      const nextSelected =
        currentSelected && list.some((i) => i.id === currentSelected)
          ? currentSelected
          : defaultInst
            ? defaultInst.id
            : '';
      this.setState({ instances: list, selectedInstanceId: nextSelected, loadError: null });
    } catch (err) {
      this.setState({ loadError: `Could not reach the backend to load instances: ${String(err)}` });
    }
  }

  async loadProfile(): Promise<void> {
    try {
      const res = await fetch('/api/profile');
      if (res.ok) {
        this.setState({ profile: (await res.json()) as ProfileData });
      }
    } catch {
      // The profile is cosmetic; the app works without it and initials are shown.
    }
  }

  async loadBundles(): Promise<void> {
    try {
      const res = await fetch('/api/demos');
      if (!res.ok) {
        this.setState({ loadError: `Could not load demo bundles (HTTP ${res.status}).` });
        return;
      }
      const data = await res.json();
      const infos: Array<{ manifest: { id: string; name?: string; min_release?: string } }> =
        Array.isArray(data) ? data : [];
      const list: DemoBundleItem[] = infos.map((b) => ({
        id: b.manifest.id,
        name: b.manifest.name || b.manifest.id,
        release: b.manifest.min_release || 'Unknown',
      }));
      this.setState({ bundles: list, loadError: null });
    } catch (err) {
      this.setState({ loadError: `Could not reach the backend to load bundles: ${String(err)}` });
    }
  }
}

export const workbenchStore = new WorkbenchStore();
