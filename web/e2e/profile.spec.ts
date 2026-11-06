// web/e2e/profile.spec.ts
// Profile: signed-in identity and roles, display name, built-in avatars, picture upload.
// Author: Pierre Grothe
// Date: 2026-11-06
import type { APIRequestContext, Page } from '@playwright/test';
import { expect, test } from './fixtures';

const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
  'base64',
);

async function reset(request: APIRequestContext): Promise<void> {
  await request.delete('/api/profile/avatar');
  await request.put('/api/profile', { data: { display_name: '' } });
}

async function openProfile(page: Page): Promise<void> {
  await page.goto('/#admin');
  await page.getByLabel('Settings sections').getByRole('button', { name: 'Profile' }).click();
}

test('the profile shows who is signed in and both roles in local mode', async ({ page, request }) => {
  await reset(request);
  await openProfile(page);
  await expect(page.getByText('Local mode')).toBeVisible();
  await expect(page.getByLabel('Email')).toHaveValue('local@localhost');
  await expect(page.getByText('Administrator', { exact: true })).toBeVisible();
  await expect(page.getByText('Solution Consultant', { exact: true }).first()).toBeVisible();
});

test('a display name is saved and shown in the sidebar', async ({ page, request }) => {
  await reset(request);
  await openProfile(page);
  await page.getByLabel('Display name').fill('Pierre Grothe');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.getByText('Profile saved.')).toBeVisible();
  await expect(page.locator('now-nav-rail').getByText('Pierre Grothe')).toBeVisible();
});

test('choosing a built-in avatar selects it and survives a reload', async ({ page, request }) => {
  await reset(request);
  await openProfile(page);
  const fox = page.getByRole('button', { name: 'Use fox avatar' });
  await fox.click();
  await expect(fox).toHaveAttribute('aria-pressed', 'true');
  await page.reload();
  await page.getByLabel('Settings sections').getByRole('button', { name: 'Profile' }).click();
  await expect(page.getByRole('button', { name: 'Use fox avatar' })).toHaveAttribute('aria-pressed', 'true');
});

test('a picture can be uploaded and removed; unsupported files are refused', async ({ page, request }) => {
  await reset(request);
  await openProfile(page);
  const input = page.locator('input[type=file]');
  await input.setInputFiles({ name: 'me.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') });
  await expect(page.getByRole('alert')).toContainText('PNG, JPEG or WebP');
  await input.setInputFiles({ name: 'me.png', mimeType: 'image/png', buffer: PNG });
  await expect(page.getByText('Picture updated.')).toBeVisible();
  const served = await request.get('/api/profile/avatar');
  expect(served.status()).toBe(200);
  expect(served.headers()['content-type']).toBe('image/png');
  await page.getByRole('button', { name: 'Remove' }).click();
  expect((await request.get('/api/profile/avatar')).status()).toBe(404);
});

test('a consultant sees no admin sections in Settings', async ({ page }) => {
  await page.route('**/api/profile', (route) => {
    if (route.request().method() !== 'GET') return route.continue();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        email: 'consultant@example.com',
        display_name: '',
        roles: ['solution_consultant'],
        auth_mode: 'cloudflare',
        avatar: { kind: 'none', preset: null, url: null },
      }),
    });
  });
  await page.goto('/#admin');
  const nav = page.getByLabel('Settings sections');
  await expect(nav.getByRole('button', { name: 'Profile' })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'Media capture' })).toBeVisible();
  await expect(nav.getByRole('button', { name: 'Claude and Otto' })).toHaveCount(0);
  // Instances are per user (ADR-018): everyone manages their own.
  await expect(nav.getByRole('button', { name: 'ServiceNow instances' })).toBeVisible();
  await expect(page.locator('now-nav-rail').getByText('Solution Consultant')).toBeVisible();
});

test('the chat send button is the paper-plane icon on a pale-green circle', async ({ page }) => {
  await page.goto('/');
  const send = page.getByRole('button', { name: 'Send' }).first();
  await expect(send).toBeVisible();
  await expect(send.locator('svg path').first()).toHaveAttribute('d', /^M21\.6 2\.4/);
  const bg = await send.evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).toBe('rgb(201, 240, 193)');
});

test('the Learn more pill at the top right opens the welcome guide', async ({ page }) => {
  await page.goto('/');
  const pill = page.getByRole('button', { name: 'Learn more' });
  await expect(pill).toBeVisible();
  const bg = await pill.evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(bg).toBe('rgb(228, 225, 219)');
  await pill.click();
  await expect(page.locator('now-welcome-modal').getByRole('dialog')).toBeVisible();
});
