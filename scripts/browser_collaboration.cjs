/* Authenticated collaboration UI checks for the disposable Krug preview only.
   Uses existing external Playwright; fixtures are synthetic and scoped to 18103. */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { chromium } = require('playwright');

const base = process.env.APP_URL;
if (!base || !/^http:\/\/127\.0\.0\.1:18103(?:\/|$)/.test(base)) {
  throw new Error('Set APP_URL to the isolated preview http://127.0.0.1:18103');
}
const output = process.env.BROWSER_OUTPUT || fs.mkdtempSync(path.join(os.tmpdir(), 'krug-collaboration-'));
const password = 'krug-ui-preview-only-password';
const issues = [];
const key = crypto.randomBytes(4).toString('hex');

async function api(route, { token, method = 'GET', body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(base + route, { method, headers, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
  const value = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(`${method} ${route} failed (${response.status}): ${JSON.stringify(value?.detail || value)}`);
  return value;
}

async function createAccount(username) {
  await api('/users', { method: 'POST', body: { username, password, language: 'ru' } });
  const session = await api('/login', { method: 'POST', body: { username, password } });
  const me = await api('/me', { token: session.access_token });
  return { username, token: session.access_token, id: me.id };
}

async function login(page, user) {
  await page.goto(base + '/app#login');
  await page.getByLabel('Имя пользователя').fill(user.username);
  await page.getByLabel('Пароль', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await page.getByRole('heading', { name: 'Найдите, с кем создавать дальше' }).waitFor();
}

async function capture(page, name) {
  await page.evaluate(() => { window.scrollTo({ top: 0, behavior: "instant" }); if (document.activeElement instanceof HTMLElement) document.activeElement.blur(); });
  await page.locator("#toast.visible").waitFor({ state: "hidden", timeout: 5500 }).catch(() => {});
  await page.waitForTimeout(220);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Horizontal overflow: ${name}`);
  await page.screenshot({ path: path.join(output, name), fullPage: true });
}

async function prepareAdmin() {
  const username = `krug_ui_${crypto.randomBytes(4).toString('hex')}`;
  const account = await createAccount(username);
  console.log(`Synthetic preview admin fixture ready: username=${username} id=${account.id}`);
  console.log('Promote this username only in the isolated preview DB, then set BROWSER_ADMIN_USERNAME to it.');
}

async function run() {
  fs.mkdirSync(output, { recursive: true });
  const owner = await createAccount(`krug_ui_owner_${key}`);
  const applicant = await createAccount(`krug_ui_person_${key}`);
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'ru-RU', colorScheme: 'dark' });
  const otherContext = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'ru-RU', colorScheme: 'dark' });
  const ownerPage = await context.newPage();
  const applicantPage = await otherContext.newPage();
  for (const page of [ownerPage, applicantPage]) page.on('pageerror', error => issues.push(error.message));
  let projectSlug;
  let projectId;
  let openingId;
  let updateId;
  let externalTitle;
  try {
    await login(ownerPage, owner);
    await ownerPage.goto(base + '/app#project-new');
    for (const [width, height] of [[390, 844], [1440, 1000], [3840, 2160]]) {
      await ownerPage.setViewportSize({ width, height });
      await capture(ownerPage, `project-create-${width}.png`);
    }
    await ownerPage.setViewportSize({ width: 1440, height: 1000 });
    await ownerPage.locator('input[name=title]').fill(`Preview collaboration ${key}`);
    projectSlug = `preview-collaboration-${key}`;
    await ownerPage.locator('input[name=slug]').fill(projectSlug);
    await ownerPage.locator('input[name=summary]').fill('A synthetic project for isolated collaboration UI verification.');
    await ownerPage.locator('textarea[name=description]').fill('This record exists only in the disposable preview database.');
    await ownerPage.locator('input[name=tags]').fill('game-development, preview');
    await ownerPage.locator('input[name=skills]').fill('Godot, Python');
    await ownerPage.getByLabel('Опубликовать проект').check();
    await ownerPage.getByRole('button', { name: 'Создать проект' }).click();
    await ownerPage.waitForURL(`**/app#project/${projectSlug}`);
    console.log(`Synthetic project fixture: slug=${projectSlug}; owner=${owner.username}; applicant=${applicant.username}`);
    let project = await api(`/projects/${projectSlug}`, { token: owner.token });
    projectId = project.id;
    assert.equal(project.member_count, 1, 'Owner is a factual project member');

    await ownerPage.locator('details.project-role-editor summary').click();
    for (const [width, height] of [[390, 844], [1440, 1000], [3840, 2160]]) {
      await ownerPage.setViewportSize({ width, height });
      await capture(ownerPage, `opening-create-${width}.png`);
    }
    await ownerPage.setViewportSize({ width: 1440, height: 1000 });
    const openingTitle = `Preview gameplay designer ${key}`;
    await ownerPage.locator('#opening-create input[name=role]').fill(openingTitle);
    await ownerPage.locator('#opening-create input[name=skills]').fill('Godot, game design');
    await ownerPage.locator('#opening-create input[name=commitment]').fill('3 hours weekly');
    await ownerPage.locator('#opening-create input[name=timezone]').fill('Asia/Tashkent');
    await ownerPage.locator('#opening-create input[name=experience_level]').fill('Any level');
    await ownerPage.locator('#opening-create textarea[name=description]').fill('Help shape the prototype.');
    await ownerPage.locator('#opening-create button').click();
    await ownerPage.getByText(openingTitle, { exact: true }).waitFor();
    const openings = await api(`/projects/${projectSlug}/openings?limit=24`, { token: owner.token });
    openingId = openings.items[0].id;
    assert.equal(openings.items[0].timezone, 'Asia/Tashkent');
    assert.equal(openings.items[0].experience_level, 'Any level');
    await ownerPage.goto(base + '/app#roles');
    const discoverableRole = ownerPage.locator('.platform-card-opening h3 a').filter({ hasText: openingTitle });
    await discoverableRole.waitFor();
    assert.equal(await discoverableRole.getAttribute('href'), `/project/${projectSlug}`, 'Open role links to its actual project page');
    await discoverableRole.click();
    await ownerPage.waitForURL(`**/project/${projectSlug}`);
    await ownerPage.getByRole('heading', { name: `Preview collaboration ${key}` }).waitFor();
    await ownerPage.goto(base + `/app#project/${projectSlug}`);
    await ownerPage.waitForFunction(() => { const main = document.querySelector('main'); return main && !main.inert && main.getAttribute('aria-busy') !== 'true'; });
    await ownerPage.locator('#owner-contact input[name=owner_contact_url]').fill('https://example.invalid/team-contact');
    const contactResponse = ownerPage.waitForResponse(response => response.url().includes(`/projects/${projectSlug}/contact-settings`) && response.request().method() === 'PUT');
    await ownerPage.locator('#owner-contact button').click();
    const savedContactResponse = await contactResponse;
    assert.equal(savedContactResponse.status(), 204);
    assert.deepEqual(savedContactResponse.request().postDataJSON(), { owner_contact_url: 'https://example.invalid/team-contact' });
    assert.equal((await api(`/projects/${projectSlug}/contact-settings`, { token: owner.token })).owner_contact_url, 'https://example.invalid/team-contact');
    await ownerPage.getByText('Приватный контакт сохранён.').waitFor();

    await login(applicantPage, applicant);
    await applicantPage.goto(base + '/app#collaboration-profile');
    await applicantPage.locator('[name=intent_kind]').selectOption('looking_for_teammates');
    await applicantPage.locator('[name=intent_text]').fill('I want to help build an indie game prototype.');
    await applicantPage.locator('[name=skills]').fill('Godot, Python');
    await applicantPage.locator('[name=interests]').fill('Game development');
    await applicantPage.locator('[name=wanted_skills]').fill('Game design');
    await applicantPage.locator('[name=timezone]').fill('Asia/Tashkent');
    await applicantPage.locator('[name=commitment]').fill('Evenings');
    await applicantPage.locator('[name=languages]').fill('English, Russian');
    await applicantPage.locator('[name=external_links]').fill('https://example.invalid/portfolio');
    await applicantPage.getByLabel('Показывать профиль в поиске людей').check();
    for (const [width, height] of [[390, 844], [1440, 1000], [3840, 2160]]) {
      await applicantPage.setViewportSize({ width, height });
      await capture(applicantPage, `profile-edit-${width}.png`);
    }
    await applicantPage.setViewportSize({ width: 390, height: 844 });
    await applicantPage.getByRole('button', { name: 'Сохранить профиль' }).click();
    await applicantPage.getByRole('heading', { name: applicant.username }).waitFor();

    const discoverable = await api(`/people/${applicant.id}`);
    assert.equal(discoverable.intent_kind, 'looking_for_teammates');
    await applicantPage.goto(base + `/app#explore?kind=people&search=${encodeURIComponent(applicant.username)}`);
    await applicantPage.getByRole('link', { name: applicant.username, exact: true }).waitFor();
    await capture(applicantPage, 'people-390.png');
    for (const [width, height] of [[1440, 1000], [2560, 1440], [3840, 2160]]) {
      await applicantPage.setViewportSize({ width, height });
      await capture(applicantPage, `people-${width}.png`);
    }
    await applicantPage.setViewportSize({ width: 390, height: 844 });
    await applicantPage.goto(base + `/app#profile/${applicant.id}`);
    await applicantPage.getByText('Ищу участников в проект', { exact: true }).waitFor();
    await applicantPage.getByText(/game design/i).waitFor();

    await applicantPage.goto(base + `/app#project/${projectSlug}`);
    const projectTag = applicantPage.locator(".project-detail .project-tags a.project-tag").first();
    assert((await projectTag.boundingBox()).height >= 44, "Mobile project tag has a 44px target");
    await projectTag.click();
    await applicantPage.waitForURL(/#explore\?kind=projects/);
    await applicantPage.goto(base + `/app#project/${projectSlug}`);
    const engagement = applicantPage.locator('.engagement-form');
    await engagement.waitFor();
    await engagement.locator('[name=saved]').check();
    await engagement.locator('[name=following]').check();
    await engagement.locator('[name=interested]').check();
    assert.equal(await engagement.locator('[name=interested_visible]').isChecked(), false, 'Interest is private until explicit consent');
    await engagement.getByRole('button', { name: 'Сохранить выбор' }).click();
    await applicantPage.waitForFunction(() => Boolean(document.querySelector('#engagement-status')?.textContent.trim()));
    let choices = await api(`/projects/${projectSlug}/engagement`, { token: applicant.token });
    assert.equal(choices.saved, true);
    assert.equal(choices.following, true);
    assert.equal(choices.interested, true);
    assert.equal(choices.interested_visible, false);
    let interestedProfiles = await api(`/projects/${projectSlug}/interested?limit=24`);
    assert(!interestedProfiles.items.some(person => person.id === applicant.id), 'Private interest is not publicly listed');
    await engagement.locator('[name=interested_visible]').check();
    const visibilityResponse = applicantPage.waitForResponse(response => response.url().includes(`/projects/${projectSlug}/engagement`) && response.request().method() === 'PATCH' && response.status() === 200);
    await engagement.getByRole('button', { name: 'Сохранить выбор' }).click();
    await visibilityResponse;
    await applicantPage.waitForFunction(() => Boolean(document.querySelector('#engagement-status')?.textContent.trim()));
    choices = await api(`/projects/${projectSlug}/engagement`, { token: applicant.token });
    assert.equal(choices.interested_visible, true);
    interestedProfiles = await api(`/projects/${projectSlug}/interested?limit=24`);
    assert(interestedProfiles.items.some(person => person.id === applicant.id), 'Explicitly opted-in profile appears in interested people');
    for (const [width, height] of [[390, 844], [1440, 1000], [3840, 2160]]) {
      await applicantPage.setViewportSize({ width, height });
      await capture(applicantPage, `opening-apply-${width}.png`);
    }
    await applicantPage.setViewportSize({ width: 390, height: 844 });
    await applicantPage.locator(`form[data-apply="${openingId}"]`).locator('textarea[name=message]').fill('I can help with the prototype and weekly playtests.');
    await applicantPage.locator(`form[data-apply="${openingId}"] input[name=applicant_contact_url]`).fill('https://example.invalid/applicant-contact');
    await applicantPage.locator(`form[data-apply="${openingId}"] button`).click();
    await applicantPage.getByText('Заявка отправлена владельцу проекта.').waitFor();
    const ownerApplications = await api(`/projects/${projectSlug}/applications`, { token: owner.token });
    assert.equal(ownerApplications.length, 1);
    assert.equal(ownerApplications[0].applicant_contact_url, null, 'Applicant contact stays hidden while pending');
    const applicantApplications = await api('/me/applications', { token: applicant.token });
    assert.equal(applicantApplications[0].owner_contact_url, null, 'Owner contact stays hidden while pending');

    await ownerPage.goto(base + `/app#project/${projectSlug}`);
    await ownerPage.reload();
    const acceptResponse = ownerPage.waitForResponse(response => response.url().includes(`/projects/${projectSlug}/applications/`) && response.request().method() === 'PATCH' && response.status() === 200);
    await ownerPage.getByRole('button', { name: 'Принять', exact: true }).click();
    await acceptResponse;
    await ownerPage.getByRole('link', { name: applicant.username, exact: true }).waitFor();
    const accepted = await api(`/projects/${projectSlug}/applications`, { token: owner.token });
    assert.equal(accepted[0].status, 'accepted');
    assert.equal(accepted[0].applicant_contact_url, 'https://example.invalid/applicant-contact');
    assert.equal(accepted[0].owner_contact_url, 'https://example.invalid/team-contact');
    const member = await api(`/projects/${projectSlug}/members`);
    assert(member.items.some(item => item.user_id === applicant.id));
    project = await api(`/projects/${projectSlug}`);
    assert.equal(project.member_count, 2);
    assert.equal(project.open_roles_count, 1);

    await applicantPage.goto(base + '/app#applications');
    await applicantPage.getByRole('link', { name: 'Связаться с командой' }).waitFor();
    await applicantPage.getByRole('link', { name: 'Связаться с командой' }).evaluate(link => {
      if (link.href !== 'https://example.invalid/team-contact') throw new Error('Accepted applicant contact did not match');
    });
    await applicantPage.goto(base + `/app#project/${projectSlug}`);
    const memberLink = applicantPage.locator('.project-member').filter({ hasText: applicant.username });
    await memberLink.waitFor();
    assert(await memberLink.getAttribute('href') === `/app#profile/${applicant.id}`, 'Membership link uses the actual user ID');

    await applicantPage.goto(base + `/app#project/${projectSlug}`);
    const updateLink = applicantPage.locator(`a[href="/app#new?project=${projectId}"]`);
    await updateLink.waitFor();
    await updateLink.click();
    await applicantPage.getByText('Обновление проекта', { exact: true }).waitFor();
    for (const [width, height] of [[390, 844], [1440, 1000], [3840, 2160]]) {
      await applicantPage.setViewportSize({ width, height });
      await capture(applicantPage, `project-update-edit-${width}.png`);
    }
    await applicantPage.setViewportSize({ width: 390, height: 844 });
    await applicantPage.locator('input[name=title]').fill(`Accepted member update ${key}`);
    await applicantPage.locator('textarea[name=content]').fill('A synthetic progress update from an accepted project member.');
    await applicantPage.getByLabel('Опубликовать для всех').check();
    await applicantPage.getByRole('button', { name: "Сохранить обновление", exact: true }).click();
    await applicantPage.waitForURL(/#post\/\d+$/);
    updateId = Number(applicantPage.url().match(/post\/(\d+)$/)[1]);
    await applicantPage.goto(base + `/app#project/${projectSlug}`);
    await applicantPage.reload();
    await applicantPage.getByText(`Accepted member update ${key}`, { exact: true }).waitFor();
    project = await api(`/projects/${projectSlug}`);
    assert.equal(project.published_updates_count, 1);
    await applicantPage.goto(base + '/app#explore');
    await applicantPage.getByRole('heading', { name: 'Все результаты' }).waitFor();
    await applicantPage.locator('.platform-card h3 a').filter({ hasText: `Preview collaboration ${key}` }).waitFor();
    for (const [width, height] of [[390, 844], [1440, 1000], [2560, 1440], [3840, 2160]]) {
      await applicantPage.setViewportSize({ width, height });
      await capture(applicantPage, `discovery-${width}.png`);
    }
    await applicantPage.setViewportSize({ width: 390, height: 844 });
    await applicantPage.goto(base + `/app#project/${projectSlug}`);
    await applicantPage.getByText(`Accepted member update ${key}`, { exact: true }).waitFor();
    await capture(applicantPage, 'project-390.png');
    for (const [width, height] of [[1440, 1000], [2560, 1440], [3840, 2160]]) {
      await applicantPage.setViewportSize({ width, height });
      await capture(applicantPage, `project-${width}.png`);
    }
    await applicantPage.goto(base + `/app#profile/${applicant.id}`);
    await applicantPage.getByText('Проекты и участие').waitFor();
    await applicantPage.getByRole('link', { name: new RegExp(`Preview collaboration ${key}`) }).waitFor();
    for (const [width, height] of [[390, 844], [1440, 1000], [2560, 1440], [3840, 2160]]) {
      await applicantPage.setViewportSize({ width, height });
      await capture(applicantPage, `profile-${width}.png`);
    }

    const publicProject = await context.newPage();
    await publicProject.goto(base + `/project/${projectSlug}`, { waitUntil: 'networkidle' });
    await publicProject.locator('.share-project').waitFor();
    await publicProject.getByRole('heading', { name: 'Open roles' }).waitFor();
    await publicProject.getByRole('heading', { name: 'Project members' }).waitFor();
    await publicProject.getByText(applicant.username, { exact: true }).waitFor();
    for (const [width, height] of [[390, 844], [1440, 1000], [2560, 1440], [3840, 2160]]) {
      await publicProject.setViewportSize({ width, height });
      await capture(publicProject, `public-project-${width}.png`);
    }
    const publicUpdate = await publicProject.goto(base + `/project/${projectSlug}/updates/${updateId}`, { waitUntil: 'networkidle' });
    assert.equal(publicUpdate.status(), 200);
    await publicProject.getByRole('heading', { name: `Accepted member update ${key}` }).waitFor();
    for (const [width, height] of [[390, 844], [1440, 1000], [2560, 1440], [3840, 2160]]) {
      await publicProject.setViewportSize({ width, height });
      await capture(publicProject, `public-update-${width}.png`);
    }

    if (process.env.BROWSER_ADMIN_USERNAME) {
      externalTitle = `Preview external suggestion ${key}`;
      await applicantPage.goto(base + '/app#external-submit');
      await applicantPage.locator('[name=title]').fill(externalTitle);
      await applicantPage.locator('[name=summary]').fill('A synthetic external submission awaiting review.');
      await applicantPage.locator('[name=description]').fill('Synthetic content used only in the isolated preview.');
      await applicantPage.locator('[name=tags]').fill('preview, game-development');
      await applicantPage.locator('[name=skills]').fill('Godot');
      await applicantPage.locator('[name=source_url]').fill(`https://example.invalid/${key}`);
      await applicantPage.getByRole('button', { name: 'Отправить на проверку' }).click();
      await applicantPage.getByText('Проект отправлен на проверку').waitFor();

      const adminPage = await context.newPage();
      const admin = { username: process.env.BROWSER_ADMIN_USERNAME };
      await login(adminPage, admin);
      await adminPage.goto(base + '/app#admin-review');
      await adminPage.getByRole('heading', { name: externalTitle }).waitFor();
      await capture(adminPage, 'admin-review-1440.png');
      const externalReview = adminPage.locator('.review-item').filter({ has: adminPage.getByRole('heading', { name: externalTitle, exact: true }) });
      await externalReview.getByRole('button', { name: 'Одобрить', exact: true }).click();
      await adminPage.getByText(externalTitle, { exact: true }).waitFor({ state: 'detached' });
      const external = await api(`/discovery?search=${encodeURIComponent(externalTitle)}&limit=10`);
      const externalProject = external.items.find(item => item.title === externalTitle);
      assert(externalProject, 'Approved suggestion is discoverable as an external project');
      assert.equal(externalProject.origin, 'external');
      await applicantPage.goto(base + `/app#project/${externalProject.slug}`);
      await applicantPage.getByRole('link', { name: 'Создать похожий проект' }).waitFor();
      await applicantPage.getByRole('link', { name: 'Открытые профили интереса' }).waitFor();
      await applicantPage.getByRole('link', { name: 'Создать похожий проект' }).click();
      await applicantPage.getByText(externalTitle, { exact: true }).waitFor();
      await applicantPage.locator('input[name=slug]').fill(`inspired-${key}`);
      await applicantPage.locator('input[name=title]').fill(`Inspired project ${key}`);
      await applicantPage.locator('input[name=summary]').fill('An independent synthetic project inspired by an external reference.');
      await applicantPage.getByLabel('Опубликовать проект').check();
      await applicantPage.getByRole('button', { name: 'Создать проект' }).click();
      await applicantPage.waitForURL(`**/app#project/inspired-${key}`);
      const inspired = await api(`/projects/inspired-${key}`, { token: applicant.token });
      assert.equal(inspired.derived_from_project_id, externalProject.id);

      await applicantPage.goto(base + `/app#project/${externalProject.slug}`);
      await applicantPage.getByRole('link', { name: 'Я представляю этот проект' }).click();
      const claimEvidence = `Synthetic preview claim ${key} used to test the admin queue.`;
      await applicantPage.locator('textarea[name=evidence_text]').fill(claimEvidence);
      await applicantPage.getByRole('button', { name: 'Отправить на проверку' }).click();
      await applicantPage.waitForURL(`**/app#project/${externalProject.slug}`);
      await adminPage.goto(base + '/app#admin-review');
      await adminPage.reload();
      await adminPage.getByRole('heading', { name: externalTitle }).waitFor();
      await adminPage.getByText(claimEvidence, { exact: true }).waitFor();
      const claimReview = adminPage.locator('.review-item').filter({ hasText: claimEvidence });
      await claimReview.locator('[data-review=approved][data-type=claim]').click();
      await adminPage.getByText(claimEvidence, { exact: true }).waitFor({ state: 'detached' });
      await applicantPage.goto(base + `/app#project/${externalProject.slug}`);
      // Approval changed ownership in another session; the hash is unchanged from claim submission.
      await applicantPage.reload();
      await applicantPage.getByRole('link', { name: 'Редактировать проект' }).waitFor();
      await applicantPage.goto(base + `/app#project-edit/${externalProject.slug}`);
      await applicantPage.locator('input[name=source_url]').waitFor({ state: 'detached' });
      for (const [width, height] of [[390, 844], [1440, 1000], [3840, 2160]]) {
        await applicantPage.setViewportSize({ width, height });
        await capture(applicantPage, `claimed-project-edit-${width}.png`);
      }
      await applicantPage.setViewportSize({ width: 390, height: 844 });
      await applicantPage.locator('input[name=summary]').fill('Updated synthetic summary; original source remains unchanged.');
      await applicantPage.getByRole('button', { name: 'Сохранить изменения' }).click();
      await applicantPage.getByText('Updated synthetic summary; original source remains unchanged.', { exact: true }).waitFor();
      const editedClaimedProject = await api(`/projects/${externalProject.slug}`, { token: applicant.token });
      assert.equal(editedClaimedProject.summary, 'Updated synthetic summary; original source remains unchanged.');
      assert.equal(editedClaimedProject.source_url, `https://example.invalid/${key}`);
    } else {
      console.log('Admin review flow skipped: set BROWSER_ADMIN_USERNAME to the synthetic promoted preview admin.');
    }

    assert.deepEqual(issues, [], `Browser errors: ${issues.join('; ')}`);
    console.log(`Authenticated collaboration flows passed. Project: ${projectSlug}; screenshots: ${output}`);
  } finally {
    await browser.close();
  }
}

(process.argv.includes('--prepare-admin') ? prepareAdmin() : run()).catch(error => { console.error(error); process.exitCode = 1; });
