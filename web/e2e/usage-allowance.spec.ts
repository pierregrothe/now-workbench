// web/e2e/usage-allowance.spec.ts
// The monthly Claude allowance in the chat (ADR-031): the 80% warning and the refusal show.
// Author: Pierre Grothe
// Date: 2026-11-07
import { expect, test } from './fixtures';

const WARNING =
  'You have used 85% of your monthly Claude allowance (85,000 of 100,000 tokens). It resets on December 1.';
const REFUSAL =
  'You have used your monthly Claude allowance (100,000 tokens). It resets on December 1; an administrator can raise it.';

async function ask(page: import('@playwright/test').Page): Promise<void> {
  const box = page.locator('.prompt-box').first();
  await box.getByPlaceholder('Find answers, automate tasks, or create content instantly').fill('How many instances?');
  await box.getByRole('button', { name: 'Send' }).click();
}

test('the 80% warning shows next to the prompt', async ({ page }) => {
  // The real server answers; only the warning header is added to its response.
  await page.route('**/api/threads/*/messages', async (route) => {
    if (route.request().method() !== 'POST') return route.continue();
    const response = await route.fetch();
    await route.fulfill({ response, headers: { ...response.headers(), 'x-usage-warning': WARNING } });
  });
  await page.goto('/');
  await ask(page);
  await expect(page.locator('now-chat-view').getByText('How many instances?').first()).toBeVisible();
  await expect(page.getByText(WARNING)).toBeVisible();
});

test('a spent allowance is refused with the reason', async ({ page }) => {
  await page.route('**/api/threads/*/messages', async (route) => {
    if (route.request().method() !== 'POST') return route.continue();
    await route.fulfill({ status: 429, contentType: 'application/json', body: JSON.stringify({ detail: REFUSAL }) });
  });
  await page.goto('/');
  await ask(page);
  await expect(page.getByText(`Could not send message: ${REFUSAL}`)).toBeVisible();
});

test('administrators set a person allowance on the Team screen', async ({ page, request }) => {
  const sc = 'allowance-sc@example.com';
  expect((await request.put(`/api/team/${sc}`, { data: { solution_consultant: true } })).ok()).toBeTruthy();
  try {
    await page.goto('/#admin/team');
    const card = page.locator('now-usage-allowances');
    const row = card.locator('.usage-row', { hasText: sc });
    await expect(row).toContainText('0 of 10,000,000 tokens (0%)');

    await row.getByLabel(`Monthly allowance for ${sc}`).fill('500000');
    await row.getByRole('button', { name: 'Set' }).click();
    await expect(row).toContainText('0 of 500,000 tokens (0%) - own allowance');
    await expect(card.getByRole('status')).toHaveText(`Allowance saved for ${sc}.`);

    await row.getByRole('button', { name: 'Use default' }).click();
    await expect(row).toContainText('0 of 10,000,000 tokens (0%)');
    await expect(row).not.toContainText('own allowance');
  } finally {
    await request.delete(`/api/usage/allowances/${sc}`).catch(() => undefined);
    await request.delete(`/api/team/${sc}`);
  }
});

test('everyone sees their own usage on the Profile screen', async ({ page }) => {
  await page.goto('/#admin/profile');
  await expect(page.getByTestId('own-usage')).toContainText('tokens (administrator, no limit).');
});

test('the default allowance is a conversation limit', async ({ page }) => {
  await page.goto('/#admin/limits');
  await expect(page.getByLabel('Monthly Claude allowance per person (tokens; administrators exempt)')).toHaveValue('10000000');
});
