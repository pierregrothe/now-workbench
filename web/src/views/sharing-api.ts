// web/src/views/sharing-api.ts
// Types and a fetch helper for groups, versions, shares and approvals (PRD-003, ADR-018).
// Author: Pierre Grothe
// Date: 2026-11-06

export type GroupKind = 'region' | 'territory' | 'business_unit';

export const KIND_LABELS: Record<GroupKind, string> = {
  region: 'Region',
  territory: 'Territory',
  business_unit: 'Business unit',
};

export interface Group {
  id: string;
  name: string;
  kind: GroupKind;
  description: string;
  member_count: number;
  my_status: 'pending' | 'active' | null;
  my_role: 'member' | 'admin' | null;
}

export interface GroupMember {
  group_id: string;
  email: string;
  role: 'member' | 'admin';
  status: 'pending' | 'active';
  requested_at: string;
}

export interface ArtifactVersion {
  artifact_id: string;
  version: number;
  name: string;
  note: string;
  size_bytes: number;
  created_by: string;
  created_at: string;
}

export interface ArtifactShare {
  id: string;
  artifact_id: string;
  artifact_name: string;
  version: number;
  target: 'group' | 'global';
  group_id: string | null;
  group_name: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'superseded';
  requested_by: string;
  requested_at: string;
}

export interface ApprovalInbox {
  shares: ArtifactShare[];
  join_requests: GroupMember[];
  group_names: Record<string, string>;
}

/** Fetch JSON; a failed response throws an Error carrying the server's explanation. */
export async function api<T>(url: string, init: RequestInit = {}): Promise<T> {
  const headers = init.body ? { 'Content-Type': 'application/json', ...init.headers } : init.headers;
  const res = await fetch(url, { ...init, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail;
    throw new Error(typeof detail === 'string' ? detail : `HTTP ${res.status}`);
  }
  return body as T;
}

/** Human label for where a share goes. */
export function shareTargetLabel(s: ArtifactShare): string {
  return s.target === 'global' ? 'Everyone' : s.group_name || 'Group';
}
