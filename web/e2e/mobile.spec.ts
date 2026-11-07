// web/e2e/mobile.spec.ts
// Phones and tablets (ADR-030): a navigation drawer, no sideways scrolling, touch-friendly fields.
// Author: Pierre Grothe
// Date: 2026-11-07
import type { Page } from '@playwright/test';
import { expect, test } from './fixtures';

const VIEWS = ['home', 'synthesizer', 'capture', 'artifacts', 'fluent', 'actions', 'admin'];

/** The page never scrolls sideways once fonts have loaded. */
async function expectNoSidewaysScroll(page: Page): Promise<void> {
  await page.evaluate(() => document.fonts.ready);
  const { scroll, width } = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    width: window.innerWidth,
  }));
  expect(scroll).toBeLessThanOrEqual(width);
}

test.describe('phone portrait (iPhone size)', () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

  test('navigation lives in a drawer opened from the top bar', async ({ page }) => {
    await page.goto('/#home');
    const rail = page.locator('now-nav-rail');
    const bar = page.locator('now-mobile-bar');
    await expect(bar.getByRole('heading')).toHaveText('Otto');
    await expect(rail).toBeHidden();

    await bar.getByRole('button', { name: 'Open navigation' }).tap();
    await expect(rail).toBeVisible();
    await expect(bar.getByRole('button', { name: 'Close navigation' })).toHaveAttribute('aria-expanded', 'true');

    await rail.getByText('Artifact library').tap();
    await expect(rail).toBeHidden();
    await expect(page).toHaveURL(/#artifacts$/);
    await expect(bar.getByRole('heading')).toHaveText('Artifact library');
  });

  test('the drawer closes on Escape and on a tap outside it', async ({ page }) => {
    await page.goto('/#actions');
    const rail = page.locator('now-nav-rail');
    const open = page.locator('now-mobile-bar').getByRole('button', { name: 'Open navigation' });

    await open.tap();
    await expect(rail).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(rail).toBeHidden();

    await open.tap();
    await expect(rail).toBeVisible();
    await page.mouse.click(370, 400);
    await expect(rail).toBeHidden();
    await expect(page).toHaveURL(/#actions$/);
  });

  for (const view of VIEWS) {
    test(`${view} fits the width of the phone`, async ({ page }) => {
      await page.goto(`/#${view}`);
      await expect(page.locator('now-mobile-bar')).toBeVisible();
      await expectNoSidewaysScroll(page);
    });
  }

  test('settings sections are a strip above the section', async ({ page }) => {
    await page.goto('/#admin');
    const strip = page.getByRole('navigation', { name: 'Settings sections' });
    await strip.getByRole('button', { name: 'Team' }).tap();
    await expect(page.getByRole('heading', { name: 'Team' })).toBeVisible();
    const box = await strip.boundingBox();
    expect(box?.height ?? 0).toBeLessThan(80);
    await expectNoSidewaysScroll(page);
  });

  test('a chosen action shows its form above the list', async ({ page }) => {
    await page.goto('/#actions');
    await page.getByRole('button', { name: 'List conversations' }).tap();
    const panel = page.getByRole('region', { name: 'Action' });
    await expect(panel.getByRole('heading', { name: 'List conversations' })).toBeInViewport();
    const search = page.getByRole('searchbox', { name: 'Search actions' });
    const [form, list] = [await panel.boundingBox(), await search.boundingBox()];
    expect(form!.y).toBeLessThan(list!.y);
  });

  test('fields are at least 16px so iOS does not zoom into them', async ({ page }) => {
    await page.goto('/#actions');
    const size = await page
      .getByRole('searchbox', { name: 'Search actions' })
      .evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(size).toBeGreaterThanOrEqual(16);
  });

  test('the top bar opens the command palette and a command navigates', async ({ page }) => {
    await page.goto('/#home');
    await page.locator('now-mobile-bar').getByRole('button', { name: 'Open command palette' }).tap();
    const search = page.locator('now-command-palette .search-input');
    await expect(search).toBeVisible();
    expect(await search.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
    await page.locator('now-command-palette').getByText('Workbench Settings').tap();
    await expect(search).toHaveCount(0);
    await expect(page).toHaveURL(/#admin$/);
  });

  test('a tap shows no tooltip', async ({ page }) => {
    await page.goto('/#artifacts');
    await page.locator('button[title="Clone Demonstration Bundle"]').first().tap();
    await expect(page.locator('.now-smart-tooltip')).toHaveCSS('opacity', '0');
  });
});

test.describe('phone landscape', () => {
  test.use({ viewport: { width: 844, height: 390 }, hasTouch: true, isMobile: true });

  test('a short screen also gets the drawer and fits', async ({ page }) => {
    await page.goto('/#home');
    await expect(page.locator('now-mobile-bar')).toBeVisible();
    await expect(page.locator('now-nav-rail')).toBeHidden();
    await expectNoSidewaysScroll(page);
  });
});

test.describe('tablet portrait (iPad size)', () => {
  test.use({ viewport: { width: 820, height: 1180 }, hasTouch: true });

  test('the rail stays and settings stack beside it', async ({ page }) => {
    await page.goto('/#admin');
    await expect(page.locator('now-nav-rail')).toBeVisible();
    await expect(page.locator('now-mobile-bar')).toHaveCount(0);
    const strip = await page.getByRole('navigation', { name: 'Settings sections' }).boundingBox();
    expect(strip?.height ?? 0).toBeLessThan(80);
    await expectNoSidewaysScroll(page);
  });
});

test.describe('tablet without a keyboard', () => {
  test.use({ viewport: { width: 820, height: 1180 }, hasTouch: true });

  test('the rail opens the command palette', async ({ page }) => {
    await page.goto('/#home');
    await page.locator('now-nav-rail').getByRole('button', { name: 'Command palette' }).tap();
    await expect(page.locator('now-command-palette .search-input')).toBeVisible();
  });
});

test('Cmd+K still opens and closes the command palette on a desktop', async ({ page }) => {
  await page.goto('/#home');
  await page.locator('now-nav-rail').waitFor();
  const search = page.locator('now-command-palette .search-input');
  await page.keyboard.press('ControlOrMeta+k');
  await expect(search).toBeVisible();
  await page.keyboard.press('ControlOrMeta+k');
  await expect(search).toHaveCount(0);
});

test('a desktop keeps the rail and has no phone bar', async ({ page }) => {
  await page.goto('/#home');
  await expect(page.locator('now-nav-rail')).toBeVisible();
  await expect(page.locator('now-mobile-bar')).toHaveCount(0);
});
