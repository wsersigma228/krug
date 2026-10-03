/* Optional end-to-end check: npm install --no-save playwright in a separate tools folder.
   NODE_PATH should point to that folder's node_modules. App/DB run on the execution host. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const base = process.env.APP_URL || 'http://127.0.0.1:8000';
const output = process.env.BROWSER_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), 'blog-browser-'));
fs.mkdirSync(output, { recursive: true });
const users = [];
const mailIds = [];
const errors = [];

async function main() {
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'ru-RU', colorScheme: 'light' });
  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'ru-RU', colorScheme: 'dark' });
  const page = await desktop.newPage();
  const phone = await mobile.newPage();
  for (const p of [page, phone]) {
    p.on('pageerror', e => errors.push(e.message));
    p.on('dialog', dialog => dialog.accept());
  }
  async function register(p, role) {
    const user = { username: `browser_${role}_${crypto.randomBytes(4).toString('hex')}`, password: 'browser-check-password' };
    if (role === 'author' && process.env.MAILPIT_URL) user.email = user.username + '@example.test';
    await p.goto(base + '/app#register');
    await p.getByLabel('Имя пользователя').fill(user.username);
    await p.getByLabel('Пароль', { exact: true }).fill(user.password);
    if (user.email) await p.locator('input[name=email]').fill(user.email);
    await p.getByRole('button', { name: 'Создать аккаунт' }).click();
    await p.waitForURL('**/app#explore');
    users.push(user);
    await p.getByRole('heading', { name: 'Есть что рассказать' }).waitFor();
    return user;
  }
  async function mailToken(user, subject) {
    const mailbox = process.env.MAILPIT_URL;
    const deadline = Date.now() + 75000;
    while (Date.now() < deadline) {
      const result = await fetch(mailbox + '/api/v1/messages?limit=100').then(r => r.json());
      const message = result.messages.find(m => m.Subject === subject && m.To.some(to => to.Address === user.email));
      if (message) {
        mailIds.push(message.ID);
        const content = await fetch(mailbox + '/api/v1/message/' + message.ID).then(r => r.json());
        const token = content.Text.match(/#token=([A-Za-z0-9_-]+)/);
        assert(token, 'Missing captured link');
        return token[1];
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error('Captured email missing');
  }
  async function noOverflow(p) {
    assert(await p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Horizontal overflow');
  }
  try {
    await page.goto(base + '/app#login');
    await page.getByLabel('Имя пользователя').fill('not_an_existing_account');
    await page.getByLabel('Пароль', { exact: true }).fill('wrong-password');
    await page.getByRole('button', { name: 'Войти', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Неверное имя' }).waitFor();
    const author = await register(page, 'author');
    await page.goto(base + '/app#feed');
    await page.getByRole('heading', { name: 'Лента ждёт ваших людей' }).waitFor();
    await page.goto(base + '/app#new');
    const title = 'Browser story ' + crypto.randomBytes(3).toString('hex');
    await page.getByLabel('Заголовок').fill(title);
    await page.getByLabel('Текст', { exact: true }).fill('A real browser check. <script>window.bad=true</script>');
    const photo = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jDPsAAAAASUVORK5CYII=', 'base64');
    await page.locator('input[type=file]').setInputFiles({ name: 'check.png', mimeType: 'image/png', buffer: photo });
    await page.getByRole('button', { name: 'Сохранить историю' }).click();
    await page.waitForURL(/#post\/\d+$/);
    const postId = page.url().match(/post\/(\d+)/)[1];
    await page.getByText('Личный черновик', { exact: true }).waitFor();
    await page.locator('img.post-photo').waitFor();
    await page.waitForFunction(() => document.querySelector('img.post-photo')?.naturalWidth > 0);
    assert.equal(await page.evaluate(() => window.bad), undefined);
    await page.getByRole('link', { name: 'Редактировать', exact: true }).click();
    await page.getByLabel('Опубликовать для всех').check();
    await page.getByRole('button', { name: 'Сохранить изменения' }).click();
    await page.waitForURL('**/app#post/' + postId);
    await page.getByRole('heading', { name: title }).waitFor();
    await page.screenshot({ path: path.join(output, 'desktop-post.png'), fullPage: true });
    await noOverflow(page);
    await page.goto(base + '/app#settings');
    await page.locator('textarea[name=bio]').fill('Browser profile');
    await page.getByRole('button', { name: 'Сохранить профиль' }).click();
    await page.getByRole('status').filter({ hasText: 'Профиль сохранён' }).waitFor();
    const session = await page.evaluate(() => JSON.parse(sessionStorage.getItem('krug-session')));
    const own = await fetch(base + '/me', { headers: { Authorization: 'Bearer ' + session.access_token } }).then(r => r.json());
    if (author.email) {
      await page.locator('#verify').click();
      const token = await mailToken(author, 'Подтвердите email');
      await page.goto(base + '/verify-email#token=' + token);
      await page.getByRole('button', { name: 'Подтвердить email' }).click();
      await page.getByText(/Email подтверждён. Теперь/).waitFor();
      assert.equal(new URL(page.url()).hash, '');
      await page.goto(base + '/app#settings');
      await page.locator('input[name=enabled]').check();
      await page.getByRole('button', { name: 'Сохранить уведомления' }).click();
      await page.getByRole('status').filter({ hasText: 'Настройки уведомлений сохранены' }).waitFor();
    }
    const reader = await register(phone, 'reader');
    await phone.goto(base + '/app#profile/' + own.id);
    await phone.getByText('Browser profile', { exact: true }).waitFor();
    await phone.getByRole('button', { name: 'Подписаться', exact: true }).click();
    await phone.getByRole('button', { name: 'Вы подписаны · отписаться' }).waitFor();
    await phone.goto(base + '/app#feed');
    await phone.getByRole('link', { name: title, exact: true }).click();
    await phone.locator('#like').click();
    await phone.locator('#like[aria-pressed=true]').waitFor();
    await phone.getByLabel('Ваш комментарий').fill('Mobile comment <img onerror=alert(1)>');
    await phone.getByRole('button', { name: 'Отправить', exact: true }).click();
    await phone.getByText('Mobile comment <img onerror=alert(1)>', { exact: true }).waitFor();
    await phone.screenshot({ path: path.join(output, 'mobile-post.png'), fullPage: true });
    await noOverflow(phone);
    await phone.locator('[data-delete-comment]').click();
    await phone.waitForFunction(() => !document.querySelector('[data-delete-comment]'));
    await phone.goto(base + '/app#explore');
    await phone.locator('input[name=search]').fill(title);
    await phone.getByRole('button', { name: 'Найти', exact: true }).click();
    await phone.getByRole('link', { name: title, exact: true }).waitFor();
    await noOverflow(phone);
    await phone.goto(base + '/app#post/2147483647');
    await phone.getByRole('alert').waitFor();
    await phone.goto(base + '/app#recover');
    await phone.getByLabel('Email', { exact: true }).fill('missing@example.test');
    await phone.getByRole('button', { name: 'Отправить ссылку' }).click();
    await phone.getByText(/Если аккаунт существует, письмо скоро придёт/).waitFor();
    await phone.goto(base + '/reset-password#token=invalid');
    await phone.getByLabel('Новый пароль').fill('browser-new-password');
    await phone.getByRole('button', { name: 'Сохранить пароль' }).click();
    await phone.getByRole('alert').waitFor();
    assert.equal(new URL(phone.url()).hash, '');
    if (author.email) {
      await page.goto(base + '/app#recover');
      await page.getByLabel('Email', { exact: true }).fill(author.email);
      await page.getByRole('button', { name: 'Отправить ссылку' }).click();
      const token = await mailToken(author, 'Сброс пароля');
      await page.goto(base + '/reset-password#token=' + token);
      await page.getByLabel('Новый пароль').fill('browser-replacement-password');
      await page.getByRole('button', { name: 'Сохранить пароль' }).click();
      await page.getByText(/Пароль сохранён. Войдите/).waitFor();
      author.password = 'browser-replacement-password';
      assert.equal((await fetch(base + '/me', { headers: { Authorization: 'Bearer ' + session.access_token } })).status, 401);
      console.log('Captured email UI: verification, notification opt-in and successful password reset: OK');
    }
    assert.deepEqual(errors, []);
    console.log('Desktop/mobile UI: registration, login errors, drafts/photos, publish, profile, follow/feed, likes/comments, search, missing post and reset errors: OK');
    console.log('Screenshots: ' + output);
  } finally {
    for (const user of users.reverse()) {
      const login = await fetch(base + '/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: user.username, password: user.password }) });
      const tokens = await login.json();
      assert(login.ok, 'Could not authenticate cleanup');
      const own = await fetch(base + '/me', { headers: { Authorization: 'Bearer ' + tokens.access_token } }).then(r => r.json());
      const result = await fetch(base + '/users/' + own.id, { method: 'DELETE', headers: { Authorization: 'Bearer ' + tokens.access_token } });
      assert.equal(result.status, 204, 'Could not remove temporary browser account');
    }
    for (const id of mailIds) await fetch(process.env.MAILPIT_URL + '/api/v1/message/' + id, { method: 'DELETE' });
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
