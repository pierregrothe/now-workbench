// web/e2e/deepfix-settings-save.spec.ts
// Settings save must report failure, never a fabricated success (D2).
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, test } from './fixtures';

test('failed settings save shows an error and not the success message', async ({ page }) => {
  await page.goto('/#admin');
  await page.route('**/api/settings', async (route) => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'disk full' }),
      });
    } else {
      await route.continue();
    }
  });

  await page.getByRole('button', { name: 'Save Preferences' }).click();

  const msg = page.getByTestId('save-message');
  await expect(msg).toContainText('Could not save settings: disk full');
  await expect(page.getByText('Saved & encrypted')).toHaveCount(0);
});

test('network failure on settings save shows an error', async ({ page }) => {
  await page.goto('/#admin');
  await page.route('**/api/settings', async (route) => {
    if (route.request().method() === 'PUT') {
      await route.abort();
    } else {
      await route.continue();
    }
  });

  await page.getByRole('button', { name: 'Save Preferences' }).click();

  await expect(page.getByTestId('save-message')).toContainText('Could not save settings');
  await expect(page.getByText('Saved settings in local session')).toHaveCount(0);
});
