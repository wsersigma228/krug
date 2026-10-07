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
    await page.locator('.discovery-search input[name=search]').fill('game dev');
    await page.locator('.discovery-search-main button').click();
    await page.waitForFunction(() => new URLSearchParams(location.hash.split('?')[1]).get('search') === 'game dev');
    for (const [width, height] of sizes) {
      await page.setViewportSize({ width, height });
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Horizontal overflow at ${width}px`);
      if (width <= 850) assert.equal(await page.locator('.nav a').count(), 4, 'Four mobile destinations remain available');
      if (width === 390) assert.equal(await page.locator('.discovery-filters').evaluate(node => node.open), false, 'Desktop-open filters collapse at mobile width when only search is set');
      if (width === 1440) {
        const search = await page.locator('.discovery-search').boundingBox();
        const tabs = await page.locator('.discovery-tabs').boundingBox();
        const rail = await page.locator('.discovery-sidebar').boundingBox();
        const results = await page.locator('.discovery-results').boundingBox();
        assert(search.y + search.height < tabs.y, 'Search sits above result tabs');
        assert(rail.x + rail.width < results.x, 'Desktop filters occupy the left rail');
        assert.equal(await page.locator('#discovery-results > .discovery-group').count(), 0, 'All results avoid sparse type-by-type blank sections');
        if (await page.locator('#discovery-results .project-card').count()) assert.equal(await page.locator('#discovery-results > .project-grid').count(), 1, 'All real result types share one grid');
      }
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
    await page.locator('.discovery-filter-form input[name=skill]').fill('Programming');
    await page.locator('.discovery-filter-form select[name=status]').selectOption('active');
    await page.locator('.discovery-filter-form button[type=submit]').click();
    await page.waitForFunction(() => {
      const query = new URLSearchParams(location.hash.split('?')[1]);
      return query.get('kind') === 'projects' && query.get('search') === 'game dev' && query.get('skill') === 'Programming' && query.get('status') === 'active';
    });
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
    const firstCardTop = await page.locator(".project-card").first().evaluate(node => node.getBoundingClientRect().top);
    const viewportHeight = await page.evaluate(() => innerHeight);
    assert(firstCardTop < viewportHeight - 96, "A real project card appears above the mobile bottom navigation in the first viewport");
    await page.locator(".discovery-search input[name=search]").focus();
    assert.equal(await page.evaluate(() => document.activeElement === document.querySelector(".discovery-search input[name=search]")), true, "Search receives keyboard focus");
    await page.keyboard.press("Tab");
    assert.equal(await page.evaluate(() => document.activeElement === document.querySelector(".discovery-search-main button")), true, "Keyboard tab reaches search action");
    await page.evaluate(() => window.scrollTo(0, Math.min(240, document.documentElement.scrollHeight - innerHeight)));
    const beforeThemeScroll = await page.evaluate(() => scrollY);
    await page.locator("#ui-theme").click();
    await page.locator("[data-theme-choice=light]").click();
    await page.waitForFunction(() => document.documentElement.dataset.theme === "light");
    assert.equal(await page.evaluate(() => document.activeElement?.id), "ui-theme", "Theme change returns keyboard focus to its control");
    assert.equal(await page.evaluate(() => scrollY), beforeThemeScroll, "Theme change preserves scroll position");
    const rapidTransition = await page.evaluate(() => {
      const native = document.startViewTransition;
      if (!native) return { supported: false, skips: 0 };
      const probe = { supported: true, skips: 0 };
      Object.defineProperty(document, "startViewTransition", { configurable: true, value(update) {
        const transition = native.call(document, update);
        const skip = transition.skipTransition.bind(transition);
        transition.skipTransition = () => { probe.skips++; return skip(); };
        return transition;
      } });
      window.__rapidThemeProbe = probe;
      document.querySelector("#ui-theme").click();
      document.querySelector("[data-theme-choice=dark]").click();
      document.querySelector("#ui-theme").click();
      document.querySelector("[data-theme-choice=light]").click();
      Object.defineProperty(document, "startViewTransition", { configurable: true, value: native });
      return probe;
    });
    if (rapidTransition.supported) assert(rapidTransition.skips > 0, "A rapid theme change interrupts the in-flight transition");
    await page.waitForFunction(() => document.documentElement.dataset.theme === "light");
    await page.locator("#ui-theme").click();
    await page.locator("[data-theme-choice=dark]").click();
    await page.waitForFunction(() => document.documentElement.dataset.theme === "dark");
    await page.emulateMedia({ reducedMotion: "reduce" });
    assert.equal(await page.locator(".project-card").first().evaluate(node => getComputedStyle(node).animationDuration), "0s", "Reduced motion disables card animation");
    await page.locator("#ui-theme").click();
    await page.locator("[data-theme-choice=light]").click();
    assert.equal(await page.locator("html").getAttribute("data-theme"), "light", "Reduced motion applies theme changes immediately");
    await page.route("**/people?*", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Synthetic preview error" }) }));
    const failedPeopleRequest = page.waitForResponse(response => response.url().includes("/people?") && response.status() === 503);
    await page.reload({ waitUntil: "networkidle" });
    assert.equal((await failedPeopleRequest).status(), 503, "The people source failure was requested and intercepted");
    await page.locator(".project-card").first().waitFor();
    await page.locator("#discovery-results .error[role=alert]").first().waitFor();
    assert(await page.locator("#discovery-results .project-card").count(), "Other source cards remain visible when one source fails");
    await page.goto(base + "/app#explore?kind=people&search=error-check");
    await page.getByRole("alert").waitFor();
    await page.unroute("**/people?*");
    await page.addInitScript(() => Object.defineProperty(document, "startViewTransition", { configurable: true, value: undefined }));
    await page.goto(base + "/app#explore");
    await page.locator(".project-card").first().waitFor();
    await page.locator("#ui-theme").click();
    await page.locator("[data-theme-choice=dark]").click();
    assert.equal(await page.locator("html").getAttribute("data-theme"), "dark", "Browsers without View Transitions apply the theme immediately");
    assert.deepEqual(errors, [], `Browser errors: ${errors.join('; ')}`);
    console.log(`Viewport and discovery checks passed. Screenshots: ${output}`);
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
