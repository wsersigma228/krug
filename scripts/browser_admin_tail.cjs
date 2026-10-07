/* Focused admin approval and claim/edit UI check for an existing isolated preview submission. */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { chromium } = require('playwright');

const base = process.env.APP_URL;
const adminUsername = process.env.BROWSER_ADMIN_USERNAME;
const title = process.env.BROWSER_EXTERNAL_TITLE;
if (!base || !/^http:\/\/127\.0\.0\.1:18103(?:\/|$)/.test(base) || !adminUsername || !title) {
  throw new Error('Set APP_URL to 18103, BROWSER_ADMIN_USERNAME to the synthetic preview admin, and BROWSER_EXTERNAL_TITLE to a pending fixture.');
}
const password = 'krug-ui-preview-only-password';
const output = process.env.BROWSER_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), 'krug-admin-tail-'));
const key = crypto.randomBytes(4).toString('hex');

async function api(route, { token, method = 'GET', body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(base + route, { method, headers, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
  const value = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(`${method} ${route} failed (${response.status})`);
  return value;
}

async function sessionFor(username, register = false) {
  if (register) await api('/users', { method: 'POST', body: { username, password, language: 'ru' } });
  return api('/login', { method: 'POST', body: { username, password } });
}

async function run() {
  const adminSession = await sessionFor(adminUsername);
  const adminList = await api('/admin/external-submissions', { token: adminSession.access_token });
  const submission = adminList.items.find(item => item.title === title);
  assert(submission, `Pending external submission not found: ${title}`);
  const person = `krug_ui_claim_${key}`;
  const personSession = await sessionFor(person, true);
  const personProfile = await api('/me', { token: personSession.access_token });
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'ru-RU' });
  const adminPage = await context.newPage();
  const personPage = await context.newPage();
  try {
    await adminPage.addInitScript(value => sessionStorage.setItem('krug-session', JSON.stringify(value)), adminSession);
    await personPage.addInitScript(value => sessionStorage.setItem('krug-session', JSON.stringify(value)), personSession);
    await adminPage.goto(base + '/app#admin-review');
    const submissionCard = adminPage.locator('.review-item').filter({ has: adminPage.getByRole('heading', { name: title, exact: true }) });
    await submissionCard.waitFor();
    await adminPage.screenshot({ path: path.join(output, 'admin-review.png'), fullPage: true });
    await submissionCard.getByRole('button', { name: 'Одобрить', exact: true }).click();
    await submissionCard.waitFor({ state: 'detached' });
    const discovery = await api(`/discovery?search=${encodeURIComponent(title)}&limit=10`);
    const project = discovery.items.find(item => item.title === title);
    assert(project && project.origin === 'external', 'Approved submission is available as an external project');

    await personPage.goto(base + `/app#project/${project.slug}`);
    await personPage.reload();
    await personPage.getByRole('link', { name: 'Я представляю этот проект' }).click();
    const evidence = `Synthetic admin tail claim ${key}`;
    await personPage.locator('[name=evidence_text]').fill(evidence);
    await personPage.getByRole('button', { name: 'Отправить на проверку' }).click();
    await personPage.waitForURL(`**/app#project/${project.slug}`);

    await adminPage.goto(base + '/app#admin-review');
    await adminPage.reload();
    const claimCard = adminPage.locator('.review-item').filter({ hasText: evidence });
    await claimCard.waitFor();
    await claimCard.locator('[data-review=approved][data-type=claim]').click();
    await claimCard.waitFor({ state: 'detached' });

    await personPage.goto(base + `/app#project/${project.slug}`);
    await personPage.reload();
    await personPage.getByRole('link', { name: 'Редактировать проект' }).waitFor();
    await personPage.goto(base + `/app#project-edit/${project.slug}`);
    await personPage.locator('input[name=source_url]').waitFor({ state: 'detached' });
    const originalProject = await api(`/projects/${project.slug}`, { token: personSession.access_token });
    assert.equal(await personPage.locator('[name=status]').inputValue(), originalProject.status);
    assert.equal(await personPage.locator('[name=stage]').inputValue(), originalProject.stage);
    const summary = `Synthetic claimed project edit ${key}`;
    await personPage.locator('[name=summary]').fill(summary);
    const updateResponse = personPage.waitForResponse(response => response.url().includes(`/projects/${project.slug}`) && response.request().method() === 'PATCH');
    await personPage.getByRole('button', { name: 'Сохранить изменения' }).click();
    const savedResponse = await updateResponse;
    if (!savedResponse.ok()) throw new Error(`Claimed project PATCH failed (${savedResponse.status()}): ${await savedResponse.text()}`);
    await personPage.getByText(summary, { exact: true }).waitFor();
    const edited = await api(`/projects/${project.slug}`, { token: personSession.access_token });
    assert.equal(edited.summary, summary);
    assert.equal(edited.source_url, project.source_url);
    assert.equal(edited.status, originalProject.status);
    assert.equal(edited.stage, originalProject.stage);
    assert(edited.owner_id === personProfile.id, 'Claim approval assigned ownership');
    console.log(`Focused admin approval and claimed project edit passed. Screenshot: ${output}`);
  } finally {
    await browser.close();
  }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
