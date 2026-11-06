// web/e2e/deepfix-workbench-context.spec.ts
// The shared store reads the real list shapes of /api/instances and /api/demos.
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, seedInstance, test } from './fixtures';

test('synthesizer instance picker lists registered instances from the bare list response', async ({
  page,
  request,
}) => {
  await seedInstance(request, {
    name: 'Ctx Dev Instance',
    url: 'fake://ctx-dev.service-now.com',
    username: 'ctx.admin',
    password: 'Ctx-S3cret-pw!',
    is_default: true,
  });

  await page.goto('/#synthesizer');

  const picker = page.locator('select.instance-picker-select');
  await expect(picker.locator('option')).toHaveCount(1);
  await expect(picker.locator('option').first()).toContainText('Ctx Dev Instance');
});

test('a failing instances route shows an error banner instead of an empty picker', async ({
  page,
}) => {
  await page.route('**/api/instances', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"db down"}' });
  });
  await page.goto('/#synthesizer');
  await expect(page.getByRole('alert')).toContainText('Could not load instances (HTTP 500)');
});
