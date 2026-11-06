// web/e2e/deepfix-demo-pipeline-controller.spec.ts
// Synthesizer view calls the real /api/demos synthesize and seed routes with valid payloads.
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, test } from './fixtures';

const RESULT = {
  bundle_id: 'acme-bundle',
  bundle_path: '/tmp/acme-bundle',
  title: 'Acme Demo',
  customer_name: 'Acme Global',
  industry: 'Financial Services',
  fluent_table_name: 'x_acme_case',
  fluent_code: '// code',
  seed_records: [],
  sys_properties: {},
  narrative_markdown: '# Narrative',
};

test('synthesize and seed hit the real demo routes with backend-shaped payloads', async ({
  page,
}) => {
  let synthBody: Record<string, unknown> | null = null;
  let seedUrl = '';
  await page.route('**/api/demos/synthesize', async (route) => {
    synthBody = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(RESULT) });
  });
  await page.route('**/api/demos/*/seed', async (route) => {
    seedUrl = route.request().url();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'op1',
        bundle_id: 'acme-bundle',
        instance_id: 'inst1',
        status: 'completed',
        created_records: [],
        created_at: '2026-11-06T00:00:00+00:00',
      }),
    });
  });

  await page.goto('/#synthesizer');
  await page.getByRole('button', { name: 'Synthesize Demo Bundle' }).click();
  await expect(page.getByText('Acme Demo')).toBeVisible();

  expect(synthBody).not.toBeNull();
  const body = synthBody as unknown as Record<string, unknown>;
  expect(body).toHaveProperty('use_case');
  expect(body).not.toHaveProperty('sn_release');
  expect(body).not.toHaveProperty('prompt');
  expect(body).not.toHaveProperty('release_target');
  expect(body).not.toHaveProperty('personas');

  await page.getByRole('button', { name: '1-Click Seed Target' }).click();
  await expect(page.getByText(/Successfully seeded/)).toBeVisible();
  expect(seedUrl).toContain('/api/demos/acme-bundle/seed');
});

test('a rejected synthesize shows the backend reason in the view', async ({ page }) => {
  await page.route('**/api/demos/synthesize', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'No release to build for: register an instance.' }),
    });
  });
  await page.goto('/#synthesizer');
  await page.getByRole('button', { name: 'Synthesize Demo Bundle' }).click();
  await expect(page.getByRole('alert')).toContainText('No release to build for');
});

test('a failed seed is styled as an error, not a success', async ({ page }) => {
  await page.route('**/api/demos/synthesize', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(RESULT) });
  });
  await page.route('**/api/demos/*/seed', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'seed exploded' }),
    });
  });
  await page.goto('/#synthesizer');
  await page.getByRole('button', { name: 'Synthesize Demo Bundle' }).click();
  await page.getByRole('button', { name: '1-Click Seed Target' }).click();
  const badge = page.getByText(/Seed error: seed exploded/);
  await expect(badge).toBeVisible();
  await expect(badge).toHaveClass(/error/);
});
