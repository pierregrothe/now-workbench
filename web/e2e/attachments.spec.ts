// web/e2e/attachments.spec.ts
// Attaching files to a question and the administrators' conversation limits (ADR-021).
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, test } from './fixtures';

test('a file can be attached, removed, and sent with a question', async ({ page }) => {
  await page.goto('/');
  const box = page.locator('.prompt-box').first();
  await box.locator('#attach-input').setInputFiles([
    { name: 'notes.md', mimeType: 'text/markdown', buffer: Buffer.from('# Notes\nhello') },
    { name: 'extra.txt', mimeType: 'text/plain', buffer: Buffer.from('extra') },
  ]);
  await expect(box.locator('.attach-chip')).toHaveCount(2);
  await box.getByRole('button', { name: 'Remove extra.txt' }).click();
  await expect(box.locator('.attach-chip')).toHaveCount(1);

  await box.getByPlaceholder('Find answers, automate tasks, or create content instantly').fill(
    'Summarize my notes'
  );
  await box.getByRole('button', { name: 'Send' }).click();
  // The test server has no Claude key, so Otto explains instead of ignoring the file.
  await expect(page.getByText('Otto needs a Claude API key to read attached files.')).toBeVisible();
  await expect(page.locator('.attach-chip')).toHaveCount(0);
});

test('an unsupported file is refused with the reason', async ({ page }) => {
  await page.goto('/');
  const box = page.locator('.prompt-box').first();
  await box.locator('#attach-input').setInputFiles({
    name: 'tool.exe',
    mimeType: 'application/octet-stream',
    buffer: Buffer.from([0x4d, 0x5a, 0x00, 0x00]),
  });
  await expect(page.getByText(/Attach a PDF, an image/).first()).toBeVisible();
});

test('administrators can change the conversation limits', async ({ page, request }) => {
  await page.goto('/#admin');
  await page.getByLabel('Settings sections').getByRole('button', { name: 'Conversation limits' }).click();
  const budget = page.getByLabel('Tokens per conversation');
  await expect(budget).toHaveValue(/\d+/);
  await budget.fill('3000000');
  await page.getByRole('button', { name: 'Save limits' }).click();
  await expect(page.getByRole('status')).toHaveText('Limits saved. They apply to everyone right away.');
  expect((await (await request.get('/api/limits')).json()).max_conversation_tokens).toBe(3000000);
  await request.put('/api/limits', { data: { max_conversation_tokens: 2000000 } });
});
