// web/e2e/admin-instances.spec.ts
// Admin panel renders the real instance registry and never exposes passwords (ADR-011, ADR-012).
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, openInstancesPanel, seedInstance, test } from './fixtures';

test('empty registry renders an empty state, never a sample instance', async ({ page }) => {
  await openInstancesPanel(page);

  await expect(page.getByText('Connected Sub-Production Instances (0)')).toBeVisible();
  await expect(page.getByTestId('instances-empty')).toContainText('No ServiceNow instances');
  // Regression: a hardcoded sample instance used to appear when the DB was empty.
  await expect(page.getByText('demoalectriallwfau164179')).toHaveCount(0);
});

test('registered instance is listed and its password never reaches the browser', async ({
  page,
  request,
}) => {
  const secret = 'E2e-S3cret-pw!';
  await seedInstance(request, {
    name: 'E2E Dev Instance',
    url: 'fake://e2e-dev.service-now.com',
    username: 'e2e.admin',
    password: secret,
    is_default: true,
  });

  const apiBodies: string[] = [];
  page.on('response', async (res) => {
    if (res.url().includes('/api/instances')) apiBodies.push(await res.text());
  });

  await openInstancesPanel(page);

  await expect(page.getByText('Connected Sub-Production Instances (1)')).toBeVisible();
  const row = page.getByRole('table').getByRole('row', { name: /E2E Dev Instance/ });
  await expect(row).toBeVisible();
  await expect(row).toContainText('e2e.admin');
  await expect(row).toContainText('authenticated');
  await expect(page.getByTestId('instances-empty')).toHaveCount(0);

  expect(apiBodies.length).toBeGreaterThan(0);
  for (const body of apiBodies) expect(body).not.toContain(secret);
  expect(await page.content()).not.toContain(secret);
});
