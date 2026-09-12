// Offline projection of the actual C1 card payload, not a Feishu/phone receipt.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import { chromium } from "playwright-core";

const html = await fs.readFile(
  new URL("../c1-preview.html", import.meta.url),
  "utf8",
);
const preview = JSON.parse(
  await fs.readFile(new URL("../c1-preview.json", import.meta.url), "utf8"),
);
const card = JSON.parse(preview.content);
const artifacts = new URL("../.browser-artifacts/", import.meta.url);
await fs.mkdir(artifacts, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const requests = [];
const errors = [];
try {
  const context = await browser.newContext({
    offline: true,
    viewport: { width: 390, height: 844 },
  });
  await context.route("**/*", (route) => route.abort());
  const page = await context.newPage();
  page.on("request", (request) => requests.push(request.url()));
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setContent(html);
  assert.equal(await page.locator("h1").innerText(), card.header.title.content);
  assert.deepEqual(
    await page.locator("article p").allTextContents(),
    card.elements.map((e) => e.text.content),
  );
  assert.equal(
    await page.locator("a,button,input,form,iframe,script,img,link").count(),
    0,
  );
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: new URL(`c1-preview-${width}.png`, artifacts).pathname.replace(
        /^\/(\w:)/,
        "$1",
      ),
      fullPage: true,
    });
  }
  assert.deepEqual(requests, []);
  assert.deepEqual(errors, []);
  console.log(
    "C1 offline preview: card payload text exact; 390/320px fit; no actions, network requests or page errors.",
  );
} finally {
  await browser.close();
}
