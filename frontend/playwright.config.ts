import { defineConfig, devices } from '@playwright/test';
import os from 'node:os';
import path from 'node:path';

// The backend launched for E2E runs writes to a throwaway database so test
// scans never touch the local dev database.db.
import fs from 'node:fs';

const E2E_DB = path.join(os.tmpdir(), 'shadow-ai-e2e.db');

// Ensure a fresh database for every E2E test run to avoid stale scan records.
// Only delete from the parent runner process, not from worker processes.
if (process.env.TEST_WORKER_INDEX === undefined) {
  try {
    fs.rmSync(E2E_DB, { force: true });
  } catch (e) {
    // Ignore
  }
}

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false, // journeys share one backend; keep them ordered
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5175',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      command: './.venv/bin/python -m uvicorn app.main:app --port 8000',
      cwd: path.join(import.meta.dirname, '..', 'backend'),
      url: 'http://localhost:8000/',
      reuseExistingServer: false,
      env: { SHADOW_AI_DATABASE_PATH: E2E_DB },
      timeout: 30_000,
    },
    {
      command: 'npm run dev -- --strictPort --port 5175',
      url: 'http://localhost:5175/',
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
});
