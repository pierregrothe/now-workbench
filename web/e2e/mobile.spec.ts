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

/**
 * Nothing scrolls sideways inside one screen either. The page check misses it: each screen
 * scrolls inside its own host, under a content area that clips. So the host and every scroll
 * container in its shadow trees (overflow other than visible) must be no wider than its box.
 * Form controls and icons are not layout boxes and are skipped. `sideways` lists, by selector,
 * the frames meant to scroll sideways (a wide table, a code box, a strip); their own overflow
 * is allowed, their insides are still checked. The VIEWS loop keeps the page-level check only:
 * its other screens have not been audited for such frames.
 */
async function expectNoSidewaysScrollIn(page: Page, host: string, sideways: string[]): Promise<void> {
  await expectNoSidewaysScroll(page);
  const wide = await page.locator(host).evaluate((root, allowed) => {
    const found: string[] = [];
    const visit = (el: Element): void => {
      if (el.matches('input, select, textarea, button, svg')) return;
      const overflow = getComputedStyle(el).overflowX;
      const scrolls = overflow !== 'visible' && overflow !== 'clip';
      const meant = allowed.some((sel) => el.matches(sel));
      if (scrolls && !meant && el.scrollWidth > el.clientWidth + 1) {
        found.push(`${el.tagName.toLowerCase()}.${el.getAttribute('class') ?? ''} ${el.scrollWidth}>${el.clientWidth}`);
      }
      for (const child of el.shadowRoot?.children ?? []) visit(child);
      for (const child of el.children) visit(child);
    };
    visit(root);
    return found;
  }, sideways);
  expect(wide).toEqual([]);
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

  test('the Team usage list fits the width of the phone', async ({ page }) => {
    await page.goto('/#admin/team');
    await expect(page.locator('now-usage-allowances').getByRole('heading', { name: 'Claude usage this month' })).toBeVisible();
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

  test('synthesizer and capture buttons and fields are touch-sized, fields 16px', async ({ page }) => {
    const height = async (name: string) =>
      (await page.getByRole('button', { name, exact: true }).boundingBox())?.height ?? 0;
    /** Every form field of the screen: [font size, height] in px. */
    const fields = (form: string) =>
      page
        .locator(form)
        .locator('input, select, textarea')
        .evaluateAll((els) => els.map((el) => [parseFloat(getComputedStyle(el).fontSize), el.getBoundingClientRect().height]));
    const expectTouchFields = (found: number[][], count: number) => {
      expect(found).toHaveLength(count);
      for (const [size, tall] of found) {
        expect(size).toBeGreaterThanOrEqual(16);
        expect(tall).toBeGreaterThanOrEqual(40);
      }
    };

    await page.goto('/#synthesizer');
    expect(await height('Synthesize Demo Bundle')).toBeGreaterThanOrEqual(40);
    expectTouchFields(await fields('now-synthesizer-view .synth-grid'), 4);
    await page.goto('/#capture');
    expect(await height('Video Walkthrough')).toBeGreaterThanOrEqual(40);
    expect(await height('Capture Screenshot')).toBeGreaterThanOrEqual(40);
    expectTouchFields(await fields('now-capture-studio .studio-grid'), 3);
  });

  test('fluent explorer and artifact library buttons are touch-sized and fit the phone', async ({ page }) => {
    /** Every button of the screen: [width, height] in px. */
    const buttons = (screen: string) =>
      page
        .locator(screen)
        .locator('button')
        .evaluateAll((els) => els.map((el) => [el.getBoundingClientRect().width, el.getBoundingClientRect().height]));
    const expectTouchSized = (found: number[][]) => {
      expect(found.length).toBeGreaterThan(0);
      for (const [wide, tall] of found) {
        expect(wide).toBeGreaterThanOrEqual(40);
        expect(tall).toBeGreaterThanOrEqual(40);
      }
    };

    await page.goto('/#fluent');
    await expect(page.locator('now-fluent-explorer .columns-table')).toBeVisible();
    const picker = page.locator('now-fluent-explorer select');
    await expect(picker).toBeVisible();
    expect(await picker.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
    expect((await picker.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(40);
    expectTouchSized(await buttons('now-fluent-explorer'));
    await expectNoSidewaysScrollIn(page, 'now-fluent-explorer', ['.tables-sidebar', '.table-card', '.code-box']);

    await page.goto('/#artifacts');
    await expect(page.locator('now-demo-catalog .demo-card').first()).toBeVisible();
    expectTouchSized(await buttons('now-demo-catalog'));
    await expectNoSidewaysScrollIn(page, 'now-demo-catalog', []);
  });

  test('a capture gallery with a long-labelled card fits the width of the phone', async ({ page }) => {
    const card = {
      id: 'c1',
      bundle_id: 'sample-ai-assistant',
      instance_url: 'fake://dev',
      target_path: '/now/nav/ui/classic/params/target/incident_list.do',
      media_type: 'screenshot',
      label: 'A very long capture caption that must ellipsize instead of widening the card'.repeat(2),
      filename: 'c1.png',
      file_path: 'c1.png',
      url: 'data:image/gif;base64,R0lGODlhAQABAAAAACw=',
      engine: 'playwright',
      created_at: '2026-11-07T00:00:00Z',
    };
    await page.route('**/api/demos/*/captures', async (route) => {
      if (route.request().method() !== 'GET') return route.fallback();
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([card]) });
    });
    await page.goto('/#capture');
    await expect(page.getByRole('heading', { name: 'Captured Proofs (1)' })).toBeVisible();
    expect(await page.getByRole('button', { name: 'Rename', exact: true }).boundingBox()).not.toBeNull();
    await expectNoSidewaysScroll(page);
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
