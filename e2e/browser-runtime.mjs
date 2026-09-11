// Real E gateway/API/PostgreSQL. New isolated Chrome contexts, synthetic sessions only.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire(new URL('../web/package.json', import.meta.url));
const { chromium } = require('playwright-core');
const base = 'http://127.0.0.1:18084';
const sessionFile = process.env.OIL_E_SESSION_FILE;
assert(sessionFile, 'Inject the newly created synthetic E session file');
const seed = JSON.parse(await fs.readFile(sessionFile, 'utf8'));
assert(seed.is_fixture && seed.dataset === 'synthetic-e-runtime');
const results = [];
const errors = [];
const artifacts = new URL('./runtime-artifacts/', import.meta.url);
await fs.mkdir(artifacts, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true });
async function contextFor(name) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  if (name) await context.addCookies([{ name: 'oil_session', value: seed.sessions[name], url: base, httpOnly: true, sameSite: 'Lax' }]);
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  // This is a network boundary, not an API response mock: all E requests continue unchanged.
  await context.route('**/*', route => {
    if (new URL(route.request().url()).origin === base) return route.continue();
    errors.push('Unexpected external request blocked');
    return route.abort();
  });
  return { context, page };
}
async function record(name, operation) {
  await operation();
  results.push({ name, status: 'PASS', evidence: 'actual local gateway + API + PostgreSQL; synthetic data' });
}
try {
  const anonymous = await contextFor();
  await record('T23 anonymous event link requires session', async () => {
    await anonymous.page.goto(`${base}/#/events/${seed.event_id}`);
    await anonymous.page.getByRole('button', { name: '使用飞书登录' }).waitFor();
    assert.equal((await anonymous.context.request.get(`${base}/api/v1/events/${seed.event_id}`)).status(), 401);
  });
  await anonymous.context.close();
  const viewer = await contextFor('viewer');
  await record('T24 T27 live fixture home and responsive layout', async () => {
    await viewer.page.goto(base);
    await viewer.page.getByRole('heading', { name: '今日关注' }).waitFor();
    await viewer.page.locator(`a[href="#/events/${seed.event_id}"]`).waitFor();
    assert((await viewer.page.locator('body').innerText()).includes('演练'));
    assert(await viewer.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await viewer.page.screenshot({ path: new URL('home-390.png', artifacts).pathname.replace(/^\/(\w:)/, '$1'), fullPage: true });
  });
  await record('T17 T23 persisted browser acknowledgment and feedback', async () => {
    await viewer.page.goto(`${base}/#/events/${seed.event_id}`);
    const acknowledge = viewer.page.getByRole('button', { name: '确认 v1', exact: true });
    await viewer.page.getByRole('heading', { name: '确认与反馈' }).waitFor();
    if (await acknowledge.isVisible()) {
      const response = viewer.page.waitForResponse(r => r.url().endsWith('/ack') && r.request().method() === 'POST');
      await acknowledge.click();
      assert.equal((await response).status(), 200);
    }
    await viewer.page.getByRole('button', { name: '本版本已确认', exact: true }).waitFor();
    await viewer.page.getByLabel('补充说明').fill('Synthetic E local browser feedback only');
    const feedback = viewer.page.waitForResponse(r => r.url().endsWith('/feedback') && r.request().method() === 'POST');
    await viewer.page.getByRole('button', { name: '提交反馈' }).click();
    assert.equal((await feedback).status(), 200);
    await viewer.page.screenshot({ path: new URL('event-390.png', artifacts).pathname.replace(/^\/(\w:)/, '$1'), fullPage: true });
  });
  await record('T19 T24 persisted report is visible', async () => {
    assert(seed.report_id);
    await viewer.page.goto(`${base}/#/reports/${seed.report_id}`);
    await viewer.page.getByRole('heading', { name: /简报 · v1/ }).waitFor();
    assert((await viewer.page.locator('body').innerText()).includes('数据截止'));
  });
  await record('T23 viewer cannot configure or import quotes', async () => {
    await viewer.page.goto(`${base}/#/quotes`);
    await viewer.page.getByRole('heading', { name: '需要管理员权限' }).waitFor();
    assert.equal((await viewer.context.request.get(`${base}/api/v1/config`)).status(), 403);
  });
  const outsider = await contextFor('outsider');
  await record('T23 forwarded link denied to ungranted user', async () => {
    await outsider.page.goto(`${base}/#/events/${seed.event_id}`);
    const response = await outsider.context.request.get(`${base}/api/v1/events/${seed.event_id}`);
    assert.equal(response.status(), 403);
    assert(!(await outsider.page.locator('body').innerText()).includes('Synthetic publisher confirms'));
  });
  await outsider.context.close();
  const admin = await contextFor('admin');
  await record('T11 T24 actual safe quote preview and import', async () => {
    await admin.page.goto(`${base}/#/quotes`);
    const row = 'product,spec,region,supplier,quote_type,tax_basis,delivery_basis,currency,unit,value,as_of,published_at\nsynthetic diesel,E-grade,E-region,E-supplier,offer,included,pickup,CNY,tonne,1234.50,2026-09-11T00:00:00Z,2026-09-11T00:00:00Z\n';
    await admin.page.locator('input[type=file]').setInputFiles({ name: 'e-browser.csv', mimeType: 'text/csv', buffer: Buffer.from(row) });
    await admin.page.getByLabel('数据使用授权或来源依据').fill('fixture:original-synthetic-E-browser');
    await admin.page.getByRole('button', { name: '校验并预览' }).click();
    await admin.page.getByRole('button', { name: '确认导入此预览' }).waitFor();
    assert((await admin.page.locator('body').innerText()).includes('1234.50'));
    const response = admin.page.waitForResponse(r => r.url().endsWith('/quotes/import'));
    await admin.page.getByRole('button', { name: '确认导入此预览' }).click();
    assert.equal((await response).status(), 200);
    await admin.page.getByRole('button', { name: '已导入', exact: true }).waitFor();
    await admin.page.screenshot({ path: new URL('quotes-390.png', artifacts).pathname.replace(/^\/(\w:)/, '$1'), fullPage: true });
  });
  await record('T23 browser logout revokes persisted session', async () => {
    await viewer.page.getByRole('button', { name: '退出', exact: true }).click();
    await viewer.page.getByRole('button', { name: '使用飞书登录' }).waitFor();
    assert.equal((await viewer.context.request.get(`${base}/api/v1/session`)).status(), 401);
  });
  await viewer.context.close();
  await admin.context.close();
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
  await fs.writeFile(new URL('browser-results.json', artifacts), JSON.stringify({ is_fixture: true, results, errors, externalPhoneAndIdentity: 'NOT EXECUTED' }, null, 2));
}
console.log(`${results.length} actual local browser checks passed; real Feishu/phone NOT EXECUTED`);
