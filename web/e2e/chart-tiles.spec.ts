// web/e2e/chart-tiles.spec.ts
// Chart tiles (ADR-027): every form draws, hover reads values, and the data is one click away.
// Author: Pierre Grothe
// Date: 2026-11-07
import { expect, selectThread, test } from './fixtures';

const days = ['Nov 01', 'Nov 02', 'Nov 03', 'Nov 04', 'Nov 05'];

const charts = [
  { id: 'area', type: 'chart', title: 'Questions per day', props: { chart: 'area', labels: days, series: [{ name: 'Questions', values: [2, 5, 3, 0, 7] }] } },
  {
    id: 'bar',
    type: 'chart',
    title: 'Seed runs per day',
    props: { chart: 'bar', stacked: true, unit: 'runs', labels: days, series: [{ name: 'Completed', values: [1, 2, 0, 3, 1] }, { name: 'Failed', values: [0, 1, 0, 0, 2] }] },
  },
  { id: 'donut', type: 'chart', title: 'Tokens by conversation', span: 1, props: { chart: 'donut', unit: 'tokens', labels: ['Seeding', 'Capture'], series: [{ name: 'Tokens', values: [3000, 1000] }] } },
  { id: 'meter', type: 'chart', title: 'Token budget', span: 1, props: { chart: 'meter', unit: 'tokens', value: 1800, max: 2000, labels: [], series: [] } },
  { id: 'kpi', type: 'kpis', title: 'This week', span: 1, props: { items: [{ label: 'Runs', value: '9', trend: [1, 3, 2, 5, 9] }] } },
];

test.beforeEach(async ({ page }) => {
  await page.route('**/api/threads/default-thread/messages', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'm-charts',
          thread_id: 'default-thread',
          role: 'assistant',
          content: 'Here is your activity.',
          widget_type: 'generative_tiles',
          widget_data: { tiles: charts, layout: '2-col' },
          created_at: '2026-11-07T12:00:00Z',
        },
      ]),
    }),
  );
  await page.goto('/');
  await selectThread(page);
});

test('every chart form draws with a readable description', async ({ page }) => {
  await expect(page.getByRole('img', { name: /area chart of Questions over 5 points/ })).toBeVisible();
  await expect(page.getByRole('img', { name: /bar chart of Completed, Failed/ })).toBeVisible();
  await expect(page.getByRole('img', { name: /donut chart of Tokens/ })).toBeVisible();
  await expect(page.getByRole('meter', { name: '1,800 tokens of 2,000 tokens' })).toBeVisible();
  await expect(page.getByText('Almost at limit, 90%')).toBeVisible();
  await expect(page.getByRole('img', { name: 'Trend, latest 9' })).toBeVisible();
  // The stacked bar has a legend (two series); the donut lists each slice with its share.
  await expect(page.getByText('75%')).toBeVisible();
});

test('lines are smooth curves that never pass below zero', async ({ page }) => {
  const line = page.locator('now-chart-tile').filter({ hasText: 'Questions per day' }).locator('path.line');
  await expect(line).toHaveAttribute('d', /C/);
  // Monotone tangents: the lowest point of the curve is the data's own zero (Nov 04), not below it.
  const { curveBottom, zeroY } = await line.evaluate((el: SVGPathElement) => {
    const svg = el.ownerSVGElement!;
    const base = svg.querySelector('line.baseline')!;
    let bottom = 0;
    for (let i = 0; i <= 400; i++) bottom = Math.max(bottom, el.getPointAtLength((el.getTotalLength() * i) / 400).y);
    return { curveBottom: bottom, zeroY: Number(base.getAttribute('y1')) };
  });
  expect(curveBottom).toBeLessThanOrEqual(zeroY + 0.5);
});

test('hovering a chart reads every series at that point', async ({ page }) => {
  const bars = page.getByRole('img', { name: /bar chart/ });
  const box = (await bars.boundingBox())!;
  // The last of five bands holds Nov 05: 1 completed, 2 failed.
  await page.mouse.move(box.x + box.width - 30, box.y + box.height / 2);
  const tip = page.locator('now-chart-tile .tooltip');
  await expect(tip).toContainText('Nov 05');
  await expect(tip).toContainText('2 runs');
  await expect(tip).toContainText('Failed');
});

test('the data behind a chart is one click away', async ({ page }) => {
  const tile = page.locator('now-chart-tile').filter({ hasText: 'Questions per day' });
  await tile.getByRole('button', { name: 'Show data' }).click();
  await expect(tile.getByRole('cell', { name: '7' })).toBeVisible();
  await tile.getByRole('button', { name: 'Show chart' }).click();
  await expect(tile.getByRole('img')).toBeVisible();
});
