// web/e2e/deepfix-presenter-hud.spec.ts
// Presenter HUD must show real errors, never a fabricated runbook (D2).
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, test } from './fixtures';

const runbook = {
  bundle_id: 'sample-ai-assistant',
  title: 'Real Runbook',
  narrative: 'n',
  personas: [],
  stages: [
    {
      step_number: 1,
      title: 'Stage One',
      instructions: ['do it'],
      talking_points: ['say it'],
    },
  ],
};

async function openHud(page: import('@playwright/test').Page) {
  await page.goto('/');
  await page.evaluate(() => {
    document.querySelector('now-presenter-hud')?.remove();
    const hud = document.createElement('now-presenter-hud') as HTMLElement & {
      bundleId: string;
      visible: boolean;
    };
    hud.bundleId = 'sample-ai-assistant';
    hud.visible = true;
    document.body.appendChild(hud);
  });
}

test('runbook 404 shows no-guide message and no fabricated playbook', async ({ page }) => {
  await page.route('**/api/demos/*/runbook', (route) =>
    route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"nf"}' }),
  );
  await openHud(page);
  await expect(page.getByTestId('hud-load-error')).toContainText(
    'No walkthrough guide for this demo',
  );
  await expect(page.getByText('Enterprise AI Copilot')).toHaveCount(0);
});

test('runbook 500 shows could-not-load error', async ({ page }) => {
  await page.route('**/api/demos/*/runbook', (route) =>
    route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"boom"}' }),
  );
  await openHud(page);
  await expect(page.getByTestId('hud-load-error')).toContainText('Could not load runbook: boom');
  await expect(page.getByText('Enterprise AI Copilot')).toHaveCount(0);
});

test('verify sends no fake_mode and shows failure as non-success', async ({ page }) => {
  let body: Record<string, unknown> = {};
  await page.route('**/api/demos/*/runbook', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(runbook) }),
  );
  await page.route('**/api/demos/*/runbook/verify-stage', (route) => {
    body = route.request().postDataJSON();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: false, message: 'No records found' }),
    });
  });
  await openHud(page);
  await page.getByTitle('Verify Stage State').click();
  const msg = page.getByTestId('hud-verification-message');
  await expect(msg).toContainText('No records found');
  await expect(msg).not.toHaveClass(/success/);
  expect(body).not.toHaveProperty('fake_mode');
});

test('verify HTTP error shows an error message', async ({ page }) => {
  await page.route('**/api/demos/*/runbook', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(runbook) }),
  );
  await page.route('**/api/demos/*/runbook/verify-stage', (route) =>
    route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: '{"detail":"Target instance not found."}',
    }),
  );
  await openHud(page);
  await page.getByTitle('Verify Stage State').click();
  const msg = page.getByTestId('hud-verification-message');
  await expect(msg).toContainText('Verification failed: Target instance not found.');
  await expect(msg).not.toHaveClass(/success/);
});
