/* Viewport and navigation checks for the isolated Krug collaboration preview.
   Uses the shared external Playwright install; it creates no user or DB fixtures. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { chromium } = require('playwright');

const base = process.env.APP_URL;
if (!base || !/^http:\/\/127\.0\.0\.1:18103(?:\/|$)/.test(base)) {
  throw new Error('Set APP_URL to the isolated preview http://127.0.0.1:18103');
}
const output = process.env.BROWSER_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), 'krug-discovery-'));
fs.mkdirSync(output, { recursive: true });
const sizes = [[320, 800], [360, 800], [390, 844], [430, 900], [768, 1024], [1024, 900], [1280, 900], [1440, 1000], [1920, 1080], [2560, 1440], [3440, 1440], [3840, 2160]];
const errors = [];

async function saveScreenshot(page, file) {
  await page.evaluate(() => { window.scrollTo({ top: 0, behavior: "instant" }); if (document.activeElement instanceof HTMLElement) document.activeElement.blur(); });
  await page.locator("#toast.visible").waitFor({ state: "hidden", timeout: 5500 }).catch(() => {});
  await page.waitForTimeout(220);
  await page.screenshot({ path: path.join(output, file), fullPage: true });
}

async function main() {
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'ru-RU', colorScheme: 'dark' });
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(base + '/app#explore', { waitUntil: 'networkidle' });
    await page.locator('.discovery-intro h1').waitFor();
    await page.locator('.discovery-tabs').waitFor();
    for (const [width, height] of sizes) {
      await page.setViewportSize({ width, height });
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Horizontal overflow at ${width}px`);
      if (width <= 850) assert.equal(await page.locator('.nav a').count(), 4, 'Four mobile destinations remain available');
      if (width === 390) await saveScreenshot(page, 'discovery-390.png');
      if (width === 1440) await saveScreenshot(page, 'discovery-1440.png');
      if (width === 2560) await saveScreenshot(page, 'discovery-2560.png');
      if (width === 3440) await saveScreenshot(page, 'discovery-3440.png');
      if (width === 3840) await saveScreenshot(page, 'discovery-3840.png');
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('.discovery-tabs a[href*="kind=projects"]').click();
    await page.waitForFunction(() => location.hash.includes('kind=projects'));
    await page.locator('.discovery-filters:not([hidden]) summary').waitFor();
    assert.equal(await page.locator('.discovery-filters').evaluate(node => node.open), false, 'Project filters start collapsed on mobile');
    await page.locator('.discovery-filters:not([hidden]) summary').click();
    await page.locator('.discovery-filters select[name=status]').waitFor({ state: 'visible' });
    await page.locator('.discovery-tabs a[href*="kind=people"]').click();
    await page.waitForFunction(() => location.hash.includes('kind=people'));
    assert.equal(await page.locator(".nav [aria-current=page]").count(), 1, "Only the selected people destination is current");
    await page.locator('.discovery-filters:not([hidden]) summary').click();
    await page.locator('.discovery-filters select[name=intent_kind]').waitFor({ state: 'visible' });
    await page.locator('#ui-language').click();
    await page.locator('.discovery-intro h1').waitFor();
    await page.locator('#ui-language').click();
    await page.goto(base + "/app#explore");
    await page.locator(".project-card").first().waitFor();
    await page.waitForFunction(() => { const main = document.querySelector("main"); return main && !main.inert && !main.hasAttribute("aria-busy"); });
    await page.locator(".discovery-search input[name=search]").focus();
    assert.equal(await page.evaluate(() => document.activeElement === document.querySelector(".discovery-search input[name=search]")), true, "Search receives keyboard focus");
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.activeElement === document.querySelector(".discovery-search-main button")), true, "Keyboard tab reaches search action");
    await page.locator("#ui-theme").click();
    await page.locator("[data-theme-choice=light]").click();
    assert.equal(await page.locator("html").getAttribute("data-theme"), "light", "Light theme applies");
    await page.locator("#ui-theme").click();
    await page.locator("[data-theme-choice=dark]").click();
    await page.emulateMedia({ reducedMotion: "reduce" });
    assert.equal(await page.locator(".project-card").first().evaluate(node => getComputedStyle(node).animationDuration), "0s", "Reduced motion disables card animation");
    await page.unroute("**/people?*" ).catch(() => {});
    await page.route("**/people?*", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Synthetic preview error" }) }));
    await page.goto(base + "/app#explore?kind=people&search=error-check");
    await page.getByRole("alert").waitFor();
    await page.unroute("**/people?*");
    assert.deepEqual(errors, [], `Browser errors: ${errors.join('; ')}`);
    console.log(`Viewport and discovery checks passed. Screenshots: ${output}`);
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
