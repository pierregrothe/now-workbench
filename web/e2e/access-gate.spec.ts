// web/e2e/access-gate.spec.ts
// First-run setup dialog, no-access page, and the admin Team section.
// Author: Pierre Grothe
// Date: 2026-11-06
import type { Page } from '@playwright/test';
import { expect, test } from './fixtures';

async function status(page: Page, body: Record<string, unknown>): Promise<void> {
  await page.route('**/api/setup/status', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) }),
  );
}

test('first run forces the setup dialog before anything else', async ({ page }) => {
  await status(page, { setup_required: true, email: 'owner@example.com', has_role: false, auth_mode: 'cloudflare' });
  let posted: unknown = null;
  await page.route('**/api/setup', async (route) => {
    posted = route.request().postDataJSON();
    const ok = (posted as { code: string }).code.toUpperCase() === 'KQ7M-R3TX';
    await route.fulfill({
      status: ok ? 200 : 400,
      contentType: 'application/json',
      body: JSON.stringify(ok ? { setup_required: false, email: 'owner@example.com', has_role: true, auth_mode: 'cloudflare' } : { detail: 'That setup code is not correct. 4 attempt(s) left.' }),
    });
  });
  await page.goto('/');
  const dialog = page.getByRole('dialog', { name: 'Set up this workbench' });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('owner@example.com');
  await expect(page.locator('now-nav-rail')).toHaveCount(0);
  await page.getByLabel('Setup code').fill('WRONGONE');
  await page.getByRole('button', { name: 'Become administrator' }).click();
  await expect(page.getByRole('alert')).toContainText('not correct');
  await page.getByLabel('Setup code').fill('kq7m-r3tx');
  await page.getByRole('button', { name: 'Become administrator' }).click();
  await expect.poll(() => posted).toEqual({ code: 'kq7m-r3tx' });
});

test('a signed-in person without a role sees a no-access page', async ({ page }) => {
  await status(page, { setup_required: false, email: 'stranger@example.com', has_role: false, auth_mode: 'cloudflare' });
  await page.goto('/');
  await expect(page.getByRole('alertdialog', { name: 'No access yet' })).toContainText('stranger@example.com');
  await expect(page.locator('now-nav-rail')).toHaveCount(0);
});

test('local mode opens straight into the app', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('now-nav-rail')).toBeVisible();
  await expect(page.getByRole('dialog', { name: 'Set up this workbench' })).toHaveCount(0);
});

test('an admin adds, changes and removes a team member', async ({ page, request }) => {
  await request.put('/api/team/boss%40example.com', { data: { admin: true, solution_consultant: true } });
  await request.delete('/api/team/sc%40example.com');
  await page.goto('/#admin');
  await page.getByLabel('Settings sections').getByRole('button', { name: 'Team' }).click();
  await page.getByLabel('New member email').fill('sc@example.com');
  await page.getByRole('button', { name: 'Add person' }).click();
  await expect(page.getByRole('status')).toContainText('sc@example.com added.');
  const adminBox = page.getByLabel('Administrator for sc@example.com');
  await expect(adminBox).not.toBeChecked();
  await adminBox.check();
  await expect(page.getByRole('status')).toContainText('Roles updated');
  await adminBox.uncheck();
  await page.getByRole('row', { name: /sc@example.com/ }).getByRole('button', { name: 'Remove' }).click();
  await expect(page.getByRole('status')).toContainText('sc@example.com removed.');
});
