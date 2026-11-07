// web/e2e/reply-feedback.spec.ts
// The feedback row under Otto's replies: rate, change, Get help, and the feedback list.
// Author: Pierre Grothe
// Date: 2026-11-07
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import type { APIRequestContext, Page } from '@playwright/test';
import { expect, test } from './fixtures';

const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));
let seq = 0;

/**
 * Store a conversation holding one Otto reply through the real repository code, as the reply
 * path would (the API only takes questions). Returns the reply's message id.
 */
function seedConversation(title: string, reply: string): string {
  seq += 1;
  const ids = { thread: `t-fb-${Date.now()}-${seq}`, message: `m-fb-${Date.now()}-${seq}` };
  const script = [
    'import json, sys',
    'from now_workbench.domains.conversations import ChatMessageRecord, ChatThreadCreate, ThreadRepository',
    'from now_workbench.platform.db.session import db_session',
    'from now_workbench.platform.owner import LOCAL_EMAIL, owner_scope',
    'd = json.load(sys.stdin)',
    'with db_session() as conn, owner_scope(LOCAL_EMAIL):',
    '    repo = ThreadRepository(conn)',
    "    repo.create_thread(ChatThreadCreate(id=d['thread'], title=d['title']))",
    "    repo.add_message(ChatMessageRecord(id=d['message'], thread_id=d['thread'], role='assistant', content=d['reply']))",
  ].join('\n');
  execFileSync('uv', ['run', 'python', '-c', script], {
    cwd: REPO_ROOT,
    input: JSON.stringify({ ...ids, title, reply }),
    env: { ...process.env, WORKBENCH_DATA_DIR: '.e2e/data', WORKBENCH_KEY_FILE: '.e2e/keys/master.key' },
    stdio: ['pipe', 'inherit', 'inherit'],
  });
  return ids.message;
}

async function openConversation(page: Page, title: string): Promise<void> {
  await page.goto('/#home');
  await page.locator('now-nav-rail').getByText(title, { exact: true }).click();
}

async function storedRating(request: APIRequestContext, reply: string): Promise<{ rating: string; comment: string }[]> {
  const res = await request.get('/api/feedback');
  expect(res.ok()).toBeTruthy();
  return ((await res.json()) as { reply: string; rating: string; comment: string }[])
    .filter((f) => f.reply === reply)
    .map(({ rating, comment }) => ({ rating, comment }));
}

test('rating a reply stores it and the button shows the choice', async ({ page, request }) => {
  const reply = `Reply to rate ${Date.now()}`;
  seedConversation('Feedback rate', reply);
  await openConversation(page, 'Feedback rate');
  // Each row's buttons are named after their reply.
  const up = page.getByRole('button', { name: `Good reply: "${reply}"` });
  await expect(page.getByText(reply)).toBeVisible();
  await expect(up).toHaveAttribute('aria-pressed', 'false');
  await expect(page.getByRole('textbox', { name: 'Feedback comment' })).toHaveCount(0);

  await up.click();
  await expect(page.getByRole('status').filter({ hasText: 'Thanks for the feedback.' })).toBeVisible();
  await expect(up).toHaveAttribute('aria-pressed', 'true');
  await expect(up).toBeFocused();
  await page.getByRole('textbox', { name: 'Feedback comment' }).fill('Clear and right');
  await page.getByRole('button', { name: 'Send', exact: true }).last().click();
  await expect(page.getByRole('status').filter({ hasText: 'Thanks, comment saved.' })).toBeVisible();
  expect(await storedRating(request, reply)).toEqual([{ rating: 'up', comment: 'Clear and right' }]);

  // The stored choice comes back with the conversation.
  await page.reload();
  await openConversation(page, 'Feedback rate');
  await expect(page.getByRole('button', { name: 'Good reply' })).toHaveAttribute('aria-pressed', 'true');
});

test('changing the rating replaces it and keeps the comment, also after a reload', async ({ page, request }) => {
  const reply = `Reply to change ${Date.now()}`;
  seedConversation('Feedback change', reply);
  await openConversation(page, 'Feedback change');
  await page.getByRole('button', { name: 'Good reply' }).click();
  await page.getByRole('textbox', { name: 'Feedback comment' }).fill('Mostly right');
  await page.getByRole('button', { name: 'Send', exact: true }).last().click();
  await expect(page.getByRole('status').filter({ hasText: 'Thanks, comment saved.' })).toBeVisible();

  await page.reload();
  await openConversation(page, 'Feedback change');
  const down = page.getByRole('button', { name: 'Bad reply' });
  await down.click();
  await expect(down).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'Good reply' })).toHaveAttribute('aria-pressed', 'false');
  // Thumbs down is not shown in the "good" green.
  await expect(down).not.toHaveCSS('color', 'rgb(31, 122, 51)');
  await expect(page.getByRole('textbox', { name: 'Feedback comment' })).toHaveValue('Mostly right');
  await expect.poll(() => storedRating(request, reply)).toEqual([{ rating: 'down', comment: 'Mostly right' }]);
});

test('a failed save says so and changes nothing', async ({ page, request }) => {
  const reply = `Reply that fails ${Date.now()}`;
  seedConversation('Feedback fails', reply);
  await page.route('**/api/feedback/*', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Database is locked.' }) }),
  );
  await openConversation(page, 'Feedback fails');
  const up = page.getByRole('button', { name: 'Good reply' });
  await up.click();
  await expect(page.getByRole('alert').filter({ hasText: 'Could not save: Database is locked.' })).toBeVisible();
  await expect(up).toHaveAttribute('aria-pressed', 'false');
  await expect(page.getByRole('textbox', { name: 'Feedback comment' })).toHaveCount(0);
  expect(await storedRating(request, reply)).toEqual([]);
});

test('Get help opens the help guide', async ({ page }) => {
  seedConversation('Feedback help', `Reply needing help ${Date.now()}`);
  await openConversation(page, 'Feedback help');
  await page.getByRole('button', { name: 'Get help' }).click();
  await expect(page.getByRole('dialog', { name: 'Welcome to Now Workbench' })).toBeVisible();
});

test('the administrator sees ratings with the reply text and who gave them', async ({ page, request }) => {
  const reply = `Reply for the list ${Date.now()}\n${'A long answer line. '.repeat(40)}`;
  const id = seedConversation('Feedback list', reply);
  const put = await request.put(`/api/feedback/${id}`, { data: { rating: 'down', comment: 'Missed the point' } });
  expect(put.ok()).toBeTruthy();

  await page.goto('/#admin/feedback');
  const item = page.getByTestId('feedback-item').filter({ hasText: 'Reply for the list' });
  await expect(item).toBeVisible();
  await expect(item).toContainText('Thumbs down');
  await expect(item).toContainText('Missed the point');
  await expect(item).toContainText('local@localhost');
  // A long reply is clipped until it is expanded.
  const more = item.getByRole('button', { name: 'Show the whole reply' });
  await expect(more).toHaveAttribute('aria-expanded', 'false');
  const clipped = (await item.locator('.fb-reply').boundingBox())?.height ?? 0;
  await more.click();
  await expect(item.getByRole('button', { name: 'Show less' })).toHaveAttribute('aria-expanded', 'true');
  expect((await item.locator('.fb-reply').boundingBox())?.height ?? 0).toBeGreaterThan(clipped);
});

test('a consultant sees only their own list, without the owner column', async ({ page }) => {
  await page.route('**/api/profile', async (route) => {
    const res = await route.fetch();
    const profile = await res.json();
    await route.fulfill({ response: res, json: { ...profile, roles: ['solution_consultant'] } });
  });
  await page.route('**/api/feedback', (route) =>
    route.fulfill({
      json: [
        {
          message_id: 'm1',
          thread_id: 't1',
          owner_email: 'ana@example.com',
          rating: 'up',
          comment: '',
          reply: 'Ana rated this one.',
          created_at: '2026-11-07T10:00:00Z',
          updated_at: '2026-11-07T10:00:00Z',
        },
      ],
    }),
  );
  await page.goto('/#admin/feedback');
  const item = page.getByTestId('feedback-item');
  await expect(item).toContainText('Ana rated this one.');
  await expect(item).not.toContainText('ana@example.com');
  await expect(page.getByText(/ratings you gave/)).toBeVisible();
});

test('the feedback list reports a failed load', async ({ page }) => {
  await page.route('**/api/feedback', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'boom' }) }),
  );
  await page.goto('/#admin/feedback');
  await expect(page.getByRole('alert').filter({ hasText: 'Could not load feedback: boom' })).toBeVisible();
  await expect(page.getByTestId('feedback-item')).toHaveCount(0);
});

test('the feedback row fits a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  seedConversation('Feedback phone', `Reply on a phone ${Date.now()}`);
  await page.goto('/#home');
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.locator('now-nav-rail').getByText('Feedback phone', { exact: true }).click();
  const up = page.getByRole('button', { name: 'Good reply' });
  await expect(up).toBeVisible();
  const box = await up.boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(40);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
