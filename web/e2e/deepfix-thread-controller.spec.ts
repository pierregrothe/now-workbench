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
  await expect(page.getByText('Otto', { exact: true }).first()).toBeVisible({ timeout: 30000 });
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
  await expect(page.getByText('Approved', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirm', exact: true })).toHaveCount(0);
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
  await expect(page.getByText('Cancelled', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancel', exact: true })).toHaveCount(0);
  expect(posts).toBe(0);
});

const instanceCardRecord = {
  id: 'm-card',
  thread_id: 'default-thread',
  role: 'assistant',
  content: 'You have one instance.',
  widget_type: 'generative_tiles',
  widget_data: {
    tiles: [
      {
        id: 'tile-instance-card-i1',
        type: 'instance-card',
        title: 'Demo Alecto',
        props: {
          name: 'Demo Alecto',
          release: 'Australia',
          url: 'https://x.service-now.com',
          status: 'authenticated',
          actions: [
            { id: 'manage', label: 'Edit in Settings', variant: 'secondary' },
            { id: 'delete_instance', label: 'Delete', variant: 'secondary' },
          ],
        },
      },
    ],
  },
  created_at: '2026-11-06T12:00:00Z',
};

test('instance card actions open Settings instead of doing nothing', async ({ page }) => {
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([instanceCardRecord]) }),
  );
  await page.goto('/');
  await selectThread(page);
  await page.getByRole('button', { name: 'Edit in Settings' }).click();
  await expect(page).toHaveURL(/#admin/);
});

test('the prompt box is docked below the conversation', async ({ page }) => {
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([instanceCardRecord]) }),
  );
  await page.goto('/');
  await selectThread(page);
  const prompt = page.getByRole('textbox').last();
  await expect(prompt).toBeVisible();
  const box = await prompt.boundingBox();
  const viewport = page.viewportSize();
  expect(box!.y).toBeGreaterThan(viewport!.height / 2);
});

test('a reply with tool runs shows a collapsible steps list from the backend', async ({ page }) => {
  const withSteps = {
    ...instanceCardRecord,
    widget_data: {
      ...instanceCardRecord.widget_data,
      steps: [
        { label: 'Listed 1 instance', ok: true },
        { label: 'Probe failed', ok: false },
      ],
    },
  };
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([withSteps]) }),
  );
  await page.goto('/');
  await selectThread(page);
  const summary = page.getByText('Thought for a moment', { exact: false });
  await expect(summary).toContainText('2 steps');
  await expect(page.getByText('Listed 1 instance')).toBeHidden();
  await summary.click();
  await expect(page.getByText('Listed 1 instance')).toBeVisible();
  await expect(page.getByText('Probe failed')).toBeVisible();
});
