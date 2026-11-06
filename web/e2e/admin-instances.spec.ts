// web/e2e/admin-instances.spec.ts
// Admin panel renders the real instance registry and never exposes passwords (ADR-011, ADR-012).
// Author: Pierre Grothe
// Date: 2026-11-06
import { expect, openInstancesPanel, seedInstance, seedProfile, test } from './fixtures';

test('empty registry renders an empty state, never a sample instance', async ({ page }) => {
  await openInstancesPanel(page);

  await expect(page.getByText('Connected Sub-Production Instances (0)')).toBeVisible();
  await expect(page.getByTestId('instances-empty')).toContainText('No ServiceNow instances');
  // Regression: a hardcoded sample instance used to appear when the DB was empty.
  await expect(page.getByText('demoalectriallwfau164179')).toHaveCount(0);
});

test('registered instance is listed and its password never reaches the browser', async ({
  page,
  request,
}) => {
  const secret = 'E2e-S3cret-pw!';
  await seedInstance(request, {
    name: 'E2E Dev Instance',
    url: 'fake://e2e-dev.service-now.com',
    username: 'e2e.admin',
    password: secret,
    is_default: true,
  });

  const apiBodies: string[] = [];
  page.on('response', async (res) => {
    if (res.url().includes('/api/instances')) apiBodies.push(await res.text());
  });

  await openInstancesPanel(page);

  await expect(page.getByText('Connected Sub-Production Instances (1)')).toBeVisible();
  const row = page.getByRole('table').getByRole('row', { name: /E2E Dev Instance/ });
  await expect(row).toBeVisible();
  await expect(row).toContainText('e2e.admin');
  await expect(row).toContainText('authenticated');
  await expect(page.getByTestId('instances-empty')).toHaveCount(0);

  expect(apiBodies.length).toBeGreaterThan(0);
  for (const body of apiBodies) expect(body).not.toContain(secret);
  expect(await page.content()).not.toContain(secret);
});

test('connect form has no release picker; release is detected, not chosen', async ({ page }) => {
  await openInstancesPanel(page);

  // The release family is read from the instance build (glide.war), never asked for.
  await expect(page.getByText(/Release Family/)).toHaveCount(0);
  // The only selector is the owner-declared purpose; there is nothing for the release.
  await expect(page.locator('select')).toHaveCount(1);
  await expect(page.getByLabel('Purpose')).toBeVisible();

  await page.getByPlaceholder('e.g. Novartis BioHealth Sub-Prod').fill('Form Instance');
  await page.getByPlaceholder('https://instancename.service-now.com').fill('fake://form.service-now.com');
  await page.getByPlaceholder('Enter instance credentials').fill('form-pw');
  await page.getByTitle('Connect Instance').click();

  const row = page.getByRole('table').getByRole('row', { name: /Form Instance/ });
  await expect(row).toBeVisible();
  // Simulated (fake://) instances are never probed, so no release is invented.
  await expect(row).toContainText('Unknown');
});

test('unprofiled instance says details come from the first connection test', async ({
  page,
  request,
}) => {
  await seedInstance(request, { name: 'Fresh Instance', url: 'fake://fresh.service-now.com', is_default: true });
  await openInstancesPanel(page);

  await expect(page.getByText('Release not detected')).toBeVisible();
  await expect(page.getByTestId('profile-empty')).toContainText('first successful connection test');
  await expect(page.getByTestId('profile-facts')).toHaveCount(0);
});

test('detected platform profile is shown: environment, datacenter, nodes, CPU, memory', async ({
  page,
  request,
}) => {
  const inst = await seedInstance(request, {
    name: 'Profiled Instance',
    url: 'fake://profiled.service-now.com',
    is_default: true,
  });
  const node = (n: number, pressure: string) => ({
    node_id: `n${n}`,
    hostname: `app${n}.yyz3.service-now.com`,
    datacenter: 'yyz3',
    status: 'online',
    cpu_count: 64,
    memory_max_mb: 2000,
    memory_in_use_mb: 1000,
    memory_pressure: pressure,
  });
  seedProfile({
    instance_id: inst.id,
    release: 'Brazil',
    build_tag: 'glide-brazil-08-01-2027__patch0',
    build_date: '2027-08-15',
    installation_name: 'Lab Server',
    instance_type: 'prod',
    production_property: true,
    datacenter: 'yyz3',
    db_product: 'MySQL',
    db_version: '5.8',
    java_version: '21.0.11',
    nodes: [node(1, 'NOMINAL'), node(2, 'SUSTAINED_OVER')],
  });

  await openInstancesPanel(page);

  // A release name the code has never seen is displayed as reported by the instance.
  await expect(page.getByText('Brazil Family')).toBeVisible();
  const facts = page.getByTestId('profile-facts');
  // Platform-reported values are labelled as reported, not shown as a verdict.
  await expect(facts).toContainText('Instance type (reported)');
  await expect(facts).toContainText('prod, production property true');
  await expect(facts).toContainText('Lab Server');
  await expect(facts).toContainText('yyz3');
  await expect(facts).toContainText('2/2 online');
  await expect(facts).toContainText('2000 / 4000 MB (50%)');
  await expect(facts).toContainText('SUSTAINED_OVER');
  const row = page.getByRole('table').getByRole('row', { name: /Profiled Instance/ });
  await expect(row).toContainText('Brazil');
  // The badge is the owner's declared purpose (default demo), even though the
  // platform reports type "prod" for this instance.
  await expect(page.getByTestId('row-purpose')).toHaveText('Demo');
  await expect(page.getByTestId('hero-purpose')).toHaveText('Demo');
});

test('purpose is declared by the user; only "Production" is flagged red', async ({ page }) => {
  await openInstancesPanel(page);

  await page.getByPlaceholder('e.g. Novartis BioHealth Sub-Prod').fill('Purpose Instance');
  await page.getByPlaceholder('https://instancename.service-now.com').fill('fake://purpose.service-now.com');
  await page.getByLabel('Purpose').selectOption('production');
  await page.getByTitle('Connect Instance').click();

  const badge = page.getByTestId('row-purpose');
  await expect(badge).toHaveText('Production');
  await expect(badge).toHaveClass(/prod/);

  // Edit it back to a non-production purpose: the red flag goes away.
  await page.getByTitle('Edit Credentials').click();
  await page.locator('#edit-purpose').selectOption('demo');
  await page.getByTitle('Save Changes').click();
  await expect(page.getByTestId('row-purpose')).toHaveText('Demo');
  await expect(page.getByTestId('row-purpose')).not.toHaveClass(/prod/);
});
