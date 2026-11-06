// web/playwright.config.ts
// End-to-end UI tests against the real FastAPI backend and built Lux UI (ADR-013).
// Author: Pierre Grothe
// Date: 2026-11-06
import { defineConfig } from '@playwright/test';

const PORT = 8091;
const BASE_URL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: './e2e',
  // One backend + one SQLite file: run tests serially so they never race on shared state.
  fullyParallel: false,
  workers: 1,
  forbidOnly: true,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  outputDir: 'test-results',
  use: {
    baseURL: BASE_URL,
    // Use the locally installed Google Chrome: no browser download needed.
    channel: 'chrome',
    viewport: { width: 1440, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    // Fresh, isolated data dir and master key per run, then build the UI and serve it.
    command:
      'rm -rf .e2e && npm run build --prefix web && ' +
      `uv run workbench serve --host 127.0.0.1 --port ${PORT}`,
    cwd: '..',
    url: `${BASE_URL}/api/settings`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      WORKBENCH_DATA_DIR: '.e2e/data',
      WORKBENCH_KEY_FILE: '.e2e/keys/master.key',
      WORKBENCH_SN_INSTANCE_URL: '',
      WORKBENCH_ANTHROPIC_API_KEY: '',
    },
  },
});
