const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const base = process.env.APP_URL;
const artDir = process.env.BROWSER_ART_DIR;
if (!base || !/^http:\/\/127\.0\.0\.1:18103(?:\/|$)/.test(base)) throw new Error('Set APP_URL to the isolated preview http://127.0.0.1:18103');
if (!artDir || !fs.existsSync(path.join(artDir, 'event.png')) || !fs.existsSync(path.join(artDir, 'team.png')) || !fs.existsSync(path.join(artDir, 'project.png'))) throw new Error('Set BROWSER_ART_DIR to the isolated synthetic preview art directory');
const password = 'krug-ui-platform-preview-only-password';
const key = crypto.randomBytes(4).toString('hex');
const issues = [];
const slug = prefix => `${prefix}-${key}`;

async function api(route, { token, method = 'GET', body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(base + route, { method, headers, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
  const value = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(`${method} ${route} failed (${response.status}): ${JSON.stringify(value?.detail || value)}`);
  return value;
}
async function assertDeleted(route, token, label) {
  const response = await fetch(base + route, { headers: { Authorization: `Bearer ${token}` } });
  assert.equal(response.status, 404, `${label} remains retrievable after deletion`);
}
async function assertDraftCover(kind, entitySlug, owner, member, ownerPage) {
  const plural = { project: 'projects', team: 'teams', community: 'communities', event: 'events' }[kind];
  const route = '/' + plural + '/' + entitySlug;
  const detailRoute = (kind === 'project' ? 'project/' : kind + '/') + entitySlug;
  const editRoute = (kind === 'project' ? 'project-edit/' : kind + '-edit/') + entitySlug;
  const entity = await api(route, { token: owner.token, method: 'PATCH', body: { visibility: 'draft' } });
  assert(entity.cover_url, kind + ' draft retains its uploaded cover');
  const coverUrl = new URL(entity.cover_url, base);
  const anonymous = await fetch(coverUrl);
  const nonOwner = await fetch(coverUrl, { headers: { Authorization: 'Bearer ' + member.token } });
  assert.equal(anonymous.status, 404, kind + ' draft cover remains private to anonymous requests');
  assert.equal(nonOwner.status, 404, kind + ' draft cover remains private to non-owner requests');
  for (const routeName of [detailRoute, editRoute]) {
    await ownerPage.goto(base + '/app#' + routeName);
    const coverSelector = routeName === detailRoute
      ? kind === 'project' ? '.project-detail-main > img.platform-cover' : '.platform-detail > div > img.platform-cover'
      : '.cover-editor img.platform-cover';
    await waitReady(ownerPage, coverSelector);
    await ownerPage.waitForFunction(selector => {
      const image = document.querySelector(selector);
      return image && image.complete && image.naturalWidth > 0 && image.src.startsWith('blob:');
    }, coverSelector);
    assert.match(await ownerPage.locator(coverSelector).getAttribute('src'), /^blob:/, kind + ' owner cover uses an authenticated blob URL');
  }
  const restored = await api(route, { token: owner.token, method: 'PATCH', body: { visibility: 'public' } });
  await ownerPage.goto(base + '/app#' + detailRoute);
  const detailSelector = kind === 'project' ? '.project-detail-main > img.platform-cover' : '.platform-detail > div > img.platform-cover';
  await waitReady(ownerPage, detailSelector);
  assert.equal(await ownerPage.locator(detailSelector).getAttribute('src'), restored.cover_url, kind + ' public cover keeps its direct URL');
  await ownerPage.waitForFunction(selector => {
    const image = document.querySelector(selector);
    return image && image.complete && image.naturalWidth > 0;
  }, detailSelector);
}

async function account(prefix) {
  const username = slug(prefix);
  await api('/users', { method: 'POST', body: { username, password, language: 'ru' } });
  const session = await api('/login', { method: 'POST', body: { username, password } });
  const me = await api('/me', { token: session.access_token });
  return { username, token: session.access_token, id: me.id };
}

async function login(page, user) {
  await page.goto(base + '/app#login');
  await waitReady(page, '.auth form');
  await page.locator('.auth input[name=username]').fill(user.username);
  await page.locator('.auth input[name=password]').fill(password);
  await page.locator('.auth form button').click();
  await page.getByRole('heading', { name: 'Найдите, с кем создавать дальше' }).waitFor();
  await waitReady(page, '#discovery-results');
}

function localDate(hoursFromNow) {
  const date = new Date(Date.now() + hoursFromNow * 60 * 60 * 1000);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

async function capture(page, name) {
  const output = process.env.BROWSER_OUTPUT || path.join(require("node:os").tmpdir(), "krug-platform-captures");
  fs.mkdirSync(output, { recursive: true });
  await page.evaluate(async () => {
    const transition = document.activeViewTransition;
    if (transition) await transition.finished.catch(() => {});
    else await new Promise(resolve => setTimeout(resolve, 450));
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => image.decode().catch(() => {})));
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.screenshot({ path: path.join(output, name), fullPage: false });
}

async function waitReady(page, selector) {
  await page.waitForFunction(target => {
    const main = document.querySelector('#main');
    return main && !main.hasAttribute('aria-busy') && !main.inert && main.querySelector(target);
  }, selector);
  await page.locator(selector).waitFor({ state: 'visible' });
}

async function run() {
  const owner = await account('krug_platform_owner');
  const member = await account('krug_platform_member');
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const ownerContext = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'ru-RU', colorScheme: 'light' });
  const memberContext = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'ru-RU', colorScheme: 'dark', isMobile: true, hasTouch: true });
  const ownerPage = await ownerContext.newPage();
  const memberPage = await memberContext.newPage();
  for (const page of [ownerPage, memberPage]) page.on('pageerror', error => issues.push(error.message));
  try {
    await login(ownerPage, owner);
    await ownerPage.goto(base + '/app#settings');
    await waitReady(ownerPage, '#avatar-form');
    const avatarPng = await ownerPage.evaluate(() => { const canvas = document.createElement('canvas'); canvas.width = 96; canvas.height = 96; const ctx = canvas.getContext('2d'); ctx.fillStyle = '#dc6757'; ctx.fillRect(0, 0, 96, 96); ctx.fillStyle = '#263b3b'; ctx.beginPath(); ctx.arc(48, 48, 27, 0, Math.PI * 2); ctx.fill(); return canvas.toDataURL('image/png').split(',')[1]; });
    await ownerPage.locator('#avatar-form input[name=avatar]').setInputFiles({ name: 'synthetic-geometric-avatar.png', mimeType: 'image/png', buffer: Buffer.from(avatarPng, 'base64') });
    const avatarResponse = ownerPage.waitForResponse(response => response.url().endsWith('/me/avatar') && response.request().method() === 'PUT');
    await ownerPage.locator('#avatar-form button:not([type=button])').click();
    await avatarResponse;
    assert((await api('/me', { token: owner.token })).avatar_url, 'Profile avatar upload is exposed as a URL');
    const eventSlug = slug('ui-event');
    await ownerPage.goto(base + '/app#event-new');
    await waitReady(ownerPage, '[data-platform-form=event]');
    await ownerPage.locator('[data-platform-form=event] input[name=slug]').fill(eventSlug);
    await ownerPage.locator('[data-platform-form=event] input[name=title]').fill(`Preview event ${key}`);
    await ownerPage.locator('[data-platform-form=event] input[name=summary]').fill('Synthetic event for isolated UI checks.');
    await ownerPage.locator('[data-platform-form=event] textarea[name=description]').fill('This record and its cover exist only in the disposable preview database.');
    await ownerPage.locator('[data-platform-form=event] input[name=topics]').fill('preview, game development');
    await ownerPage.locator('[data-platform-form=event] input[name=skills]').fill('Godot');
    await ownerPage.locator('[data-platform-form=event] input[name=languages]').fill('English, Russian');
    await ownerPage.locator('[data-platform-form=event] select[name=type]').selectOption('game_jam');
    await ownerPage.locator('[data-platform-form=event] select[name=origin]').selectOption('external');
    await ownerPage.locator('[data-platform-form=event] input[name=source_name]').fill('Synthetic preview organizer');
    await ownerPage.locator('[data-platform-form=event] input[name=source_url]').fill(`https://example.invalid/preview-event-${key}`);
    await ownerPage.locator('[data-platform-form=event] input[name=timezone]').fill('Asia/Tashkent');
    await ownerPage.locator('[data-platform-form=event] input[name=starts_at]').fill(localDate(48));
    await ownerPage.locator('[data-platform-form=event] input[name=ends_at]').fill(localDate(52));
    await ownerPage.locator('[data-platform-form=event] select[name=format]').selectOption('online');
    await ownerPage.locator('[data-platform-form=event] select[name=visibility]').selectOption('public');
    await ownerPage.locator('[data-platform-form=event] input[name=cover]').setInputFiles(path.join(artDir, 'event.png'));
    const eventCreateResponse = ownerPage.waitForResponse(response => response.url().endsWith('/events') && response.request().method() === 'POST');
    await ownerPage.locator('[data-platform-form=event] button').click();
    const eventCreated = await eventCreateResponse;
    const eventCreateBody = await eventCreated.json().catch(() => null);
    assert(eventCreated.ok(), `Event creation failed (${eventCreated.status()}): ${JSON.stringify(eventCreateBody?.detail || eventCreateBody)}`);
    await ownerPage.waitForURL(`**/app#event/${eventSlug}`);
    await waitReady(ownerPage, '#event-engagement');
    let event = await api(`/events/${eventSlug}`, { token: owner.token });
    assert(event.cover_url, 'Owner cover upload is exposed as a URL');
    assert.equal(event.origin, 'external');
    assert.equal(event.type, 'game_jam');
    assert.equal(event.source_name, 'Synthetic preview organizer');
    assert.equal(event.source_url, `https://example.invalid/preview-event-${key}`);
    await ownerPage.getByRole('heading', { name: `Preview event ${key}` }).waitFor();
    await ownerPage.locator('#ui-theme').click();
    await ownerPage.locator('[data-theme-choice=light]').click();
    await capture(ownerPage, 'platform-event-desktop-light.png');
    await ownerPage.locator('#ui-theme').click();
    await ownerPage.locator('[data-theme-choice=dark]').click();
    await capture(ownerPage, 'platform-event-desktop-dark.png');
    await ownerPage.locator('#ui-theme').click();
    await ownerPage.locator('[data-theme-choice=light]').click();
    await ownerPage.setViewportSize({ width: 390, height: 844 });
    await capture(ownerPage, 'platform-event-mobile-light.png');
    await ownerPage.locator('#ui-theme').click();
    await ownerPage.locator('[data-theme-choice=dark]').click();
    await capture(ownerPage, 'platform-event-mobile-dark.png');
    await ownerPage.setViewportSize({ width: 1440, height: 1000 });
    await ownerPage.locator('#ui-theme').click();
    await ownerPage.locator('[data-theme-choice=light]').click();

    await ownerPage.locator('#event-engagement [name=saved]').check();
    await ownerPage.locator('#event-engagement [name=interested]').check();
    await ownerPage.locator('#event-engagement [name=interested_visible]').check();
    const eventSaveResponse = ownerPage.waitForResponse(response => response.url().includes(`/events/${eventSlug}/engagement`) && response.request().method() === 'PATCH');
    await ownerPage.locator('#event-engagement button:not([type=button])').click();
    await eventSaveResponse;
    await ownerPage.locator('#event-engagement [role=status]').filter({ hasText: 'Выбор сохранён.' }).waitFor();
    let eventEngagement = await api(`/events/${eventSlug}/engagement`, { token: owner.token });
    assert.deepEqual([eventEngagement.saved, eventEngagement.interested, eventEngagement.interested_visible], [true, true, true]);

    const teamSlug = slug('ui-team');
    await ownerPage.goto(base + `/app#team-new?event=${event.id}`);
    await waitReady(ownerPage, '[data-platform-form=team]');
    await ownerPage.locator('[data-platform-form=team] input[name=slug]').fill(teamSlug);
    await ownerPage.locator('[data-platform-form=team] input[name=title]').fill(`Preview team ${key}`);
    await ownerPage.locator('[data-platform-form=team] input[name=summary]').fill('A synthetic team connected to the preview event.');
    await ownerPage.locator('[data-platform-form=team] textarea[name=description]').fill('This team exists only in the disposable preview database.');
    await ownerPage.locator('[data-platform-form=team] input[name=topics]').fill('game development');
    await ownerPage.locator('[data-platform-form=team] input[name=skills]').fill('Godot, design');
    await ownerPage.locator('[data-platform-form=team] input[name=languages]').fill('English');
    await ownerPage.locator('[data-platform-form=team] input[name=commitment]').fill('3 hours weekly');
    await ownerPage.locator('[data-platform-form=team] select[name=event_id]').selectOption(String(event.id));
    await ownerPage.locator('[data-platform-form=team] select[name=status]').selectOption('recruiting');
    await ownerPage.locator('[data-platform-form=team] input[name=cover]').setInputFiles(path.join(artDir, 'team.png'));
    await ownerPage.locator('[data-platform-form=team] button:not([type=button])').click();
    await ownerPage.waitForURL(`**/app#team/${teamSlug}`);
    await waitReady(ownerPage, '#team-opening-form');
    let team = await api(`/teams/${teamSlug}`, { token: owner.token });
    assert.equal(team.event_id, event.id, 'Team keeps its event association');
    assert(team.cover_url, 'Team cover upload is exposed as a URL');
    await ownerPage.locator('#team-engagement [name=saved]').check();
    await ownerPage.locator('#team-engagement [name=interested]').check();
    await ownerPage.locator('#team-engagement [name=interested_visible]').check();
    const teamSaveResponse = ownerPage.waitForResponse(response => response.url().includes(`/teams/${teamSlug}/engagement`) && response.request().method() === 'PATCH');
    await ownerPage.locator('#team-engagement button:not([type=button])').click();
    await teamSaveResponse;
    const teamEngagement = await api(`/teams/${teamSlug}/engagement`, { token: owner.token });
    assert.deepEqual([teamEngagement.saved, teamEngagement.interested, teamEngagement.interested_visible], [true, true, true]);

    await ownerPage.locator('#team-opening-form input[name=title]').fill(`Preview opening ${key}`);
    await ownerPage.locator('#team-opening-form input[name=skills]').fill('Godot, design');
    await ownerPage.locator('#team-opening-form textarea[name=description]').fill('Join the prototype team.');
    const openingCreateResponse = ownerPage.waitForResponse(response => response.url().includes(`/teams/${teamSlug}/openings`) && response.request().method() === 'POST');
    await ownerPage.locator('#team-opening-form button:not([type=button])').click();
    const openingCreated = await openingCreateResponse;
    const openingCreateBody = await openingCreated.json().catch(() => null);
    assert(openingCreated.ok(), `Opening creation failed (${openingCreated.status()}): ${JSON.stringify(openingCreateBody?.detail || openingCreateBody)}`);
    const openings = await api(`/teams/${teamSlug}/openings?limit=24`, { token: owner.token });
    assert.equal(openings.items.length, 1, 'Owner can publish an opening');
    const openingId = openings.items[0].id;

    await login(memberPage, member);
    await memberPage.goto(base + `/app#team/${teamSlug}`);
    const applicationMessage = memberPage.locator(`[data-opening-apply="${openingId}"] textarea[name=message]`);
    await waitReady(memberPage, `[data-opening-apply="${openingId}"] textarea[name=message]`);
    await applicationMessage.fill('I can help with gameplay design.');
    assert.equal(await applicationMessage.inputValue(), 'I can help with gameplay design.', 'Application message was entered before submit');
    const applicationResponse = memberPage.waitForResponse(response => response.url().includes(`/team-openings/${openingId}/applications`) && response.request().method() === 'POST');
    await memberPage.locator(`[data-opening-apply="${openingId}"] button`).click();
    await applicationResponse;
    await memberPage.locator(`[data-opening-apply="${openingId}"] [role=status]`).filter({ hasText: 'Заявка отправлена владельцу команды.' }).waitFor();
    const ownApplications = await api('/team-applications?limit=24', { token: member.token });
    assert.equal(ownApplications.items.length, 1, 'Applicant can retrieve their team application');
    assert.equal(ownApplications.items[0].team_slug, teamSlug);

    await ownerPage.reload();
    await waitReady(ownerPage, '.team-owner-applications');
    const accept = ownerPage.locator('.team-owner-applications [data-application][data-status=accepted]');
    await accept.waitFor();
    const applicationId = await accept.getAttribute('data-application');
    const acceptResponse = ownerPage.waitForResponse(response => response.url().includes(`/team-applications/${applicationId}`) && response.request().method() === 'PATCH');
    await accept.click();
    await acceptResponse;
    assert.equal((await api(`/teams/${teamSlug}/applications?limit=24`, { token: owner.token })).items.find(item => String(item.id) === applicationId).status, 'accepted');
    const teamMembers = await api(`/teams/${teamSlug}/members?limit=24`, { token: owner.token });
    assert(teamMembers.items.some(item => item.user_id === member.id), 'Accepted applicant becomes a real team member');
    const transferDisclosure = 'details:has(#team-project-transfer) summary';
    await waitReady(ownerPage, transferDisclosure);
    await ownerPage.locator(transferDisclosure).click();
    await waitReady(ownerPage, '#team-project-transfer');
    await ownerPage.locator('#team-project-transfer').scrollIntoViewIfNeeded();
    const projectSlug = slug('ui-project');
    await ownerPage.locator('#team-project-transfer input[name=slug]').fill(projectSlug);
    await ownerPage.locator('#team-project-transfer input[name=title]').fill('Preview project ' + key);
    await ownerPage.locator('#team-project-transfer input[name=summary]').fill('A transferred team project in the disposable preview.');
    await ownerPage.locator('#team-project-transfer textarea[name=description]').fill('Project created by the real team transfer flow.');
    await ownerPage.locator('#team-project-transfer button:not([type=button])').click();
    await ownerPage.waitForURL('**/app#project/' + projectSlug);
    await waitReady(ownerPage, 'h1');
    const project = await api('/projects/' + projectSlug, { token: owner.token });
    assert.equal(project.member_count, 2, 'Team transfer retains both members');
    await ownerPage.goto(base + '/app#project-edit/' + projectSlug);
    await waitReady(ownerPage, '.project-editor');
    await ownerPage.locator('.project-editor input[name=cover]').setInputFiles(path.join(artDir, 'project.png'));
    await ownerPage.locator('.project-editor button:not([type=button])').click();
    await ownerPage.waitForURL('**/app#project/' + projectSlug);
    assert((await api('/projects/' + projectSlug, { token: owner.token })).cover_url, 'Transferred project cover upload works');

    const communitySlug = slug('ui-community');
    await ownerPage.goto(base + '/app#community-new');
    await waitReady(ownerPage, '[data-platform-form=community]');
    await ownerPage.locator('[data-platform-form=community] input[name=slug]').fill(communitySlug);
    await ownerPage.locator('[data-platform-form=community] input[name=title]').fill(`Preview community ${key}`);
    await ownerPage.locator('[data-platform-form=community] input[name=summary]').fill('A synthetic community for member-post verification.');
    await ownerPage.locator('[data-platform-form=community] textarea[name=description]').fill('This community exists only in the disposable preview database.');
    await ownerPage.locator('[data-platform-form=community] input[name=topics]').fill('game development');
    await ownerPage.locator('[data-platform-form=community] input[name=skills]').fill('Godot');
    await ownerPage.locator('[data-platform-form=community] input[name=languages]').fill('English');
    await ownerPage.locator('[data-platform-form=community] select[name=format]').selectOption('online');
    await ownerPage.locator('[data-platform-form=community] select[name=visibility]').selectOption('public');
    await ownerPage.locator('[data-platform-form=community] input[name=cover]').setInputFiles(path.join(artDir, 'team.png'));
    await ownerPage.locator('[data-platform-form=community] button:not([type=button])').click();
    await ownerPage.waitForURL(`**/app#community/${communitySlug}`);
    await waitReady(ownerPage, '#community-engagement');
    const community = await api(`/communities/${communitySlug}`, { token: owner.token });
    assert(community.cover_url, 'Community cover upload is exposed as a URL');
    for (const [kind, entitySlug] of [['project', projectSlug], ['team', teamSlug], ['event', eventSlug], ['community', communitySlug]]) {
      await assertDraftCover(kind, entitySlug, owner, member, ownerPage);
    }
    assert.deepEqual(await api(`/communities/${communitySlug}/membership`, { token: owner.token }), { is_member: true, is_owner: true });
    await ownerPage.locator('#community-engagement [name=saved]').check();
    const communitySaveResponse = ownerPage.waitForResponse(response => response.url().includes(`/communities/${communitySlug}/engagement`) && response.request().method() === 'PATCH');
    await ownerPage.locator('#community-engagement button:not([type=button])').click();
    await communitySaveResponse;
    assert.equal((await api(`/communities/${communitySlug}/engagement`, { token: owner.token })).saved, true);

    await memberPage.goto(base + `/app#community/${communitySlug}`);
    await waitReady(memberPage, '#community-membership');
    const membershipResponse = memberPage.waitForResponse(response => response.url().includes(`/communities/${communitySlug}/membership`) && response.request().method() === 'PUT');
    await memberPage.locator('#community-membership').click();
    await membershipResponse;
    await memberPage.waitForFunction(() => location.hash.startsWith('#community/'));
    assert.equal((await api(`/communities/${communitySlug}/membership`, { token: member.token })).is_member, true);
    await memberPage.goto(base + `/app#new?community_id=${community.id}&community=${communitySlug}`);
    await waitReady(memberPage, 'form textarea[name=content]');
    await memberPage.locator('form textarea[name=content]').fill(`Preview community post ${key}`);
    await memberPage.locator('form input[name=published]').check();
    const postResponse = memberPage.waitForResponse(response => response.url().endsWith('/posts') && response.request().method() === 'POST');
    await memberPage.locator('main form').filter({ has: memberPage.locator('textarea[name=content]') }).locator('button:not([type=button])').click();
    await postResponse;
    await memberPage.waitForURL('**/app#post/*');
    await waitReady(memberPage, '#discussion');
    const posts = await api(`/communities/${communitySlug}/posts?limit=24`, { token: owner.token });
    assert.equal(posts.items.length, 1, 'Community post appears in the member feed');
    assert.equal(posts.items[0].community_id, community.id);
    const postId = posts.items[0].id;
    await memberPage.locator('#discussion form textarea[name=content]').fill('Synthetic comment for community owner moderation.');
    const commentResponse = memberPage.waitForResponse(response => response.url().includes(`/posts/${postId}/comments`) && response.request().method() === 'POST');
    await memberPage.locator('#discussion form button:not([type=button])').click();
    await commentResponse;
    await ownerPage.goto(base + `/app#post/${postId}?community=${communitySlug}`);
    await waitReady(ownerPage, '[data-delete-comment]');
    const deleteComment = ownerPage.locator('[data-delete-comment]');
    await deleteComment.waitFor();
    const commentDeleteResponse = ownerPage.waitForResponse(response => response.url().includes(`/posts/${postId}/comments/`) && response.request().method() === 'DELETE');
    ownerPage.once('dialog', dialog => dialog.accept());
    await deleteComment.click();
    await commentDeleteResponse;
    assert.equal((await api(`/posts/${postId}/comments?limit=24`, { token: owner.token })).items.length, 0, 'Community owner can moderate member comments');

    await ownerPage.goto(base + `/app#community/${communitySlug}`);
    await waitReady(ownerPage, '[data-community-moderate]');
    await ownerPage.getByRole('status').filter({ hasText: 'Вы владелец сообщества и остаетесь его участником.' }).waitFor();
    assert.equal(await ownerPage.locator('#community-membership').count(), 0, 'Community owner is not offered the forbidden leave action');
    const moderate = ownerPage.locator('[data-community-moderate]');
    await moderate.waitFor();
    const moderationResponse = ownerPage.waitForResponse(response => response.url().includes('/posts/') && response.request().method() === 'DELETE');
    await moderate.click();
    await moderationResponse;
    assert.equal((await api(`/communities/${communitySlug}/posts?limit=24`, { token: owner.token })).items.length, 0, 'Community owner can moderate a member post');

    for (let index = 1; index <= 25; index++) await api('/posts', { token: member.token, method: 'POST', body: { community_id: community.id, content: `Pagination fixture ${key} ${index}`, is_published: true } });
    await ownerPage.reload();
    await waitReady(ownerPage, '#community-posts .post-card:first-child');
    await ownerPage.locator('#community-posts .post-card').nth(23).waitFor();
    assert.equal(await ownerPage.locator('#community-posts .post-card').count(), 24);
    const communityMore = ownerPage.locator('#community-posts > .load-more');
    await communityMore.waitFor();
    const communityPageResponse = ownerPage.waitForResponse(response => response.url().includes(`/communities/${communitySlug}/posts?limit=24&cursor=`) && response.request().method() === 'GET');
    await communityMore.click();
    await communityPageResponse;
    const lastPagePostText = `Pagination fixture ${key} 1`;
    const lastPagePost = ownerPage.locator('#community-posts .post-card').filter({ has: ownerPage.getByText(lastPagePostText, { exact: true }) });
    await lastPagePost.waitFor();
    assert.equal(await lastPagePost.count(), 1, 'Exact post text identifies one post on the appended page');
    assert.equal(await ownerPage.locator('#community-posts .post-card').count(), 25, 'Community posts expose records beyond the first page');
    const pagedPostId = await lastPagePost.locator('[data-community-moderate]').getAttribute('data-community-moderate');
    const pagedPostDelete = ownerPage.waitForResponse(response => response.url().endsWith(`/posts/${pagedPostId}`) && response.request().method() === 'DELETE');
    await lastPagePost.locator('[data-community-moderate]').click();
    await pagedPostDelete;
    assert.equal((await api(`/communities/${communitySlug}`, { token: owner.token })).published_posts_count, 24, 'Owner moderation is bound to posts added on later pages');

    await ownerPage.goto(base + '/app#saved');
    await ownerPage.getByRole('heading', { name: 'Сохранённое', exact: true }).waitFor();
    await waitReady(ownerPage, `#saved-results .platform-card[data-platform-kind=event][data-platform-slug="${eventSlug}"]`);
    await ownerPage.locator(`.platform-card[data-platform-kind=event][data-platform-slug="${eventSlug}"]`).waitFor();
    await ownerPage.locator(`.platform-card[data-platform-kind=team][data-platform-slug="${teamSlug}"]`).waitFor();
    await ownerPage.locator(`.platform-card[data-platform-kind=community][data-platform-slug="${communitySlug}"]`).waitFor();

    await ownerPage.goto(base + `/app#event/${eventSlug}`);
    await waitReady(ownerPage, `a[href="/app#teams?event_id=${event.id}"]`);
    await ownerPage.locator(`a[href="/app#teams?event_id=${event.id}"]`).click();
    await ownerPage.locator(`.platform-card[data-platform-slug="${teamSlug}"]`).waitFor();

    const disposableTeamSlug = slug('ui-delete-team');
    await api('/teams', { token: owner.token, method: 'POST', body: { slug: disposableTeamSlug, title: `Delete check team ${key}`, summary: 'Disposable owner delete check.', visibility: 'public', status: 'active' } });
    await ownerPage.goto(base + `/app#team/${disposableTeamSlug}`);
    await waitReady(ownerPage, '#team-delete');
    const teamDelete = ownerPage.locator('#team-delete');
    await teamDelete.waitFor();
    const teamDeleteResponse = ownerPage.waitForResponse(response => response.url().endsWith(`/teams/${disposableTeamSlug}`) && response.request().method() === 'DELETE');
    ownerPage.once('dialog', dialog => { assert(dialog.message().includes(`Delete check team ${key}`)); dialog.accept(); });
    await teamDelete.click();
    assert.equal((await teamDeleteResponse).status(), 204);
    await ownerPage.waitForURL('**/app#teams');
    await assertDeleted(`/teams/${disposableTeamSlug}`, owner.token, 'Disposable team');

    const disposableCommunitySlug = slug('ui-delete-community');
    await api('/communities', { token: owner.token, method: 'POST', body: { slug: disposableCommunitySlug, title: `Delete check community ${key}`, summary: 'Disposable owner delete check.', visibility: 'public' } });
    await ownerPage.goto(base + `/app#community/${disposableCommunitySlug}`);
    await waitReady(ownerPage, '#community-delete');
    const communityDelete = ownerPage.locator('#community-delete');
    await communityDelete.waitFor();
    const communityDeleteResponse = ownerPage.waitForResponse(response => response.url().endsWith(`/communities/${disposableCommunitySlug}`) && response.request().method() === 'DELETE');
    ownerPage.once('dialog', dialog => { assert(dialog.message().includes(`Delete check community ${key}`)); dialog.accept(); });
    await communityDelete.click();
    assert.equal((await communityDeleteResponse).status(), 204);
    await ownerPage.waitForURL('**/app#communities');
    await assertDeleted(`/communities/${disposableCommunitySlug}`, owner.token, 'Disposable community');

    const disposableEventSlug = slug('ui-delete-event');
    await api('/events', { token: owner.token, method: 'POST', body: { slug: disposableEventSlug, title: `Delete check event ${key}`, summary: 'Disposable owner delete check.', starts_at: new Date(Date.now() + 7 * 86400000).toISOString(), timezone: 'UTC', visibility: 'public' } });
    await ownerPage.goto(base + `/app#event/${disposableEventSlug}`);
    await waitReady(ownerPage, '#event-delete');
    const eventDelete = ownerPage.locator('#event-delete');
    await eventDelete.waitFor();
    const eventDeleteResponse = ownerPage.waitForResponse(response => response.url().endsWith(`/events/${disposableEventSlug}`) && response.request().method() === 'DELETE');
    ownerPage.once('dialog', dialog => { assert(dialog.message().includes(`Delete check event ${key}`)); dialog.accept(); });
    await eventDelete.click();
    assert.equal((await eventDeleteResponse).status(), 204);
    await ownerPage.waitForURL('**/app#explore?kind=events');
    await assertDeleted(`/events/${disposableEventSlug}`, owner.token, 'Disposable event');
    assert.deepEqual(issues, [], `Browser errors: ${issues.join('; ')}`);
    console.log(`Platform flows passed in isolated preview. owner=${owner.username} member=${member.username} event=${eventSlug} team=${teamSlug} community=${communitySlug}`);
  } catch (error) {
    for (const [label, page] of [['owner', ownerPage], ['member', memberPage]]) {
      try { await capture(page, `platform-failure-${label}.png`); }
      catch (captureError) { issues.push(`${label} capture failed: ${captureError.message}`); }
    }
    const pageStates = await Promise.all([ownerPage, memberPage].map(async page => ({ url: page.url(), title: await page.title().catch(() => '') })));
    console.error(JSON.stringify({ failure: error.stack || error.message, pages: pageStates, issues }, null, 2));
    throw error;
  } finally {
    await browser.close();
  }
}

run().catch(error => { console.error(error); process.exitCode = 1; });
