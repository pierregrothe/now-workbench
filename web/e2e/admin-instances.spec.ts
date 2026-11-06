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

test('connect form has no release picker; release is detected, not chosen', async ({ page }) => {
  await openInstancesPanel(page);

  // The release family is read from the instance build (glide.war), never asked for.
  await expect(page.getByText(/Release Family/)).toHaveCount(0);
  await expect(page.locator('select')).toHaveCount(0);

  await page.getByPlaceholder('e.g. Novartis BioHealth Sub-Prod').fill('Form Instance');
  await page.getByPlaceholder('https://instancename.service-now.com').fill('fake://form.service-now.com');
  await page.getByPlaceholder('Enter instance credentials').fill('form-pw');
  await page.getByTitle('Connect Instance').click();

  const row = page.getByRole('table').getByRole('row', { name: /Form Instance/ });
  await expect(row).toBeVisible();
  // Simulated (fake://) instances are never probed, so no release is invented.
  await expect(row).toContainText('Unknown');
});
