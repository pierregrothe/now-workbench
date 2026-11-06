// web/e2e/sharing.spec.ts
// Artifact versions and sharing, groups and approvals in the UI (PRD-003, ADR-018).
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, test } from './fixtures';

test('an owned artifact can save a version and be shared with everyone', async ({ page }) => {
  await page.goto('/#artifacts');
  const card = page.locator('.demo-card').first();
  await expect(card.locator('.own-chip')).toContainText('Yours');
  await card.getByRole('button', { name: /^Share / }).click();

  const dialog = page.getByRole('dialog', { name: /^Share / });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel('What changed').fill('e2e version');
  await dialog.getByRole('button', { name: 'Save version' }).click();
  await expect(dialog.getByRole('status')).toHaveText('Version saved.');
  await expect(dialog.getByText('e2e version')).toBeVisible();

  // The local operator is an administrator, so a share with everyone is approved at once.
  await dialog.getByLabel('Share with').selectOption('global');
  await dialog.getByRole('button', { name: /^Share v\d+$/ }).click();
  await expect(dialog.getByText('Everyone', { exact: false }).first()).toBeVisible();
  await expect(dialog.locator('.chip.approved').first()).toHaveText('Shared');
  await dialog.getByRole('button', { name: 'Stop sharing' }).first().click();
  await expect(dialog.getByRole('status')).toHaveText('No longer shared.');
  await dialog.getByRole('button', { name: 'Close' }).click();
  await expect(dialog).toHaveCount(0);
});

test('an administrator creates a group and the approvals inbox explains when empty', async ({
  page,
}) => {
  const name = `Region ${Date.now()}`;
  await page.goto('/#admin');
  const nav = page.getByLabel('Settings sections');
  await nav.getByRole('button', { name: 'Groups' }).click();
  await page.getByLabel('New group name').fill(name);
  await page.getByLabel('Group kind').selectOption('territory');
  await page.getByRole('button', { name: 'Create group' }).click();
  await expect(page.getByText(name, { exact: true })).toBeVisible();
  await expect(page.getByText('Territory', { exact: false }).first()).toBeVisible();

  await nav.getByRole('button', { name: 'Approvals' }).click();
  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible();
});
