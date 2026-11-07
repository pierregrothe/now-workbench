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

test('a tile spans one, two or three columns of the reply', async ({ page }) => {
  const text = (id: string, span: number) => ({ id, type: 'rich-text', title: `Span ${span}`, span, props: { body: id } });
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([reply([text('one', 1), text('two', 2), text('three', 3)])]),
    }),
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/');
  await selectThread(page);
  const width = async (title: string) =>
    (await page.locator('now-tile-renderer').filter({ hasText: title }).boundingBox())!.width;
  const [one, two, three] = [await width('Span 1'), await width('Span 2'), await width('Span 3')];
  // One and two columns share a row; three columns take the whole row.
  expect(Math.round(one + two + 16)).toBeCloseTo(Math.round(three), -1);
  expect(two).toBeGreaterThan(one * 1.8);
  await page.setViewportSize({ width: 800, height: 1000 });
  // Narrow screens stack every tile at full width.
  await expect.poll(async () => Math.round(await width('Span 1'))).toBe(Math.round(await width('Span 3')));
});
