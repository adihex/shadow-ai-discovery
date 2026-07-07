import { test, expect } from '@playwright/test';

// The backend seeds a deterministic demo catalog on first run:
// 8 assets total, 6 of which are classified as AI agents.
const TOTAL_ASSETS = 8;
const TOTAL_AGENTS = 6;

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.table-row-interactive').first()).toBeVisible();
});

test('dashboard loads inventory metrics and the assets table', async ({ page }) => {
  const metric = (label: string) =>
    page.locator('.metric-card', { hasText: label }).locator('.metric-value');

  await expect(metric('Total Assets Scanned')).toHaveText(String(TOTAL_ASSETS));
  await expect(metric('Likely AI Workloads')).toHaveText(String(TOTAL_AGENTS));

  await expect(page.locator('.table-row-interactive')).toHaveCount(TOTAL_ASSETS);
  await expect(
    page.getByRole('button', { name: `All Cloud Assets (${TOTAL_ASSETS})` })
  ).toHaveClass(/active/);
});

test('assets view filters by resource type', async ({ page }) => {
  await page.getByRole('combobox').selectOption('Cloud Run');

  const rows = page.locator('.table-row-interactive');
  await expect(rows).toHaveCount(4);
  for (const badge of await rows.locator('.badge-type').all()) {
    await expect(badge).toHaveText('Cloud Run');
  }
});

test('agents view lists classified workloads with risk grading', async ({ page }) => {
  await page.getByRole('button', { name: `Likely AI Agents (${TOTAL_AGENTS})` }).click();

  const rows = page.locator('.table-row-interactive');
  await expect(rows).toHaveCount(TOTAL_AGENTS);

  const highRisk = rows.filter({ hasText: 'my-ai-service' });
  await expect(highRisk.locator('.badge-danger')).toHaveText('Critical');

  // The Vertex boost regression: the platform's own Vertex AI endpoint
  // must be classified as an agent.
  await expect(rows.filter({ hasText: 'customer-churn-model' })).toHaveCount(1);
});

test('agent details show indicators, risk reasons, and masked credentials', async ({ page }) => {
  await page.locator('.table-row-interactive', { hasText: 'my-ai-service' }).click();

  const sidebar = page.locator('.details-sidebar');
  await expect(sidebar.locator('.details-title')).toHaveText('my-ai-service');

  // Confidence + risk breakdowns
  await expect(sidebar.locator('.indicator-pill', { hasText: 'OpenAI API Key configured' })).toBeVisible();
  await expect(sidebar.locator('.indicator-pill', { hasText: 'Integrates with third-party LLMs (+30)' })).toBeVisible();

  // IAM identity + relationship flow (Bonus 2)
  await expect(sidebar.getByText('default-compute@developer.gserviceaccount.com')).toBeVisible();
  await expect(sidebar.locator('.relationship-graph')).toContainText('LLM Endpoint / Vertex API');

  // Credential env values must be masked, never raw
  const apiKey = sidebar.locator('.meta-item', { hasText: 'OPENAI_API_KEY' }).locator('.meta-val');
  await expect(apiKey).toHaveText(/\*{10,}/);
});

test('non-agent workloads show no confidence breakdown', async ({ page }) => {
  await page.locator('.table-row-interactive', { hasText: 'legacy-web-app' }).click();

  const sidebar = page.locator('.details-sidebar');
  await expect(sidebar.locator('.details-title')).toHaveText('legacy-web-app');
  await expect(sidebar.getByText('AI Confidence Breakdown')).toHaveCount(0);
});

test('triggering a scan completes and re-enables the scan button', async ({ page }) => {
  // Regression: scans used to stay "running" forever, leaving the
  // dashboard spinner stuck.
  const scanButton = page.getByRole('button', { name: /Trigger Scan|Scanning Project/ });

  await scanButton.click();
  await expect(scanButton).toBeDisabled();
  await expect(scanButton).toContainText('Scanning Project...');

  // The frontend polls scan history every 2s; the mock scan itself is fast.
  await expect(scanButton).toBeEnabled({ timeout: 15_000 });
  await expect(scanButton).toContainText('Trigger Scan');

  await expect(page.locator('.table-row-interactive')).toHaveCount(TOTAL_ASSETS);
});
