// web/src/context/workbench-context.ts
// Centralized state container & context protocol for Now Workbench.
// Author: Pierre Grothe
// Date: 2026-10-31

export interface InstanceData {
  id: string;
  name: string;
  url: string;
  username: string;
  release: string;
  is_default: boolean;
  status: string;
  last_checked: string | null;
}

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
      if (res.ok) {
        const data = await res.json();
        const list: InstanceData[] = Array.isArray(data) ? data : [];
        const currentSelected = this._state.selectedInstanceId;
        const defaultInst = list.find((i) => i.is_default) || list[0];
        const nextSelected = currentSelected && list.some((i) => i.id === currentSelected)
          ? currentSelected
          : (defaultInst ? defaultInst.id : '');
        this.setState({ instances: list, selectedInstanceId: nextSelected });
      }
    } catch (err) {
      console.warn('Failed to load instances into context store:', err);
    }
  }

  async loadBundles(): Promise<void> {
    try {
      const res = await fetch('/api/demos');
      if (res.ok) {
        const data = await res.json();
        const infos: Array<{ manifest: { id: string; name?: string; min_release?: string } }> =
          Array.isArray(data) ? data : [];
        const list: DemoBundleItem[] = infos.map((b) => ({
          id: b.manifest.id,
          name: b.manifest.name || b.manifest.id,
          release: b.manifest.min_release || 'Zurich',
        }));
        this.setState({ bundles: list });
      }
    } catch (err) {
      console.warn('Failed to load bundles into context store:', err);
    }
  }
}

export const workbenchStore = new WorkbenchStore();
