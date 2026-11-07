// web/src/components/admin-instance-model.ts
// Instance, profile and diagnostics shapes plus the purpose helpers the admin elements share.
// Author: Pierre Grothe
// Date: 2026-11-07

import { html } from 'lit';

/** One application node, as reported by the instance (ADR-014). */
export interface InstanceNodeData {
  node_id: string;
  hostname: string;
  datacenter: string | null;
  status: string;
  cpu_count: number | null;
  memory_max_mb: number | null;
  memory_in_use_mb: number | null;
  memory_pressure: string | null;
  started_at: string | null;
}

/** Platform facts read from the instance at connection time (ADR-014). */
export interface InstanceProfileData {
  release: string | null;
  build_tag: string | null;
  build_date: string | null;
  platform_name: string | null;
  installation_name: string | null;
  /** Platform-reported provisioning type: a standalone demo instance reports "prod". */
  instance_type: string | null;
  /** Value of glide.installation.production (admin-editable property). */
  production_property: boolean | null;
  datacenter: string | null;
  db_product: string | null;
  db_version: string | null;
  java_version: string | null;
  os: string | null;
  nodes: InstanceNodeData[];
  captured_at: string;
}

export interface InstanceData {
  id: string;
  name: string;
  url: string;
  username: string;
  release: string;
  is_default: boolean;
  status: string;
  last_checked: string | null;
  purpose: InstancePurpose;
  profile?: InstanceProfileData | null;
}

export const PRESSURE_RANK: Record<string, number> = { UNDER: 0, NOMINAL: 1, OVER: 2, SUSTAINED_OVER: 3 };

/** What the owner uses the instance for: declared, never detected (ADR-014). */
export type InstancePurpose = 'demo' | 'development' | 'test' | 'production';

export const PURPOSES: Array<[InstancePurpose, string]> = [
  ['demo', 'Demo'],
  ['development', 'Development'],
  ['test', 'Test'],
  ['production', 'Production'],
];

export function purposeLabel(purpose: InstancePurpose): string {
  return PURPOSES.find(([value]) => value === purpose)?.[1] ?? purpose;
}

export function renderPurposeOptions(selected: InstancePurpose) {
  return PURPOSES.map(
    ([value, label]) => html`<option value=${value} ?selected=${value === selected}>${label}</option>`,
  );
}

export interface DiagnosticsData {
  app_version: string;
  python_runtime: string;
  toolchain: {
    node_available: boolean;
    node_path: string;
    now_sdk_available: boolean;
    now_sdk_path: string;
  };
  instances_count: number;
  active_instance: string;
  active_instance_url: string;
  otto_status: string;
}
