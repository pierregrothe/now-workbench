// web/src/components/admin-instance-model.ts
// Instance, profile and diagnostics shapes plus the purpose helpers the admin elements share.
// Author: Pierre Grothe
// Date: 2026-11-07

import { html } from 'lit';
import type { InstancePurpose } from '../context/instance-model.js';

export const PRESSURE_RANK: Record<string, number> = { UNDER: 0, NOMINAL: 1, OVER: 2, SUSTAINED_OVER: 3 };

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
