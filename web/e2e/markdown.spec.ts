// web/e2e/markdown.spec.ts
// Otto's text renders as HTML (ADR-028): formatting becomes elements, markup never runs.
// Author: Pierre Grothe
// Date: 2026-11-07
import { expect, selectThread, test } from './fixtures';

const reply = (content: string, tiles: unknown[] = []) => ({
  id: 'm-md',
  thread_id: 'default-thread',
  role: 'assistant',
  content,
  widget_type: 'generative_tiles',
  widget_data: { tiles, layout: '1-col' },
  created_at: '2026-11-07T12:00:00Z',
});

async function show(page: import('@playwright/test').Page, body: unknown) {
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([body]) }),
  );
  await page.goto('/');
  await selectThread(page);
}

test('a reply renders bold, italics, code and safe links as HTML', async ({ page }) => {
  await show(page, reply('Seeded **12 records** on *Alpha* with `seed_activity`; see [the docs](https://example.com/docs).'));
  const md = page.locator('now-markdown').first();
  await expect(md.locator('strong')).toHaveText('12 records');
  await expect(md.locator('em')).toHaveText('Alpha');
  await expect(md.locator('code')).toHaveText('seed_activity');
  const link = md.getByRole('link', { name: 'the docs' });
  await expect(link).toHaveAttribute('href', 'https://example.com/docs');
  await expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  await expect(md).not.toContainText('**');
});

test('text tiles render headings, lists and code blocks', async ({ page }) => {
  const body = '## Plan\n\n1. Seed records\n2. Capture proof\n\n- fast\n- safe\n\n```\nworkbench doctor\n```';
  await show(page, reply('Here is the plan.', [{ id: 't', type: 'rich-text', title: 'Plan', props: { body } }]));
  const md = page.locator('now-tile-renderer now-markdown');
  await expect(md.locator('h4')).toHaveText('Plan');
  await expect(md.locator('ol li')).toHaveText(['Seed records', 'Capture proof']);
  await expect(md.locator('ul li')).toHaveText(['fast', 'safe']);
  await expect(md.locator('pre code')).toHaveText('workbench doctor');
});

test('markup or script in a reply shows as text and never runs', async ({ page }) => {
  let ran = false;
  page.on('dialog', async (d) => {
    ran = true;
    await d.dismiss();
  });
  await show(page, reply('<img src=x onerror="alert(1)"> and [click](javascript:alert(2)) <script>alert(3)</script>'));
  const md = page.locator('now-markdown').first();
  await expect(md).toContainText('<img src=x onerror="alert(1)">');
  await expect(md).toContainText('[click](javascript:alert(2))');
  await expect(md.locator('img, script, a')).toHaveCount(0);
  expect(ran).toBe(false);
});
