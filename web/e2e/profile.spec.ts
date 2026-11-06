// web/e2e/profile.spec.ts
// Profile: built-in avatars, picture upload, servicenow.com email approval by code, SMTP.
// Author: Pierre Grothe
// Date: 2026-11-06
import type { APIRequestContext, Page } from '@playwright/test';
import { expect, test } from './fixtures';

const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
  'base64',
);

async function reset(request: APIRequestContext): Promise<void> {
  await request.delete('/api/profile/avatar');
  await request.put('/api/profile', { data: { display_name: '', email: '' } });
  await request.put('/api/profile/mail', {
    data: { host: '', port: 587, username: '', from_address: '', starttls: true, password: '' },
  });
}

async function openProfile(page: Page): Promise<void> {
  await page.goto('/#admin');
  await page.getByLabel('Settings sections').getByRole('button', { name: 'Profile' }).click();
}

test('choosing a built-in avatar selects it and survives a reload', async ({ page, request }) => {
  await reset(request);
  await openProfile(page);
  const fox = page.getByRole('button', { name: 'Use fox avatar' });
  await fox.click();
  await expect(fox).toHaveAttribute('aria-pressed', 'true');
  await page.reload();
  await page.getByLabel('Settings sections').getByRole('button', { name: 'Profile' }).click();
  await expect(page.getByRole('button', { name: 'Use fox avatar' })).toHaveAttribute('aria-pressed', 'true');
});

test('a picture can be uploaded and removed; unsupported files are refused', async ({ page, request }) => {
  await reset(request);
  await openProfile(page);
  const input = page.locator('input[type=file]');
  await input.setInputFiles({ name: 'me.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg/>') });
  await expect(page.getByRole('alert')).toContainText('PNG, JPEG or WebP');
  await input.setInputFiles({ name: 'me.png', mimeType: 'image/png', buffer: PNG });
  await expect(page.getByText('Picture updated.')).toBeVisible();
  const served = await request.get('/api/profile/avatar');
  expect(served.status()).toBe(200);
  expect(served.headers()['content-type']).toBe('image/png');
  await page.getByRole('button', { name: 'Remove' }).click();
  expect((await request.get('/api/profile/avatar')).status()).toBe(404);
});

test('only an active servicenow.com address can be saved', async ({ page, request }) => {
  await reset(request);
  await openProfile(page);
  await page.getByLabel('ServiceNow email').fill('someone@gmail.com');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.getByRole('alert')).toContainText('servicenow.com');
  await page.getByLabel('Display name').fill('Pierre Grothe');
  await page.getByLabel('ServiceNow email').fill('pierre.grothe@servicenow.com');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.getByText('Profile saved.')).toBeVisible();
  await expect(page.getByText('Not approved', { exact: true })).toBeVisible();
});

test('without email delivery the code cannot be sent and the page says why', async ({ page, request }) => {
  await reset(request);
  await request.put('/api/profile', { data: { display_name: 'P', email: 'p@servicenow.com' } });
  await openProfile(page);
  await expect(page.getByRole('button', { name: 'Send approval code' })).toBeDisabled();
  await expect(page.getByText('Set up email delivery below')).toBeVisible();
});

test('an unreachable mail server is reported, not hidden', async ({ page, request }) => {
  await reset(request);
  await request.put('/api/profile', { data: { display_name: 'P', email: 'p@servicenow.com' } });
  await request.put('/api/profile/mail', {
    data: { host: '127.0.0.1', port: 1, username: '', from_address: 'w@example.test', starttls: false },
  });
  await openProfile(page);
  await page.getByRole('button', { name: 'Send approval code' }).click();
  await expect(page.getByRole('alert')).toContainText('Could not send the email');
  await expect(page.getByLabel('Approval code')).toHaveCount(0);
});

test('entering the emailed code approves the profile', async ({ page, request }) => {
  await reset(request);
  await request.put('/api/profile', { data: { display_name: 'P', email: 'p@servicenow.com' } });
  await request.put('/api/profile/mail', {
    data: { host: 'smtp.example.test', port: 587, username: '', from_address: 'w@example.test', starttls: true },
  });
  const approved = {
    display_name: 'P', email: 'p@servicenow.com', email_verified: true,
    avatar: { kind: 'none', preset: null, url: null }, verification_pending: false, mail_configured: true,
  };
  const pending = { ...approved, email_verified: false, verification_pending: true };
  let sent = false;
  await page.route('**/api/profile/verification/send', async (route) => {
    sent = true;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sent_to: 'p@servicenow.com', expires_in_seconds: 600 }) });
  });
  await page.route('**/api/profile', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(sent ? pending : { ...pending, verification_pending: false }) });
    } else await route.continue();
  });
  await page.route('**/api/profile/verification/confirm', async (route) => {
    const code = route.request().postDataJSON().code;
    if (code.toUpperCase() === 'ABCD-EFGH') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(approved) });
    } else {
      await route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ detail: 'That code is not correct. 4 attempt(s) left.' }) });
    }
  });
  await openProfile(page);
  await page.getByRole('button', { name: 'Send approval code' }).click();
  await expect(page.getByText('Code sent to p@servicenow.com')).toBeVisible();
  await page.getByLabel('Approval code').fill('WRONGONE');
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByRole('alert')).toContainText('not correct');
  await page.getByLabel('Approval code').fill('abcd-efgh');
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByText('Email approved.')).toBeVisible();
  await expect(page.getByText('Approved', { exact: true })).toBeVisible();
});

test('the saved SMTP password is never shown back', async ({ page, request }) => {
  await reset(request);
  await openProfile(page);
  await page.getByLabel('SMTP host').fill('smtp.example.test');
  await page.getByLabel('Send from address').fill('workbench@example.test');
  await page.getByLabel('Password').fill('s3cret-smtp-pw');
  await page.getByRole('button', { name: 'Save email settings' }).click();
  await expect(page.getByText('Email delivery settings saved.')).toBeVisible();
  const mail = await (await request.get('/api/profile/mail')).text();
  expect(mail).not.toContain('s3cret-smtp-pw');
  expect(JSON.parse(mail).has_password).toBe(true);
  await expect(page.getByLabel('Password')).toHaveValue('');
});
