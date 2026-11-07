// web/e2e/otto-tiles.spec.ts
// Otto's visual aids (ADR-025): catalog tiles render with the app's own elements and offer follow-ups.
// Author: Pierre Grothe
// Date: 2026-11-07
import { expect, selectThread, test } from './fixtures';

const reply = (tiles: unknown[]) => ({
  id: 'm-aids',
  thread_id: 'default-thread',
  role: 'assistant',
  content: 'Here is the picture.',
  widget_type: 'generative_tiles',
  widget_data: { tiles, layout: '2-col' },
  created_at: '2026-11-07T12:00:00Z',
});

const instance = {
  id: 'alpha',
  name: 'Alpha Lab',
  url: 'https://alpha.service-now.com',
  username: 'admin',
  release: 'Australia',
  is_default: true,
  status: 'authenticated',
  last_checked: null,
  purpose: 'demo',
  profile: null,
};

test('generic and entity tiles render as visual aids', async ({ page }) => {
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        reply([
          { id: 'k', type: 'kpis', title: 'Health', props: { items: [{ label: 'Instances', value: '3', tone: 'good' }] } },
          { id: 's', type: 'steps', title: 'Plan', props: { items: [{ label: 'Seed records', status: 'done' }, { label: 'Capture proof', status: 'todo' }] } },
          { id: 'c', type: 'comparison', title: 'Options', props: { columns: [{ heading: 'Clone', points: ['Keeps the original'] }, { heading: 'Edit', points: ['Changes it'] }] } },
          { id: 'w', type: 'callout', title: 'Heads up', props: { tone: 'warning', body: 'Production instance' } },
          { id: 'i', type: 'instance', props: instance },
          { id: 'd', type: 'diagnostics', props: {} },
        ]),
      ]),
    }),
  );
  await page.goto('/');
  await selectThread(page);
  await expect(page.getByText('Instances', { exact: true })).toBeVisible();
  await expect(page.getByText('Seed records')).toBeVisible();
  await expect(page.getByText('Keeps the original')).toBeVisible();
  await expect(page.getByRole('alert').filter({ hasText: 'Production instance' })).toBeVisible();
  // The instance tile is the Settings hero card itself, and diagnostics is the live card.
  await expect(page.getByText('Alpha Lab')).toBeVisible();
  await expect(page.getByText('Active Deployment Target')).toBeVisible();
  await expect(page.getByText('Platform Runtime Diagnostics')).toBeVisible();
});

test('a follow-up action on a tile is asked as the next message', async ({ page }) => {
  await page.route('**/api/threads/default-thread/messages', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        reply([
          {
            id: 't',
            type: 'rich-text',
            title: 'Why it failed',
            props: { body: 'The instance refused the login.', actions: [{ id: 'ask', label: 'Retest it', prompt: 'Test Alpha Lab again' }] },
          },
        ]),
      ]),
    });
  });
  await page.goto('/');
  await selectThread(page);
  const sent = page.waitForRequest(
    (r) => r.method() === 'POST' && r.url().includes('/api/threads/default-thread/messages'),
  );
  await page.getByRole('button', { name: 'Retest it' }).click();
  expect((await sent).postDataJSON().content).toBe('Test Alpha Lab again');
});
