// web/e2e/deepfix-demo-catalog-deploy.spec.ts
// Demo catalog deploy modal never fabricates a target instance.
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, test } from './fixtures';
import type { Page } from '@playwright/test';

const BUNDLE = {
  manifest: {
    id: 'acme-bundle',
    name: 'Acme Bundle',
    version: '1.0.0',
    description: 'd',
    sn_release: 'Zurich',
    required_plugins: [],
    tags: [],
    created_at: '2026-11-06T00:00:00+00:00',
  },
  bundle_path: '/tmp/acme-bundle',
  fluent_files: [],
  seed_files: [],
  has_walkthrough: false,
};

async function openDeployModal(page: Page): Promise<void> {
  await page.route('**/api/demos', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([BUNDLE]) }),
  );
  await page.goto('/#artifacts');
  await page.getByTitle('Deploy & Seed Demonstration').first().click();
}

test('deploy modal shows an error and no fake instance when /api/instances fails', async ({ page }) => {
  await page.route('**/api/instances', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
  );
  await openDeployModal(page);
  await expect(page.getByTestId('deploy-error')).toContainText('Could not load instances');
  await expect(page.getByText('Alec Demo Trial')).toHaveCount(0);
  await expect(page.getByTestId('deploy-submit')).toBeDisabled();
});

test('deploy modal reports an empty registry and disables Deploy', async ({ page }) => {
  await page.route('**/api/instances', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  );
  await openDeployModal(page);
  await expect(page.getByTestId('deploy-error')).toContainText('No ServiceNow instances registered');
  await expect(page.getByText('Alec Demo Trial')).toHaveCount(0);
  await expect(page.getByTestId('deploy-submit')).toBeDisabled();
});

test('a partial rollback is reported as incomplete and the rollback control stays', async ({
  page,
}) => {
  const instance = {
    id: 'i-1',
    name: 'Lab Instance',
    url: 'fake://lab.service-now.com',
    username: 'admin',
    has_password: false,
    auth_type: 'basic',
    release: 'Unknown',
    purpose: 'demo',
    is_default: true,
    status: 'authenticated',
    last_checked: null,
    profile: null,
  };
  await page.route('**/api/instances', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([instance]) }),
  );
  await page.route('**/api/demos/acme-bundle/seed', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'op-1',
        bundle_id: 'acme-bundle',
        instance_id: 'i-1',
        status: 'completed',
        created_records: [
          { table: 'incident', sys_id: 'a' },
          { table: 'incident', sys_id: 'b' },
        ],
        created_at: '2026-11-06T00:00:00+00:00',
      }),
    }),
  );
  await page.route('**/api/demos/seed/op-1/rollback**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: false,
        operation_id: 'op-1',
        deleted_count: 1,
        errors: ['incident/b: HTTP 500'],
      }),
    }),
  );
  await openDeployModal(page);
  await page.getByTestId('deploy-submit').click();
  await page.getByTitle('Rollback Seeded Records').click();

  await expect(page.getByTestId('deploy-error')).toContainText('Rollback incomplete (1 removed)');
  await expect(page.getByTestId('deploy-error')).toContainText('incident/b: HTTP 500');
  // The operation id is kept so the user can retry the rollback.
  await expect(page.getByTitle('Rollback Seeded Records')).toBeVisible();
});
