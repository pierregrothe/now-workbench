// web/e2e/no-fabricated-fallbacks.spec.ts
// ADR-013 audit (STORY-058): when the backend fails, each screen says so and invents nothing.
// Author: Pierre Grothe
// Date: 2026-11-07
import { expect, test } from './fixtures';

const fail = (status: number) => ({ status, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) });

test('the artifact library reports a failed load and shows no bundle', async ({ page }) => {
  await page.route('**/api/demos', (route) => route.fulfill(fail(500)));
  await page.goto('/#artifacts');
  await expect(page.getByText('Could not load demo bundles (HTTP 500).')).toBeVisible();
  await expect(page.locator('.demo-card')).toHaveCount(0);
});

test('the artifact library reports an unreachable backend', async ({ page }) => {
  await page.route('**/api/demos', (route) => route.abort());
  await page.goto('/#artifacts');
  await expect(page.getByText(/^Could not load demo bundles: /)).toBeVisible();
  await expect(page.locator('.demo-card')).toHaveCount(0);
});

test('the fluent explorer says when the bundle list cannot load', async ({ page }) => {
  await page.route('**/api/demos', (route) => route.fulfill(fail(503)));
  await page.goto('/#fluent');
  const explorer = page.locator('now-fluent-explorer');
  await expect(explorer.getByRole('alert')).toHaveText('Could not load the demo bundles (HTTP 503).');
  await expect(explorer.locator('select')).toHaveCount(0);
});

test('the welcome guide says when it cannot save the startup choice', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('now-workbench-show-welcome', 'true'));
  await page.route('**/api/settings', (route) =>
    route.request().method() === 'PUT' ? route.fulfill(fail(500)) : route.continue(),
  );
  await page.goto('/#home');
  const modal = page.locator('now-welcome-modal');
  await modal.getByLabel("Don't show this welcome guide on startup").check();
  await expect(modal.getByRole('alert')).toHaveText('Could not save this choice for your account (HTTP 500).');
});

test('the profile says when it cannot load and shows no made-up details', async ({ page }) => {
  await page.route('**/api/profile', (route) => route.fulfill(fail(500)));
  await page.goto('/#admin/profile');
  const profile = page.locator('now-profile-settings');
  await expect(profile.getByRole('alert')).toContainText('boom');
  await expect(profile.getByLabel('Display name')).toHaveValue('');
});
