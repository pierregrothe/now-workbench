// web/e2e/fixtures.ts
// Shared Playwright fixtures: API-level state reset and navigation helpers (ADR-013).
// Author: Pierre Grothe
// Date: 2026-11-06
import { test as base, expect, type APIRequestContext, type Page } from '@playwright/test';

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
