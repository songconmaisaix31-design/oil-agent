// Synthetic API interception only. Existing browser profiles and real Feishu are never used.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright-core";
import { actor, event, detail, status } from "../src/test/fixtures.ts";

const base = "http://127.0.0.1:5174";
const artifacts = new URL("../.browser-artifacts/", import.meta.url);
await fs.mkdir(artifacts, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const checks = [];
const errors = [];
try {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  let loggedIn = false;
  let admin = false;
  let ackAttempts = 0;
  await context.route(`${base}/api/**`, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    let code = 200;
    let data;
    if (path.endsWith("/session/challenge")) {
      code = 501;
      data = { code: "not_implemented" };
    } else if (path.endsWith("/session")) {
      code = loggedIn ? 200 : 401;
      data = loggedIn
        ? {
            actor: { ...actor, role: admin ? "admin" : "viewer" },
            csrf_token: "synthetic-csrf",
          }
        : { code: "unauthorized" };
    } else if (!loggedIn) {
      code = 401;
      data = { code: "unauthorized" };
    } else if (path.endsWith("/status")) data = status;
    else if (path.endsWith("/events"))
      data = {
        items: [event],
        next_cursor: null,
        data_cutoff_at: event.assessed_at,
      };
    else if (path.endsWith("/fixture-event")) data = detail;
    else if (path.endsWith("/ack")) {
      ackAttempts++;
      code = 409;
      data = { code: "revision_mismatch" };
    } else if (path.endsWith("/reports"))
      data = { items: [], next_cursor: null };
    else if (path.endsWith("/config"))
      data = {
        regions: [],
        products: [],
        suppliers: [],
        watched_events: [],
        recipient_ids: [],
        first_report_policy: null,
        report_time: "06:00:00",
        report_timezone: "Asia/Shanghai",
        reminders_enabled: false,
        sms_enabled: false,
        phone_enabled: false,
        outbound_mode: "dry_run",
        notification_channel: "dry_run",
      };
    else {
      code = 501;
      data = { code: "not_implemented" };
    }
    await route.fulfill({
      status: code,
      contentType: "application/json",
      body: JSON.stringify(data),
    });
  });
  await page.goto(base);
  await page.getByRole("button", { name: "使用飞书登录" }).click();
  await page.getByText("此功能尚未配置，暂时不可用。").waitFor();
  checks.push("unconfigured login shows explicit failure");
  loggedIn = true;
  await page.reload();
  await page.getByRole("heading", { name: "今日关注" }).waitFor();
  await page.getByText("演练数据 · web-unit").waitFor();
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await page.screenshot({
    path: new URL("home-390.png", artifacts).pathname.replace(/^\/(\w:)/, "$1"),
    fullPage: true,
  });
  checks.push("390px home fits viewport and shows fixture/dry-run labels");
  await page.getByRole("link", { name: /Synthetic test event/ }).click();
  await page.getByRole("button", { name: "确认 v2" }).click();
  await page.getByRole("alert").filter({ hasText: "数据版本已变化" }).waitFor();
  assert.equal(ackAttempts, 1);
  assert.equal(await page.getByText(/已记录 v2 确认/).count(), 0);
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  await page.screenshot({
    path: new URL("event-390.png", artifacts).pathname.replace(
      /^\/(\w:)/,
      "$1",
    ),
    fullPage: true,
  });
  checks.push(
    "390px event detail failure remains visible without false acknowledgement",
  );
  await page.getByRole("link", { name: "日报", exact: true }).click();
  await page.getByText("暂无可见日报").waitFor();
  await page.getByRole("link", { name: "报价", exact: true }).click();
  await page.getByText("需要管理员权限").waitFor();
  checks.push("report empty state and viewer quote restriction");
  await page.getByRole("link", { name: "设置", exact: true }).click();
  await page.getByText("当前为查看者，业务配置仅管理员可修改。").waitFor();
  admin = true;
  await page.reload();
  await page.getByRole("button", { name: "保存配置" }).waitFor();
  await page.setViewportSize({ width: 320, height: 740 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  checks.push("320px admin configuration fits viewport");
  assert.equal(
    await page.evaluate(() => localStorage.length + sessionStorage.length),
    0,
  );
  assert.deepEqual(errors, []);
  checks.push("no page exceptions and no local/session storage");
  console.log(
    JSON.stringify(
      { mode: "SYNTHETIC MOCK HTTP ONLY", checks, errors },
      null,
      2,
    ),
  );
  await fs.writeFile(
    new URL("result.json", artifacts),
    JSON.stringify(
      { mode: "SYNTHETIC MOCK HTTP ONLY", checks, errors },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
