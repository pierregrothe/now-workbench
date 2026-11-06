// web/e2e/deepfix-thread-controller.spec.ts
// The thread controller reads the real bare-array shapes of /api/threads/{id}/messages.
// Author: Pierre Grothe
// Date: 2026-11-06
import type { Page } from '@playwright/test';
import { expect, test } from './fixtures';

/** Set activeThreadId on the chat view, searching through nested shadow roots. */
const selectThread = (page: Page) =>
  page.evaluate(() => {
    const find = (root: Document | ShadowRoot): Element | null => {
      const hit = root.querySelector('now-chat-view');
      if (hit) return hit;
      for (const el of Array.from(root.querySelectorAll('*'))) {
        if (el.shadowRoot) {
          const inner = find(el.shadowRoot);
          if (inner) return inner;
        }
      }
      return null;
    };
    (find(document) as any).activeThreadId = 'default-thread';
  });

const record = (id: string, role: string, content: string) => ({
  id,
  thread_id: 'default-thread',
  role,
  content,
  widget_type: null,
  widget_data: null,
  created_at: '2026-11-06T12:00:00Z',
});

test('chat view renders loaded thread history from the bare list response', async ({ page }) => {
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([record('m1', 'assistant', 'History hello from Otto')]),
    }),
  );

  await page.goto('/');
  await selectThread(page);

  await expect(page.getByText('History hello from Otto')).toBeVisible();
});

test('chat view shows an explicit error when thread history fails to load', async ({ page }) => {
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({ status: 500, body: '{}' }),
  );

  await page.goto('/');
  await selectThread(page);

  await expect(page.getByText('Could not load thread messages')).toBeVisible();
});

test('first message on Home starts a conversation instead of failing', async ({ page }) => {
  await page.goto('/');
  const box = page.getByRole('textbox').last();
  await box.fill('How many instances do I have?');
  await box.press('Enter');
  await expect(page.getByText('Otto AI Copilot').first()).toBeVisible({ timeout: 30000 });
  await expect(page.getByText(/No active thread/)).toHaveCount(0);
  await expect(page.getByText(/Could not send message/)).toHaveCount(0);
});

const confirmRecord = {
  id: 'm-confirm',
  thread_id: 'default-thread',
  role: 'assistant',
  content: 'Waiting for your confirmation.',
  widget_type: 'generative_tiles',
  widget_data: {
    tiles: [
      {
        id: 'tile-confirm-delete_bundle',
        type: 'rich-text',
        title: 'Confirm action',
        props: {
          body: 'Permanently delete demo bundle x.',
          actions: [
            {
              id: 'confirm_tool',
              label: 'Confirm',
              variant: 'primary',
              tool: 'delete_bundle',
              tool_input: { bundle_id: 'x' },
              plan: 'Delete bundle x',
            },
            { id: 'cancel_tool', label: 'Cancel', variant: 'secondary' },
          ],
        },
      },
    ],
  },
  created_at: '2026-11-06T12:00:00Z',
};

test('Confirm on a tool confirmation tile posts the tool call to the backend', async ({ page }) => {
  let posted: Record<string, unknown> | null = null;
  await page.route('**/api/threads/default-thread/messages', async (route) => {
    if (route.request().method() === 'POST') {
      posted = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([confirmRecord, { ...confirmRecord, id: 'm-done', content: 'Bundle x deleted.', widget_data: null }]),
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([confirmRecord]) });
  });
  await page.goto('/');
  await selectThread(page);
  await page.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(page.getByText('Bundle x deleted.')).toBeVisible();
  const body = posted as unknown as Record<string, any>;
  expect(body.widget_type).toBe('tool_confirm');
  expect(body.widget_data).toEqual({ tool: 'delete_bundle', input: { bundle_id: 'x' } });
});

test('Cancel on a tool confirmation tile sends nothing and says so', async ({ page }) => {
  let posts = 0;
  await page.route('**/api/threads/default-thread/messages', async (route) => {
    if (route.request().method() === 'POST') posts += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([confirmRecord]) });
  });
  await page.goto('/');
  await selectThread(page);
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByText('Action cancelled. Nothing was changed.')).toBeVisible();
  expect(posts).toBe(0);
});
