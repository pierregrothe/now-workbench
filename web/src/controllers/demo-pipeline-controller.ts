// web/src/controllers/demo-pipeline-controller.ts
// ReactiveController managing use-case synthesis, seed execution, and pipeline status.
// Author: Pierre Grothe
// Date: 2026-10-31

import type { ReactiveController, ReactiveControllerHost } from 'lit';

export interface SynthesizedDemoResult {
  bundle_id: string;
  bundle_path: string;
  title: string;
  customer_name: string;
  industry: string;
  fluent_table_name: string;
  fluent_code: string;
  seed_records: Array<Record<string, unknown>>;
  sys_properties: Record<string, string>;
  narrative_markdown: string;
}

export interface SynthesizeParams {
  prompt: string;
  customerName: string;
  industry: string;
  releaseTarget: string;
  personas?: string[];
}

// The backend takes named persona fields; only send the ones the caller provided.
function personaFields(personas: string[] = []): Record<string, string> {
  const fields: Record<string, string> = {};
  if (personas[0]) fields.persona_primary = personas[0];
  if (personas[1]) fields.persona_secondary = personas[1];
  return fields;
}

export class DemoPipelineController implements ReactiveController {
  private host: ReactiveControllerHost;
  public isSynthesizing: boolean = false;
  public isSeeding: boolean = false;
  public synthesizedResult: SynthesizedDemoResult | null = null;
  public activeResultTab: 'narrative' | 'datasets' | 'customizations' = 'narrative';
  public seedStatusMessage: string = '';
  public error: string | null = null;

  constructor(host: ReactiveControllerHost) {
    this.host = host;
    host.addController(this);
  }

  hostConnected(): void {}
  hostDisconnected(): void {}

  async synthesize(params: SynthesizeParams): Promise<SynthesizedDemoResult | null> {
    this.isSynthesizing = true;
    this.error = null;
    this.seedStatusMessage = '';
    this.host.requestUpdate();

    try {
      const res = await fetch('/api/demos/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          use_case: params.prompt,
          customer_name: params.customerName,
          industry: params.industry,
          sn_release: params.releaseTarget,
          ...personaFields(params.personas),
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Synthesis failed (HTTP ${res.status})`);
      }

      const data = await res.json();
      this.synthesizedResult = data;
      this.activeResultTab = 'narrative';
      return data;
    } catch (err: any) {
      this.error = err.message || 'Synthesis failed';
      return null;
    } finally {
      this.isSynthesizing = false;
      this.host.requestUpdate();
    }
  }

  async seedDemo(bundleId?: string, instanceId?: string): Promise<boolean> {
    const targetBundle = bundleId || this.synthesizedResult?.bundle_id;
    if (!targetBundle) {
      this.seedStatusMessage = 'No demo bundle selected to seed.';
      this.host.requestUpdate();
      return false;
    }

    this.isSeeding = true;
    this.seedStatusMessage = `Seeding ${targetBundle} to target instance...`;
    this.host.requestUpdate();

    try {
      const payload: Record<string, string> = {};
      if (instanceId) {
        payload.instance_id = instanceId;
      }

      const res = await fetch(`/api/demos/${encodeURIComponent(targetBundle)}/seed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Seed failed (HTTP ${res.status})`);
      }

      const data = await res.json();
      if (data.status !== 'completed') {
        throw new Error(`Seed finished with status "${data.status}"`);
      }
      const count = Array.isArray(data.created_records) ? data.created_records.length : 0;
      this.seedStatusMessage = `Successfully seeded ${count} records to instance ${data.instance_id}.`;
      return true;
    } catch (err: any) {
      this.seedStatusMessage = `Seed error: ${err.message || 'Failed to seed'}`;
      return false;
    } finally {
      this.isSeeding = false;
      this.host.requestUpdate();
    }
  }

  setResultTab(tab: 'narrative' | 'datasets' | 'customizations'): void {
    this.activeResultTab = tab;
    this.host.requestUpdate();
  }
}
