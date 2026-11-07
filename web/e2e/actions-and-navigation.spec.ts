// web/e2e/actions-and-navigation.spec.ts
// ADR-026: every capability runs by hand on the Actions screen; Otto's replies move the interface.
// Author: Pierre Grothe
// Date: 2026-11-07
import { expect, seedInstance, selectThread, test } from './fixtures';

test('the Actions screen runs an action and shows its tiles', async ({ page, request }) => {
  await seedInstance(request, { name: 'Alpha Lab', url: 'fake://alpha.service-now.com', is_default: true });
  await page.goto('/#actions/list_instances');
  await expect(page.getByRole('heading', { name: 'List instances' })).toBeVisible();
  await page.getByRole('button', { name: 'Run', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('1 instance(s) registered');
  await expect(page.locator('now-actions-view now-tile-renderer')).toHaveCount(1);
});

test('a change is reviewed, then confirmed, on the Actions screen', async ({ page, request }) => {
  await seedInstance(request, { name: 'Alpha Lab', url: 'fake://alpha.service-now.com', is_default: true });
  await page.goto('/#actions/delete_instances');
  await page.locator('now-actions-view input[type=text]').first().fill('Alpha Lab');
  await page.getByRole('button', { name: 'Review', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Waiting for your confirmation');
  await page.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Deleted 1 instance(s)');
  const left = await (await request.get('/api/instances')).json();
  expect(left).toEqual([]);
});

test('the action search narrows the catalog', async ({ page }) => {
  await page.goto('/#actions');
  await page.getByPlaceholder('Search actions').fill('team');
  await expect(page.getByRole('button', { name: 'List team' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'List instances' })).toHaveCount(0);
});

test('a reply from Otto moves the interface to a Settings section', async ({ page }) => {
  await page.route('**/api/threads/default-thread/messages', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'm-nav',
          thread_id: 'default-thread',
          role: 'assistant',
          content: 'Approvals live here.',
          widget_type: 'generative_tiles',
          widget_data: { tiles: [], steps: [{ label: 'Opened Settings > approvals', ok: true }], ui: [{ type: 'navigate', tab: 'admin', section: 'approvals' }] },
          created_at: '2026-11-07T12:00:00Z',
        },
      ]),
    });
  });
  await page.goto('/');
  await selectThread(page);
  const box = page.getByRole('textbox').last();
  await box.fill('Where do I approve shares?');
  await box.press('Enter');
  await expect(page).toHaveURL(/#admin\/approvals/);
  await expect(page.locator('now-approvals-settings')).toBeVisible();
});

test('a link opens Settings at a section', async ({ page }) => {
  await page.goto('/#admin/groups');
  await expect(page.locator('now-groups-settings')).toBeVisible();
});
