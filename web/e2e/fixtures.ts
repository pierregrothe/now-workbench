// web/e2e/fixtures.ts
// Shared Playwright fixtures: API-level state reset and navigation helpers (ADR-013).
// Author: Pierre Grothe
// Date: 2026-11-06
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { test as base, expect, type APIRequestContext, type Page } from '@playwright/test';

const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));

export interface InstanceSeed {
  name: string;
  url: string;
  username?: string;
  password?: string;
  is_default?: boolean;
}

/** Delete every registered instance so each test starts from an empty registry. */
async function resetInstances(request: APIRequestContext): Promise<void> {
  const res = await request.get('/api/instances');
  expect(res.ok()).toBeTruthy();
  for (const inst of (await res.json()) as Array<{ id: string }>) {
    const del = await request.delete(`/api/instances/${inst.id}`);
    expect(del.ok()).toBeTruthy();
  }
}

/** Register an instance through the real API (credentials are sealed server-side). */
export async function seedInstance(
  request: APIRequestContext,
  seed: InstanceSeed,
): Promise<{ id: string }> {
  const res = await request.post('/api/instances', { data: seed });
  expect(res.status(), await res.text()).toBe(200);
  return (await res.json()) as { id: string };
}

/**
 * Store a detected platform profile through the real repository code, exactly as a
 * live connection test would (fake:// instances are never probed, ADR-014).
 */
export function seedProfile(profile: Record<string, unknown>): void {
  const script = [
    'import json, sys',
    'from now_workbench.domains.instances import InstanceProfile, InstanceRepository',
    'from now_workbench.platform.db.session import db_session',
    'with db_session() as conn:',
    '    profile = InstanceProfile.model_validate(json.load(sys.stdin))',
    '    InstanceRepository(conn).save_instance_profile(profile)',
  ].join('\n');
  execFileSync('uv', ['run', 'python', '-c', script], {
    cwd: REPO_ROOT,
    input: JSON.stringify(profile),
    env: { ...process.env, WORKBENCH_DATA_DIR: '.e2e/data', WORKBENCH_KEY_FILE: '.e2e/keys/master.key' },
    stdio: ['pipe', 'inherit', 'inherit'],
  });
}

/** Open Workbench Settings -> ServiceNow Instances. */
export async function openInstancesPanel(page: Page): Promise<void> {
  await page.goto('/#admin');
  await page.getByRole('button', { name: 'ServiceNow Instances' }).click();
  await expect(page.getByText(/Connected Sub-Production Instances/)).toBeVisible();
}

export const test = base.extend<{ cleanState: void }>({
  cleanState: [
    async ({ request }, use) => {
      await resetInstances(request);
      // Keep the welcome modal from covering the page under test.
      const prefs = await request.put('/api/settings', {
        data: { show_welcome_on_startup: false },
      });
      expect(prefs.ok()).toBeTruthy();
      await use();
    },
    { auto: true },
  ],
});

export { expect };

/** Set activeThreadId on the chat view, searching through nested shadow roots. */
export const selectThread = async (page: Page): Promise<void> => {
  // The app renders after its access check; wait for it before reaching into the chat view.
  await page.locator('now-nav-rail').waitFor();
  await page.evaluate(() => {
    const find = (root: Document | ShadowRoot): Element | null => {
      const hit = root.querySelector('now-chat-view');
      if (hit) return hit;
      for (const el of Array.from(root.querySelectorAll('*'))) {
        if (el.shadowRoot) {
          const inner = find(el.shadowRoot);
          if (inner) return inner;
        }
      }
      return null;
    };
    (find(document) as any).activeThreadId = 'default-thread';
  });
};
