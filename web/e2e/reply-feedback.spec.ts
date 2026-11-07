// web/e2e/reply-feedback.spec.ts
// The feedback row under Otto's replies: rate, change, Get help, and the feedback list.
// Author: Pierre Grothe
// Date: 2026-11-07
import type { APIRequestContext, Page } from '@playwright/test';
import { expect, test } from './fixtures';

/** A real conversation holding one stored Otto reply (a non-user message gets no reply built). */
async function seedConversation(request: APIRequestContext, title: string, reply: string): Promise<string> {
  const thread = await request.post('/api/threads', { data: { title } });
  expect(thread.ok()).toBeTruthy();
  const id = ((await thread.json()) as { id: string }).id;
  const res = await request.post(`/api/threads/${id}/messages`, { data: { content: reply, role: 'assistant' } });
  expect(res.ok()).toBeTruthy();
  await res.text();
  return id;
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
  await seedConversation(request, 'Feedback rate', reply);
  await openConversation(page, 'Feedback rate');
  const up = page.getByRole('button', { name: 'Good reply' });
  await expect(page.getByText(reply)).toBeVisible();
  await expect(up).toHaveAttribute('aria-pressed', 'false');

  await up.click();
  await expect(page.getByText('Thanks for the feedback.')).toBeVisible();
  await expect(up).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('textbox', { name: 'Feedback comment' }).fill('Clear and right');
  await page.getByRole('button', { name: 'Send', exact: true }).last().click();
  await expect(page.getByText('Thanks, comment saved.')).toBeVisible();
  expect(await storedRating(request, reply)).toEqual([{ rating: 'up', comment: 'Clear and right' }]);

  // The stored choice comes back with the conversation.
  await page.reload();
  await openConversation(page, 'Feedback rate');
  await expect(page.getByRole('button', { name: 'Good reply' })).toHaveAttribute('aria-pressed', 'true');
});

test('changing the rating replaces it rather than adding another', async ({ page, request }) => {
  const reply = `Reply to change ${Date.now()}`;
  await seedConversation(request, 'Feedback change', reply);
  await openConversation(page, 'Feedback change');
  await page.getByRole('button', { name: 'Good reply' }).click();
  await expect(page.getByText('Thanks for the feedback.')).toBeVisible();

  const down = page.getByRole('button', { name: 'Bad reply' });
  await down.click();
  await expect(down).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'Good reply' })).toHaveAttribute('aria-pressed', 'false');
  await expect.poll(() => storedRating(request, reply)).toEqual([{ rating: 'down', comment: '' }]);
});

test('Get help opens the help guide', async ({ page, request }) => {
  await seedConversation(request, 'Feedback help', `Reply needing help ${Date.now()}`);
  await openConversation(page, 'Feedback help');
  await page.getByRole('button', { name: 'Get help' }).click();
  await expect(page.getByRole('dialog', { name: 'Welcome to Now Workbench' })).toBeVisible();
});

test('the administrator sees ratings with the reply text in Settings', async ({ page, request }) => {
  const reply = `Reply for the list ${Date.now()}`;
  const id = await seedConversation(request, 'Feedback list', reply);
  const messages = (await (await request.get(`/api/threads/${id}/messages`)).json()) as { id: string; role: string }[];
  const otto = messages.find((m) => m.role === 'assistant');
  const put = await request.put(`/api/feedback/${otto?.id}`, { data: { rating: 'down', comment: 'Missed the point' } });
  expect(put.ok()).toBeTruthy();

  await page.goto('/#admin/feedback');
  const item = page.getByTestId('feedback-item').filter({ hasText: reply });
  await expect(item).toBeVisible();
  await expect(item).toContainText('Thumbs down');
  await expect(item).toContainText('Missed the point');
  await expect(item).toContainText('local@localhost');
});

test('the feedback row fits a phone', async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await seedConversation(request, 'Feedback phone', `Reply on a phone ${Date.now()}`);
  await page.goto('/#home');
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.locator('now-nav-rail').getByText('Feedback phone', { exact: true }).click();
  const up = page.getByRole('button', { name: 'Good reply' });
  await expect(up).toBeVisible();
  const box = await up.boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(40);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
