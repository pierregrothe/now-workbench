// web/e2e/deepfix-fluent-explorer.spec.ts
// The Fluent explorer shows explicit errors instead of fabricated schema or a fake "identical" diff.
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, test } from './fixtures';

test('fluent explorer shows an error and no fabricated table when schema load fails', async ({ page }) => {
  await page.route('**/api/demos/*/fluent', (route) => route.fulfill({ status: 500, body: '{}' }));
  await page.goto('/#/fluent');
  await expect(page.getByText('Could not load schemas:').first()).toBeVisible();
  await expect(page.getByText('x_snc_ai_triage_case')).toHaveCount(0);
});

test('fluent explorer shows a diff failure instead of reporting identical schemas', async ({ page }) => {
  await page.route('**/api/demos/*/fluent', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tables: [] }) }),
  );
  await page.route('**/api/demos/*/fluent/diff', (route) => route.fulfill({ status: 500, body: '{}' }));
  await page.goto('/#/fluent');
  await page.getByTitle('Compare Schema Diff').first().click();
  await expect(page.getByTestId('diff-error').first()).toContainText('Schema diff failed:');
  await expect(page.getByText('0 drift')).toHaveCount(0);
});
