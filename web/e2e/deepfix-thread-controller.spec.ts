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
