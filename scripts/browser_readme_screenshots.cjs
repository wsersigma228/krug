/* Captures README screenshots (docs/images/*.webp) from the isolated preview seeded by
   scripts/seed_readme_preview.py. Uses the shared external Playwright install; read-only. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const base = process.env.APP_URL;
if (!base || !/^http:\/\/127\.0\.0\.1:18103(?:\/|$)/.test(base)) {
  throw new Error('Set APP_URL to the isolated preview http://127.0.0.1:18103');
}
const output = process.env.BROWSER_OUTPUT || path.join(__dirname, '..', 'docs', 'images');
const password = process.env.PREVIEW_PASSWORD;
if (!password) throw new Error('Set PREVIEW_PASSWORD to the seeded preview password');

const desktop = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 };
const mobile = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 1.5, isMobile: true, hasTouch: true };
const shots = [
  ['discovery-desktop-light', desktop, 'light', 'explore', '.hm-band h1'],
  ['discovery-desktop-dark', desktop, 'dark', 'explore', '.hm-band h1'],
  // Detail pages use a visitor account so owner-only controls stay out of the shot.
  ['project-desktop-light', desktop, 'light', 'project/transit-pulse', '.dt-box', 'kenji_t'],
  ['stories-desktop-dark', desktop, 'dark', 'stories', '.post-card'],
  ['event-desktop-dark', desktop, 'dark', 'event/spring-game-jam', '.dt-box', 'kenji_t'],
  ['community-desktop-light', desktop, 'light', 'community/open-source-starters', '.dt-box', 'kenji_t'],
  ['mobile-light', mobile, 'light', 'explore', '.hm-band h1'],
  ['mobile-dark', mobile, 'dark', 'explore', '.hm-band h1'],
  ['mobile-stories-light', mobile, 'light', 'stories', '.post-card'],
  ['mobile-stories-dark', mobile, 'dark', 'stories', '.post-card'],
];

async function main() {
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}), ...(process.env.BROWSER_EXECUTABLE ? { executablePath: process.env.BROWSER_EXECUTABLE } : {}) });
  const errors = [];
  // The app's CSP blocks data: images, so encode on a blank page outside the app origin.
  const encoder = await browser.newPage();
  try {
    for (const [name, device, theme, route, ready, username = 'sofia_l'] of shots) {
      const context = await browser.newContext({ ...device, locale: 'en-US', colorScheme: theme, reducedMotion: 'reduce' });
      await context.addInitScript(([language, selected]) => {
        localStorage.setItem('krug-language', language);
        localStorage.setItem('krug-theme', selected);
      }, ['en', theme]);
      const page = await context.newPage();
      page.on('pageerror', error => errors.push(`${name}: ${error.message}`));
      await page.goto(base + '/app', { waitUntil: 'networkidle' });
      await page.evaluate(async ({ username, password }) => {
        const response = await fetch('/login', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
        if (!response.ok) throw new Error(`Login failed: ${response.status}`);
        sessionStorage.setItem('krug-session', JSON.stringify(await response.json()));
      }, { username, password });
      await page.goto(`${base}/app#${route}`, { waitUntil: 'networkidle' });
      await page.reload({ waitUntil: 'networkidle' });
      await page.locator(ready).first().waitFor();
      // Covers and photos load lazily; wait until every visible image has decoded.
      await page.waitForFunction(() => [...document.images].filter(img => img.getBoundingClientRect().top < innerHeight).every(img => img.complete && img.naturalWidth > 0));
      await page.evaluate(() => { window.scrollTo({ top: 0, behavior: 'instant' }); if (document.activeElement instanceof HTMLElement) document.activeElement.blur(); });
      await page.locator('#toast.visible').waitFor({ state: 'hidden', timeout: 5500 }).catch(() => {});
      await page.waitForTimeout(300);
      const png = await page.screenshot();
      // Playwright writes PNG/JPEG only; the browser encodes WebP without extra tooling.
      const webp = await encoder.evaluate(async (data) => {
        const image = new Image();
        image.src = `data:image/png;base64,${data}`;
        await image.decode();
        const canvas = document.createElement('canvas');
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        canvas.getContext('2d').drawImage(image, 0, 0);
        return canvas.toDataURL('image/webp', 0.86).split(',')[1];
      }, png.toString('base64'));
      fs.writeFileSync(path.join(output, `${name}-v3.webp`), Buffer.from(webp, 'base64'));
      console.log(`saved ${name}-v3.webp`);
      await context.close();
    }
  } finally {
    await browser.close();
  }
  if (errors.length) throw new Error(errors.join('\n'));
}

main().catch(error => { console.error(error); process.exit(1); });
