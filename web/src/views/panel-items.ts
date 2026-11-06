// web/src/views/panel-items.ts
// Builds the right-hand detail panel content for instance and bundle tiles from real data.
// Author: Pierre Grothe
// Date: 2026-11-06
import type { InstanceData } from '../context/workbench-context.js';

export interface PanelItem {
  title: string;
  subtitle?: string;
  rows: { label: string; value: string }[];
  action?: { label: string; tab: string };
}

const present = (rows: { label: string; value: string | number | null | undefined }[]) =>
  rows
    .filter((r) => r.value !== null && r.value !== undefined && String(r.value) !== '')
    .map((r) => ({ label: r.label, value: String(r.value) }));

export function instancePanel(inst: InstanceData): PanelItem {
  const p = inst.profile;
  const db = [p?.db_product, p?.db_version].filter(Boolean).join(' ');
  return {
    title: inst.name,
    subtitle: inst.url,
    rows: present([
      { label: 'Release', value: inst.release },
      { label: 'Status', value: inst.status },
      { label: 'Purpose', value: inst.purpose },
      { label: 'Installation (reported)', value: p?.installation_name },
      { label: 'Datacenter', value: p?.datacenter },
      { label: 'Nodes', value: p?.nodes?.length },
      { label: 'Build', value: p?.build_tag },
      { label: 'Database', value: db },
      { label: 'Java', value: p?.java_version },
      { label: 'Last checked', value: inst.last_checked ? new Date(inst.last_checked).toLocaleString() : '' },
    ]),
    action: { label: 'Manage in Settings', tab: 'admin' },
  };
}

export function bundlePanel(props: Record<string, unknown>): PanelItem {
  return {
    title: String(props.name ?? 'Demo bundle'),
    rows: present([
      { label: 'Minimum release', value: props.release as string | undefined },
      { label: 'Industry', value: props.industry as string | undefined },
      { label: 'Tables', value: props.tables_count as number | undefined },
      { label: 'Records', value: props.records_count as number | undefined },
    ]),
    action: { label: 'Open Artifact library', tab: 'artifacts' },
  };
}
