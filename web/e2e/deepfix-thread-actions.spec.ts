// web/e2e/deepfix-thread-actions.spec.ts
// Thread create/archive/delete surface API failures and never fabricate local state.
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, test } from './fixtures';

test('new conversation failure shows an error and adds no thread', async ({ page }) => {
  await page.route('**/api/threads', (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({ status: 500, body: '{}' });
    }
    return route.continue();
  });
  await page.goto('/#home');
  await page.getByTitle('Start a new Otto AI conversation').click();

  await expect(page.getByTestId('thread-error')).toContainText('Could not create conversation');
  await expect(page.getByText('New Otto Conversation')).toHaveCount(0);
});
