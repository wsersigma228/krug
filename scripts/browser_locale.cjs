/* Real HTTP/browser checks. Run through an SSH tunnel to the Fedora application. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const base = process.env.APP_URL || 'http://127.0.0.1:8000';
const output = process.env.BROWSER_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), 'blog-locale-'));
fs.mkdirSync(output, { recursive: true });
async function main() {
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'ru-RU', colorScheme: 'light' });
  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'en-US', colorScheme: 'dark', isMobile: true, hasTouch: true });
  const page = await desktop.newPage();
  const phone = await mobile.newPage();
  const errors = [];
  for (const p of [page, phone]) p.on('pageerror', error => errors.push(error.message));
  const username = 'locale_' + crypto.randomBytes(5).toString('hex');
  const password = 'locale-check-password';
  let user;
  let headers;
  let otherUser;
  let otherHeaders;
  async function request(route, method = 'GET', body, auth = headers) {
    const response = await fetch(base + route, { method, headers: { ...auth, 'Content-Type': 'application/json' }, ...(body ? { body: JSON.stringify(body) } : {}) });
    assert(response.ok, `${method} ${route}: ${response.status}`);
    return response.status === 204 ? null : response.json();
  }
  async function preference(p, selector, value) {
    if (selector === '#ui-language') {
      if (await p.locator('html').getAttribute('lang') !== value) await p.locator(selector).click();
    } else {
      await p.locator('#ui-theme').click();
      await p.locator(`[data-theme-choice="${value}"]`).click();
    }
    if (selector === '#ui-language') await p.waitForFunction(value => document.documentElement.lang === value && !document.querySelector('#ui-language').disabled && !document.querySelector('#main[aria-busy=true]'), value);
    else await p.waitForFunction(value => document.documentElement.dataset.theme === value, value);
  }
  async function noOverflow(p) {
    assert(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Horizontal overflow');
  }
  async function englishCopy(p) {
    const copy = (await p.locator('body').innerText()).replace(/Русский/g, '');
    assert(!/[\u0400-\u04ff]/.test(copy), `Untranslated interface: ${copy}`);
  }
  try {
    await page.goto(base + '/app#register');
    assert.equal(await page.locator('html').getAttribute('lang'), 'ru');
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'dark');
    await page.locator('[name=username]').fill(username);
    await page.locator('[name=password]').fill(password);
    await preference(page, '#ui-language', 'en');
    assert.equal(await page.locator('[name=username]').inputValue(), username);
    assert.equal(await page.locator('[name=password]').inputValue(), password);
    await englishCopy(page);
    await preference(page, '#ui-language', 'ru');
    await page.getByRole('button', { name: 'Создать аккаунт', exact: true }).click();
    await page.waitForURL('**/app#explore');
    const tokens = await page.evaluate(() => JSON.parse(sessionStorage.getItem('krug-session')));
    headers = { Authorization: 'Bearer ' + tokens.access_token };
    user = await request('/me');
    assert.equal(user.language, 'ru');
    // Exercise refresh on the initial render, when no cached profile exists yet.
    let forceRefresh = true;
    await page.route('**/me', route => {
      if (forceRefresh) { forceRefresh = false; return route.fulfill({ status: 401, body: '{}' }); }
      return route.continue();
    });
    await page.goto(base + '/app#settings');
    await page.locator('#profile-form').waitFor();
    assert.equal(await page.locator('html').getAttribute('lang'), 'ru');
    await page.unroute('**/me');
    await page.goto(base + '/app#new');
    const title = 'Оригинальный заголовок — Browser check';
    const content = 'Пользовательский текст не переводится. <script>window.bad=true</script>';
    await page.locator('[name=title]').fill(title);
    await page.locator('[name=content]').fill(content);
    const photo = Buffer.from(await page.evaluate(() => {
      const canvas = document.createElement('canvas'); canvas.width = 960; canvas.height = 540;
      const ctx = canvas.getContext('2d'); const gradient = ctx.createLinearGradient(0, 0, 960, 540);
      gradient.addColorStop(0, '#333'); gradient.addColorStop(1, '#999');
      ctx.fillStyle = gradient; ctx.fillRect(0, 0, 960, 540);
      ctx.fillStyle = '#fff'; ctx.font = '32px sans-serif'; ctx.fillText('Synthetic test image', 48, 480);
      return canvas.toDataURL('image/png').split(',')[1];
    }), 'base64');
    await page.locator('[name=image]').setInputFiles({ name: 'locale.png', mimeType: 'image/png', buffer: photo });
    await preference(page, '#ui-language', 'en');
    assert.equal(await page.locator('[name=title]').inputValue(), title);
    assert.equal(await page.locator('[name=content]').inputValue(), content);
    assert.equal(await page.locator('[name=image]').evaluate(el => el.files[0].name), 'locale.png');
    await page.waitForFunction(() => document.querySelector('.photo-preview')?.naturalWidth > 0);
    // A failed upload must keep the draft ID across a language switch and retry.
    await page.route('**/posts/*/image', route => route.request().method() === 'PUT' ? route.abort() : route.continue());
    await page.getByRole('button', { name: 'Save story', exact: true }).click();
    await page.getByRole('alert').waitFor();
    const draftId = new URL(page.url()).hash.match(/^#edit\/(\d+)$/)?.[1];
    assert(draftId, 'Partial save must keep its draft route');
    await page.unroute('**/posts/*/image');
    await preference(page, '#ui-language', 'ru');
    await page.getByRole('button', { name: 'Сохранить изменения', exact: true }).click();
    await page.waitForURL('**/app#post/' + draftId);
    assert.equal((await request('/posts')).items.length, 1, 'Retry must reuse the same draft');
    assert.equal((await request('/posts/' + draftId)).content, content);
    assert.equal(await page.evaluate(() => window.bad), undefined);
    await page.goto(base + '/app#edit/' + draftId);
    await page.waitForFunction(() => document.querySelector('#preview img')?.naturalWidth > 0);
    await preference(page, '#ui-language', 'en');
    await page.waitForFunction(() => document.querySelector('#preview img')?.naturalWidth > 0);
    await page.locator('[name=published]').check();
    await page.getByRole('button', { name: 'Save changes', exact: true }).click();
    await page.waitForURL('**/app#post/' + draftId);
    await page.locator('.article-body').waitFor();
    await page.waitForFunction(() => !document.querySelector('#main[aria-busy=true]'));
    await page.locator('textarea[name=content]').fill('Несохранённый комментарий');
    await preference(page, '#ui-language', 'ru');
    assert.equal(await page.locator('textarea[name=content]').inputValue(), 'Несохранённый комментарий');
    await page.goto(base + '/app#settings');
    await page.locator('textarea[name=bio]').fill('Несохранённое описание');
    await preference(page, '#ui-language', 'en');
    assert.equal(await page.locator('textarea[name=bio]').inputValue(), 'Несохранённое описание');
    assert.equal((await request('/me')).language, 'en');
    await phone.goto(base + '/app#login');
    assert.equal(await phone.locator('html').getAttribute('lang'), 'en');
    assert.equal(await phone.locator('html').getAttribute('data-theme'), 'dark');
    await englishCopy(phone);
    await phone.locator('[name=username]').fill(username);
    await phone.locator('[name=password]').fill(password);
    await phone.getByRole('button', { name: 'Sign in', exact: true }).click();
    await phone.waitForURL('**/app#explore');
    await phone.getByRole('link', { name: title, exact: true }).waitFor();
    assert.equal(await phone.locator('html').getAttribute('lang'), 'en');
    await phone.reload();
    await phone.getByRole('link', { name: title, exact: true }).waitFor();
    await request('/posts', 'POST', { title: 'Synthetic text-only story', content: 'A text-first feed should work with and without photographs. This temporary post is part of the browser verification and will be removed with the test account.', is_published: true });
    otherUser = await request('/users', 'POST', { username: username + '_writer', password });
    const otherTokens = await request('/login', 'POST', { username: otherUser.username, password });
    otherHeaders = { Authorization: 'Bearer ' + otherTokens.access_token };
    for (let index = 0; index < 2; index++) await request('/posts', 'POST', { title: 'Another author ' + index, content: 'Temporary synthetic story for author-rail verification.', is_published: true }, otherHeaders);
    for (const [p, label] of [[page, 'desktop'], [phone, 'mobile']]) {
      await p.goto(base + '/app#explore');
      await p.reload();
      await p.getByRole('link', { name: title, exact: true }).waitFor();
      await p.waitForFunction(() => document.querySelector('.post-photo')?.naturalWidth > 0);
      await p.waitForFunction(() => !document.querySelector('#main[aria-busy=true]') && !document.querySelector('#toast.visible'));
      assert.equal(await p.locator('.rail-author').count(), 1, 'Authors are distinct and exclude the current account');
      assert.equal(await p.locator('.rail-author').textContent(), otherUser.username[0].toUpperCase() + otherUser.username);
      assert.equal(await p.locator('.context-rail').isVisible(), label === 'desktop');
      for (const selected of ['light', 'dark']) {
        await preference(p, '#ui-theme', selected);
        await p.waitForFunction(() => !document.getAnimations().some(animation => animation.playState === 'running'));
        await noOverflow(p);
        await p.screenshot({ path: path.join(output, `${label}-${selected}.png`), fullPage: true });
      }
    }
    await page.setViewportSize({ width: 1920, height: 1080 });
    await noOverflow(page);
    assert((await page.locator('.layout').boundingBox()).width >= 1500, 'Wide screens should use the desktop shell');
    await page.screenshot({ path: path.join(output, 'wide-dark.png'), fullPage: true });
    for (const width of [2560, 3840]) {
      await page.setViewportSize({ width, height: 1440 });
      await noOverflow(page);
      const photoLayout = await page.locator('.post-photo').first().evaluate(image => {
        const rect = image.getBoundingClientRect();
        const card = image.closest('.post-card').getBoundingClientRect();
        const copy = image.closest('.post-card').querySelector('.post-copy').getBoundingClientRect();
        const style = getComputedStyle(image);
        return { loaded: image.naturalWidth > 0, fits: rect.left >= card.left && rect.right <= card.right + 1 && rect.bottom <= card.bottom + 1,
          contained: style.objectFit === 'contain', belowCopy: rect.top >= copy.bottom && Math.abs(rect.left - copy.left) < 1 };
      });
      assert(photoLayout.loaded && photoLayout.fits && photoLayout.contained && photoLayout.belowCopy, 'Wide photos must stay contained below text and aligned with its left edge');
    }
    await page.setViewportSize({ width: 1440, height: 500 });
    const destinations = await page.locator('.topbar .nav a').count();
    await page.evaluate(() => window.scrollTo(0, 700));
    await page.waitForFunction(() => document.body.classList.contains('header-compact'));
    assert.equal(await page.locator('.topbar .nav a:visible').count(), destinations, 'Compact header keeps every destination');
    assert(await page.locator('#ui-language').isVisible() && await page.locator('#ui-theme').isVisible(), 'Compact preferences remain reachable');
    await page.evaluate(() => window.scrollTo(0, 400));
    await page.waitForFunction(() => !document.body.classList.contains('header-compact'));
    await page.setViewportSize({ width: 1199, height: 900 });
    assert.equal(await page.locator('.context-rail').isVisible(), false);
    await noOverflow(page);
    await phone.setViewportSize({ width: 320, height: 700 });
    await noOverflow(phone);
    await phone.reload();
    await phone.getByRole('link', { name: title, exact: true }).waitFor();
    assert.equal(await phone.locator('html').getAttribute('data-theme'), 'dark');
    // Signed-in account preference beats a conflicting browser preference on login.
    await request('/me/language', 'PATCH', { language: 'ru' });
    await phone.reload();
    await phone.getByRole('heading', { name: 'Обзор', exact: true }).waitFor();
    assert.equal(await phone.locator('html').getAttribute('lang'), 'ru');
    await noOverflow(phone);
    // Email link locale overrides a different browser language; toggling keeps token and password.
    await phone.goto(base + '/reset-password?lang=en#token=invalid');
    await phone.locator('[name=password]').fill(password);
    await preference(phone, '#ui-language', 'ru');
    assert.equal(await phone.locator('[name=password]').inputValue(), password);
    await phone.getByRole('button', { name: 'Сохранить пароль', exact: true }).click();
    await phone.getByRole('alert').waitFor();
    assert.equal(new URL(phone.url()).hash, '');
    let postedToken;
    await phone.route('**/auth/password-reset/confirm', route => {
      postedToken = route.request().postDataJSON().token;
      return route.continue();
    });
    await phone.evaluate(() => { location.hash = 'token=replacement'; });
    await phone.waitForFunction(() => !location.hash && !document.querySelector('#main[aria-busy=true]'));
    await phone.locator('[name=password]').fill(password);
    await phone.getByRole('button', { name: 'Сохранить пароль', exact: true }).click();
    await phone.getByRole('alert').waitFor();
    assert.equal(postedToken, 'replacement', 'A new link in the same tab must replace the previous token');
    assert.deepEqual(errors, []);
    console.log('RU/EN defaults, account sync, refresh, drafts/photos, partial-save retry, comments/bio, link tokens, themes and 320/390/1440px layouts: OK');
    console.log('Screenshots: ' + output);
  } finally {
    if (otherUser && otherHeaders) await request('/users/' + otherUser.id, 'DELETE', undefined, otherHeaders);
    if (user) await request('/users/' + user.id, 'DELETE');
    else {
      const login = await fetch(base + '/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
      if (login.ok) {
        const tokens = await login.json(); headers = { Authorization: 'Bearer ' + tokens.access_token };
        const account = await request('/me'); await request('/users/' + account.id, 'DELETE');
      }
    }
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
