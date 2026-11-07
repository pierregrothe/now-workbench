// web/src/context/instance-model.ts
// The instance record as the API returns it: one definition for the store and the admin screens.
// Author: Pierre Grothe
// Date: 2026-11-07

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

/** What the owner uses the instance for: declared, never detected (ADR-014). */
export type InstancePurpose = 'demo' | 'development' | 'test' | 'production';
