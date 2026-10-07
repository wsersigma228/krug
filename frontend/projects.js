"use strict";
// Discovery and project screens share the existing account, pagination and post UI.
function projectLabel(value) {
  return t({ native: "В Круге", external: "Внешний проект", active: "Активен", paused: "На паузе", completed: "Завершён", archived: "В архиве", stale: "Возможно устарел", idea: "Идея", prototype: "Прототип", building: "В разработке", shipped: "Выпущен", unknown: "Не указано", open: "Набор открыт", closed: "Набор закрыт", pending: "Ожидает", accepted: "Принято", rejected: "Отклонено", withdrawn: "Отозвано" }[value] || value);
}
function projectPath(project) {
  return "/project/" + encodeURIComponent(project.slug);
}
function projectTags(project) {
  const tags = project.tags.map(value => ({ value, filter: "tag" }));
  const skills = project.skills.filter(value => !project.tags.includes(value)).map(value => ({ value, filter: "skill" }));
  return [...tags, ...skills].slice(0, 8).map(({ value, filter }) => html`<a class="project-tag" href="/app#explore?kind=projects&${filter}=${encodeURIComponent(value)}">${esc(value)}</a>`).join("");
}
function projectCard(project) {
  const native = project.origin === "native";
  const canJoin = native || Boolean(project.owner_id);
  const hasCounts = [project.interested_count, project.member_count, project.open_roles_count, project.published_updates_count].every(Number.isInteger);
  return html`<article class="project-card">
    <div class="project-card-meta"><span>${canJoin ? t("Проект Круга") : project.owner_id ? t("Владелец в Круге") : t("Внешний проект")}</span><span class="project-status" data-status="${esc(project.status)}">${projectLabel(project.status)}</span></div>
    <h2><a href="/app#project/${esc(project.slug)}">${esc(project.title)}</a></h2>
    <p class="project-summary">${esc(project.summary)}</p>
    <div class="project-tags">${projectTags(project)}</div>
    ${hasCounts ? html`<div class="project-card-counts"><span>${project.interested_count} ${t("заинтересованы")}</span><span>${project.member_count} ${t("участников")}</span><span>${project.open_roles_count} ${t("открытых ролей")}</span><span>${project.published_updates_count} ${t("обновлений")}</span></div>` : ""}${project.origin === "external" && !project.owner_id ? html`<p class="hint">${t("Внешняя ссылка не показывает, ищут ли создатели проекта участников.")}</p>` : ""}
    <div class="project-card-bottom"><span class="hint">${projectLabel(project.stage)}</span><a class="project-open" href="/app#project/${esc(project.slug)}" aria-label="${t("Открыть проект")} ${esc(project.title)}">${native ? t("Подробнее и присоединиться") : t("Посмотреть и создать похожий проект")}${icon("arrow")}</a></div>
  </article>`;
}
function personCard(person) {
  const name = person.display_name || person.username;
  const intent = { looking_for_teammates:"Ищу участников в проект", looking_for_project:"Ищу проект", open_to_collaboration:"Открыт к сотрудничеству", interested_in_event:"Интересуюсь мероприятиями" }[person.intent_kind];
  return html`<article class="discovery-person"><a class="avatar" href="/app#profile/${person.id}" aria-label="${t("Профиль")} ${esc(name)}">${esc(name[0]?.toUpperCase())}</a><div class="discovery-person-body"><div class="project-card-meta"><a class="author" href="/app#profile/${person.id}">${esc(name)}</a><span>@${esc(person.username)}</span></div>${intent ? html`<p class="project-card-meta">${t(intent)}</p>` : ""}<p>${esc(person.intent_text || person.bio || "")}</p><div class="project-tags">${(person.skills || []).slice(0, 5).map(skill => html`<span class="project-tag">${esc(skill)}</span>`).join("")}</div>${person.wanted_skills?.length ? html`<p class="hint">${t("Ищет навыки")}: ${person.wanted_skills.slice(0, 4).map(esc).join(", ")}</p>` : ""}<p class="hint">${[person.timezone, person.commitment].filter(Boolean).map(esc).join(" · ")}</p></div><a class="project-open" href="/app#profile/${person.id}">${t("Профиль")}${icon("arrow")}</a></article>`;
}
function openingCard(opening) {
  return html`<article class="discovery-opening"><div class="project-card-meta"><span>${t("Открытая роль")}</span><span>${esc(opening.commitment || "")}</span></div><h2><a href="/app#project/${esc(opening.project.slug)}">${esc(opening.role)}</a></h2><p class="project-summary">${esc(opening.description || opening.project.summary)}</p><p class="hint">${t("Проект")}: ${esc(opening.project.title)}${opening.timezone ? " · " + esc(opening.timezone) : ""}</p><div class="project-tags">${(opening.skills || []).slice(0, 5).map(skill => html`<span class="project-tag">${esc(skill)}</span>`).join("")}</div><div class="project-card-bottom"><a class="project-open" href="/app#project/${esc(opening.project.slug)}">${t("Посмотреть и откликнуться")}${icon("arrow")}</a></div></article>`;
}
function applicationLabel(value) {
  return projectLabel(value);
}
async function discoveryScreen(root, query, stamp) {
  const kind = ["all", "projects", "people", "openings"].includes(query.get("kind")) ? query.get("kind") : "all";
  const compactIntro = kind !== "all" || query.has("search");
  const mobileSearch = matchMedia("(max-width: 850px)");
  root.innerHTML = html`<section class="discovery-intro${compactIntro ? " discovery-intro-compact" : ""}"><div><h1>Найдите людей и проекты для совместной работы.</h1><p class="intro">Ищите команду или присоединяйтесь к открытой роли.</p></div><div class="discovery-actions"><a class="button" href="/app#project-new">${t("Начать проект")}</a><a class="text-button" href="/app#external-submit">${t("Предложить внешний проект")}</a><a class="text-button" href="/project/krug">${t("Как строится Круг")} ${icon("arrow")}</a></div></section>
    <form class="discovery-search" role="search"><div class="discovery-search-main"><label class="field"><span>Поиск по Кругу</span><input name="search" maxlength="100" placeholder="Python, дизайн, совместный проект…" value="${esc(query.get("search") || "")}"></label><button>${icon("explore")} Найти</button></div></form>
    <div class="discovery-workspace"><aside class="discovery-sidebar"><form class="discovery-filter-form"><input type="hidden" name="search" value="${esc(query.get("search") || "")}">
    <details class="discovery-filters" ${!mobileSearch.matches || ["tag", "skill", "source", "status", "active", "intent_kind"].some(key => query.has(key)) ? "open" : ""}><summary>${t("Фильтры")}</summary><div class="filter-fields">
    ${input("skill", t("Навык"), "text", 'maxlength="50"')}
    <div data-project-filter ${kind === "projects" ? "" : "hidden"}>${input("tag", t("Тег"), "text", 'maxlength="50"')}${input("source", t("Источник"), "text", 'maxlength="40"')}<label class="field">${t("Статус")}<select name="status"><option value="">${t("Все статусы")}</option>${["active", "paused", "completed", "archived", "stale"].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label><label class="checkbox"><input name="active" type="checkbox">${t("Только активные")}</label></div>
    <label class="field" data-people-filter ${kind === "people" ? "" : "hidden"}>${t("Намерение")}<select name="intent_kind"><option value="">${t("Любое намерение")}</option><option value="looking_for_teammates">${t("Ищу участников в проект")}</option><option value="looking_for_project">${t("Ищу проект")}</option><option value="open_to_collaboration">${t("Открыт к сотрудничеству")}</option><option value="interested_in_event">${t("Интересуюсь мероприятиями")}</option></select></label><button type="submit" class="secondary">${t("Применить фильтры")}</button><a class="text-button" href="/app#explore?kind=${kind}${query.get("search") ? "&search=" + encodeURIComponent(query.get("search")) : ""}">${t("Сбросить фильтры")}</a></div></details></form></aside>
    <section class="discovery-results"><nav class="discovery-tabs" aria-label="${t("Тип результатов")}">${[["all", "Всё"], ["projects", "Проекты"], ["people", "Люди"], ["openings", "Открытые роли"]].map(([value,label]) => html`<a href="/app#explore?kind=${value}${query.get("search") ? "&search=" + encodeURIComponent(query.get("search")) : ""}" class="${kind === value ? "active" : ""}" ${kind === value ? 'aria-current="page"' : ""}>${t(label)}</a>`).join("")}</nav><div class="discovery-results-heading"><h2>${t({all:"Все результаты",projects:"Проекты",people:"Люди",openings:"Открытые роли"}[kind])}</h2></div><div id="discovery-results"></div></section></div>`;
  const filterDisclosure = root.querySelector(".discovery-filters");
  let manualDisclosure = false;
  filterDisclosure.querySelector("summary").addEventListener("click", () => { manualDisclosure = true; });
  mobileSearch.addEventListener("change", event => { if (!manualDisclosure && !["tag", "skill", "source", "status", "active", "intent_kind"].some(key => query.has(key))) filterDisclosure.open = !event.matches; });
  const searchForm = root.querySelector(".discovery-search");
  bindForm(searchForm, async data => {
    const params = new URLSearchParams(query);
    const value = data.get("search")?.trim();
    if (value) params.set("search", value); else params.delete("search");
    params.set("kind", kind);
    go("explore?" + params);
  });
  const form = root.querySelector(".discovery-filter-form");
  ["tag", "skill", "source", "status", "intent_kind"].forEach(key => { if (form.elements[key]) form.elements[key].value = query.get(key) || ""; });
  if (form.elements.active) form.elements.active.checked = query.get("active") === "true";
  bindForm(form, async data => {
    const params = new URLSearchParams();
    const keys = kind === "projects" ? ["search", "tag", "skill", "source", "status"] : kind === "people" ? ["search", "skill", "intent_kind"] : ["search", "skill"];
    keys.forEach(key => { const value = data.get(key)?.trim(); if (value) params.set(key, value); });
    if (kind === "projects" && data.has("active")) params.set("active", "true");
    params.set("kind", kind);
    go("explore?" + params);
  });
  const params = new URLSearchParams();
  ["search", "tag", "skill", "source", "status", "active"].forEach(key => { if (query.has(key)) params.set(key, query.get(key)); });
  const peopleParams = new URLSearchParams({ search: query.get("search") || "" });
  const openingParams = new URLSearchParams({ search: query.get("search") || "" });
  if (query.has("skill")) { peopleParams.set("skill", query.get("skill")); openingParams.set("skill", query.get("skill")); }
  if (query.has("intent_kind")) peopleParams.set("intent_kind", query.get("intent_kind"));
  const people = "/people?" + peopleParams;
  const openings = "/openings?" + openingParams;
  const blank = empty(t("Пока нет результатов"), t("Измените запрос или вернитесь позже: здесь показываются только настоящие профили, проекты и открытые роли."));
  if (kind === "projects") await paged(root.querySelector("#discovery-results"), "/discovery?" + params, projectCard, stamp, blank);
  else if (kind === "people") await paged(root.querySelector("#discovery-results"), people, personCard, stamp, blank);
  else if (kind === "openings") await paged(root.querySelector("#discovery-results"), openings, openingCard, stamp, blank);
  else {
    const target = root.querySelector("#discovery-results");
    const nativeParams = new URLSearchParams(params); nativeParams.set("source", "native");
    const externalParams = new URLSearchParams(params); externalParams.set("source", "external");
    const sources = [
      ["Проекты Круга", "/discovery?" + nativeParams, projectCard],
      ["Открытые роли", openings, openingCard],
      ["Люди", people, personCard],
      ["Внешние проекты", "/discovery?" + externalParams, projectCard],
    ];
    const pages = await Promise.all(sources.map(async ([label, path, render]) => {
      try { return { label, items: (await api(path + (path.includes("?") ? "&" : "?") + "limit=3")).items.map(render) }; }
      catch (error) { return { label, error: errorText(error) }; }
    }));
    if (stamp !== generation) return;
    const cards = [];
    for (let index = 0; index < Math.max(...pages.map(page => page.items?.length || 0)); index++) {
      for (const page of pages) if (page.items?.[index]) cards.push(page.items[index]);
    }
    const errors = pages.filter(page => page.error).map(page => `<p class="error" role="alert">${t(page.label)}: ${esc(page.error)}</p>`).join("");
    target.innerHTML = `${cards.length ? `<div class="project-grid">${cards.join("")}</div>` : errors ? "" : blank}${errors}`;
  }
}
async function projectListScreen(root, saved, stamp, query = new URLSearchParams()) {
  const following = saved && query.get("following") === "true";
  root.innerHTML = heading("", saved ? (following ? t("Подписки на проекты") : t("Сохранённые проекты")) : t("Мои проекты"), saved ? t("Вернитесь к тому, что вас заинтересовало.") : t("Ваши проекты и черновики. Публичные страницы можно отправить кому угодно.")) +
    (saved ? html`<div class="tabs"><a href="/app#saved" class="${following ? "" : "active"}">Сохранённое</a><a href="/app#saved?following=true" class="${following ? "active" : ""}">Подписки на проекты</a></div>` : html`<a class="button" href="/app#project-new">${icon("plus")} Создать проект</a><hr class="divider">`);
  await paged(root, saved ? (following ? "/me/followed-projects" : "/me/saved-projects") : "/me/projects", projectCard, stamp,
    empty(saved ? (following ? t("Пока нет подписок на проекты") : t("Пока ничего не сохранено")) : t("Ваш первый проект начинается здесь"), saved ? (following ? t("Подпишитесь на проект, чтобы держать его в своём списке.") : t("Откройте проект и сохраните его, чтобы вернуться позже.")) : t("Расскажите, что вы строите. Начать можно с черновика."), html`<a class="button" href="/app#${saved ? "explore" : "project-new"}">${saved ? t("Исследовать проекты") : t("Создать проект")}</a>`));
}
async function projectScreen(root, slug, stamp) {
  const path = "/projects/" + encodeURIComponent(slug);
  const project = await api(path);
  if (stamp !== generation) return;
  const own = me?.id === project.owner_id;
  root.innerHTML = html`<a class="back" href="/app#explore">${icon("arrow")} ${t("Все результаты")}</a>
    <article class="project-detail"><div class="project-detail-main"><div class="project-card-meta"><span>${esc(project.source_name || projectLabel(project.origin))}</span><span class="project-status" data-status="${esc(project.status)}">${projectLabel(project.status)}</span>${project.visibility === "draft" ? html`<span class="badge">Черновик</span>` : ""}</div><h1>${esc(project.title)}</h1><p class="project-lead">${esc(project.summary)}</p><div class="project-tags">${projectTags(project)}</div>${[project.interested_count, project.member_count, project.open_roles_count, project.published_updates_count].every(Number.isInteger) ? html`<div class="project-card-counts"><span>${project.interested_count} ${t("заинтересованы")}</span><span>${project.member_count} ${t("участников")}</span><span>${project.open_roles_count} ${t("открытых ролей")}</span><span>${project.published_updates_count} ${t("обновлений")}</span></div>` : ""}
    ${project.description ? html`<div class="project-description">${esc(project.description)}</div>` : ""}
    <dl class="project-facts"><div><dt>Этап</dt><dd>${projectLabel(project.stage)}</dd></div><div><dt>Последнее обновление</dt><dd>${project.last_activity_at ? date(project.last_activity_at) : projectLabel("unknown")}</dd></div>${project.last_verified_at ? html`<div><dt>Проверен</dt><dd>${date(project.last_verified_at)}</dd></div>` : ""}${project.recruitment_status ? html`<div><dt>Набор участников</dt><dd>${projectLabel(project.recruitment_status)}</dd></div>` : ""}${project.commitment ? html`<div><dt>Время на участие</dt><dd>${esc(project.commitment)}</dd></div>` : ""}${project.experience_level ? html`<div><dt>Опыт участников</dt><dd>${esc(project.experience_level)}</dd></div>` : ""}</dl>
    ${project.origin === "external" ? html`<p class="hint">${project.owner_id ? t("У этого проекта есть подтверждённый владелец в Круге. Внешняя ссылка остаётся первоисточником.") : t("Внешний источник не связан с участниками Круга. Данные об активности не означают, что автор набирает команду.")}</p>` : ""}
    <div class="toolbar">${project.source_url ? html`<a class="button secondary" href="${esc(project.source_url)}" target="_blank" rel="noopener noreferrer">${t("Открыть внешний сайт")} (${esc(new URL(project.source_url).hostname)}) ${icon("arrow")}</a>` : ""}${project.visibility === "public" ? html`<a class="button secondary" href="${projectPath(project)}">${t("Публичная ссылка")}</a>` : ""}${own ? html`<a class="text-button" href="/app#project-edit/${esc(project.slug)}">${t("Редактировать проект")}</a><a class="button" href="/app#new?project=${project.id}">${icon("plus")} ${t("Написать обновление")}</a>` : ""}</div></div>
    <aside class="project-engagement" aria-label="${t("Ваш интерес к проекту")}"><h2>${own ? t("Ваш проект") : t("Присоединяйтесь")}</h2><p class="hint">${project.origin === "external" && !project.owner_id ? t("Источник внешний и не связан с участниками Круга. Начните свой проект по мотивам или запросите подтверждение владения.") : t("Отметьте интерес или откликнитесь на открытую роль. Решение о заявке принимает владелец проекта.")}</p><div id="engagement">${session ? html`<p class="hint" role="status">Загрузка…</p>` : html`<a class="button" href="/app#login?next=${encodeURIComponent("project/" + slug)}">${t("Войти, чтобы присоединиться")}</a><p class="hint">${t("Проект и обновления доступны без входа.")}</p>`}</div><a class="text-button" href="/app#project-interested/${esc(project.slug)}">${t("Открытые профили интереса")} ${icon("arrow")}</a>${project.origin === "external" && !project.owner_id ? html`<div class="toolbar"><a class="button secondary" href="/app#project-new?inspired=${esc(project.slug)}">${t("Создать похожий проект")}</a>${session ? html`<a class="text-button" href="/app#project-claim/${esc(project.slug)}">${t("Я представляю этот проект")}</a>` : ""}</div>` : ""}</aside></article>
    <section class="project-community"><section><div class="discovery-results-heading"><h2>${t("Участники")}</h2>${Number.isInteger(project.member_count) ? html`<span class="hint">${project.member_count}</span>` : ""}</div><div id="project-members"></div></section><section class="project-roles"><div class="discovery-results-heading"><h2>${t("Открытые роли")}</h2>${own && Number.isInteger(project.open_roles_count) ? html`<span class="hint">${project.open_roles_count}</span>` : ""}</div><div id="project-openings"></div>${own ? html`<details class="project-role-editor"><summary>${t("Добавить роль")}</summary><form class="form" id="opening-create">${input("role", t("Название роли"), "text", 'required maxlength="100"')}${input("skills", t("Навыки через запятую"), "text", 'maxlength="1000"')}${input("commitment", t("Время на участие"), "text", 'maxlength="100"')}${input("timezone", t("Часовой пояс роли"), "text", 'maxlength="100"')}${input("experience_level", t("Опыт для роли"), "text", 'maxlength="50"')}<label class="field">${t("Описание роли")}<textarea name="description" maxlength="5000"></textarea></label><button>${t("Опубликовать роль")}</button></form></details><form class="form project-contact-form" id="owner-contact">${input("owner_contact_url", t("Контакт для принятых участников"), "url", 'maxlength="2048" placeholder="https://…"')}<p class="hint">${t("Ссылка показывается только участникам после принятия заявки.")}</p><button class="secondary">${t("Сохранить приватный контакт")}</button><span class="hint" role="status"></span></form><section class="project-applications"><h3>${t("Заявки")}</h3><div id="project-applications"></div></section>` : ""}</section></section>
    <section class="project-updates"><div class="discovery-results-heading"><h2>Обновления проекта</h2>${own ? html`<a class="text-button" href="/app#new?project=${project.id}">Написать обновление</a>` : ""}</div><div id="project-updates"></div></section>`;
  // Engagement failures must not hide a project's public description or updates.
  if (session) {
    try {
      const state = await api(path + "/engagement");
      if (stamp === generation) bindProjectEngagement(root.querySelector("#engagement"), path, state);
    } catch (error) {
      if (stamp === generation) root.querySelector("#engagement").textContent = errorText(error);
    }
  }
  if (stamp !== generation) return;
  await projectCollaboration(root, project, own, stamp);
  await paged(root.querySelector("#project-updates"), path + "/updates", post => post.is_published && project.visibility === "public" ? postCard(post).replaceAll("/app#post/" + post.id, projectPath(project) + "/updates/" + post.id) : postCard(post), stamp,
    empty(t("Первое обновление ещё впереди"), t("Здесь появятся новости о том, что меняется в проекте.")));
}
function bindProjectEngagement(root, path, state) {
  root.innerHTML = html`<form class="form engagement-form"><label class="checkbox"><input type="checkbox" name="saved" ${state.saved ? "checked" : ""}>Сохранить проект</label><label class="checkbox"><input type="checkbox" name="following" ${state.following ? "checked" : ""}>Подписаться на проект</label><label class="checkbox"><input type="checkbox" name="interested" ${state.interested ? "checked" : ""}>Мне интересно</label><label class="checkbox interest-visibility"><input type="checkbox" name="interested_visible" ${state.interested_visible ? "checked" : ""} ${state.interested ? "" : "disabled"}>Показать мой профиль другим заинтересованным</label><span class="hint">Интерес приватный, пока вы сами не включите видимость для этого проекта.</span><button class="secondary">Сохранить выбор</button><span class="hint" role="status" id="engagement-status"></span></form>`;
  const form = root.querySelector("form");
  form.elements.interested.addEventListener("change", () => {
    form.elements.interested_visible.disabled = !form.elements.interested.checked;
    if (!form.elements.interested.checked) form.elements.interested_visible.checked = false;
  });
  bindForm(form, async data => {
    const body = Object.fromEntries(["saved", "following", "interested", "interested_visible"].map(key => [key, data.has(key)]));
    await api(path + "/engagement", { method: "PATCH", body });
    if (root.isConnected) form.querySelector("#engagement-status").textContent = t("Выбор сохранён.");
  });
}
async function projectCollaboration(root, project, own, stamp) {
  const members = root.querySelector("#project-members");
  try {
    const page = await api("/projects/" + encodeURIComponent(project.slug) + "/members");
    if (stamp !== generation) return;
    const people = page.items || page;
    const isMember = Boolean(me && people.some(person => (person.user_id ?? person.id) === me.id));
    if (project.origin === "native" && (own || isMember)) root.querySelector("#project-updates").previousElementSibling.insertAdjacentHTML("beforeend", html`<a class="button" href="/app#new?project=${project.id}">${icon("plus")} ${t("Написать обновление")}</a>`);
    members.innerHTML = people.length ? people.map(person => html`<a class="project-member" href="/app#profile/${person.user_id ?? person.id}"><span class="avatar">${esc((person.display_name || person.username)[0].toUpperCase())}</span><span><strong>${esc(person.display_name || person.username)}</strong><small>${esc(person.role)}</small></span></a>`).join("") : html`<p class="hint">${project.origin === "external" && !project.owner_id ? t("Внешняя команда здесь не представлена. Вы можете начать отдельный проект по мотивам.") : t("У проекта пока нет других участников.")}</p>`;
  } catch (error) { if (stamp === generation) members.innerHTML = `<p class="error" role="alert">${esc(errorText(error))}</p>`; }
  if (project.origin !== "native" && !project.owner_id) return;
  const path = "/projects/" + encodeURIComponent(project.slug);
  try {
    const page = await api(path + "/openings?limit=24");
    if (stamp !== generation) return;
    const container = root.querySelector("#project-openings");
    const priorApplications = session && !own ? await api("/me/applications") : [];
    if (!page.items.length) container.innerHTML = `<p class="hint">${t("Сейчас нет открытых ролей.")}</p>`;
    else container.innerHTML = page.items.map(opening => html`<article class="project-opening"><div><h3>${esc(opening.role || opening.title)}</h3><p class="project-summary">${esc(opening.description || "")}</p><div class="project-tags">${(opening.skills || []).map(skill => `<span class="project-tag">${esc(skill)}</span>`).join("")}</div><p class="hint">${[opening.commitment, opening.timezone, opening.experience_level].filter(Boolean).map(esc).join(" · ")}</p></div>${own ? html`<button class="secondary" data-toggle-role="${opening.id}" data-next="${opening.status === "open" ? "closed" : "open"}">${t(opening.status === "open" ? "Закрыть роль" : "Открыть роль")}</button>` : session ? (priorApplications.some(application => application.opening_id === opening.id) ? html`<p class="hint">${t("Заявка")}: ${applicationLabel(priorApplications.find(application => application.opening_id === opening.id).status)}</p>` : html`<form class="form apply-form" data-apply="${opening.id}"><label class="field">${t("Почему вам интересна эта роль?")}<textarea name="message" required maxlength="5000"></textarea></label><label class="field">${t("Ссылка для связи после принятия, необязательно")}<input name="applicant_contact_url" type="url" maxlength="2048" placeholder="https://…"></label><button>${t("Отправить заявку")}</button></form>`) : html`<a class="button" href="/app#login?next=${encodeURIComponent("project/" + project.slug)}">${t("Войти и откликнуться")}</a>`}</article>`).join("");
    root.querySelectorAll("[data-toggle-role]").forEach(button => actionButton(button, async () => { const opening = page.items.find(item => item.id === Number(button.dataset.toggleRole)); await api(path + "/openings/" + opening.id, { method:"PATCH", body:{ title:opening.title,role:opening.role,skills:opening.skills,commitment:opening.commitment,timezone:opening.timezone,experience_level:opening.experience_level,description:opening.description,status:button.dataset.next} }); go("project/" + project.slug); }));
    root.querySelectorAll("[data-apply]").forEach(form => bindForm(form, async data => { const body = { message:data.get("message"), applicant_contact_url:data.get("applicant_contact_url").trim() || null }; await api(path + "/openings/" + form.dataset.apply + "/applications", {method:"POST",body}); toast(t("Заявка отправлена. Контакт станет виден только после принятия.")); form.innerHTML = `<p class="success" role="status">${t("Заявка отправлена владельцу проекта.")}</p>`; }));
  } catch (error) { if (stamp === generation) root.querySelector("#project-openings").innerHTML = `<p class="error" role="alert">${esc(errorText(error))}</p>`; }
  if (!own || !session) return;
  const roleForm = root.querySelector("#opening-create");
  bindForm(roleForm, async data => { await api(path + "/openings", { method:"POST", body:{ title:data.get("role"), role:data.get("role"), skills:data.get("skills").split(",").map(value=>value.trim()).filter(Boolean), commitment:data.get("commitment").trim() || null, timezone:data.get("timezone").trim() || null, experience_level:data.get("experience_level").trim() || null, description:data.get("description") } }); toast(t("Роль опубликована.")); go("project/" + project.slug); });
  const contactForm = root.querySelector("#owner-contact");
  try { const settings = await api(path + "/contact-settings"); contactForm.elements.owner_contact_url.value = settings.owner_contact_url || ""; } catch (error) { contactForm.querySelector('[role="status"]').textContent = errorText(error); }
  bindForm(contactForm, async data => { await api(path + "/contact-settings", {method:"PUT",body:{owner_contact_url:data.get("owner_contact_url").trim() || null}}); contactForm.querySelector('[role="status"]').textContent = t("Приватный контакт сохранён."); });
  try {
    const applications = await api(path + "/applications");
    if (stamp !== generation) return;
    const target = root.querySelector("#project-applications");
    target.innerHTML = applications.length ? applications.map(application => html`<article class="project-application"><div class="project-card-meta"><a class="author" href="/app#profile/${application.applicant_id}">${esc(application.applicant_username)}</a><span>${applicationLabel(application.status)}</span></div><p>${esc(application.message)}</p>${application.status === "accepted" && application.applicant_contact_url ? html`<a class="text-button" href="${esc(application.applicant_contact_url)}" target="_blank" rel="noopener noreferrer">${t("Открыть контакт участника")}</a>` : ""}${application.status === "pending" ? html`<div class="toolbar"><button data-decision="accepted" data-application="${application.id}">${t("Принять")}</button><button class="secondary" data-decision="rejected" data-application="${application.id}">${t("Отклонить")}</button></div>` : ""}</article>`).join("") : `<p class="hint">${t("Новых заявок пока нет.")}</p>`;
    target.querySelectorAll("[data-decision]").forEach(button => actionButton(button, async () => { await api(path + "/applications/" + button.dataset.application, {method:"PATCH",body:{status:button.dataset.decision}}); toast(t(button.dataset.decision === "accepted" ? "Участник принят." : "Заявка отклонена.")); go("project/" + project.slug); }));
  } catch (error) { if (stamp === generation) root.querySelector("#project-applications").innerHTML = `<p class="error" role="alert">${esc(errorText(error))}</p>`; }
}
async function projectInterestedScreen(root, slug, stamp) {
  const project = await api("/projects/" + encodeURIComponent(slug));
  if (stamp !== generation) return;
  root.innerHTML = html`<a class="back" href="${projectPath(project)}">${esc(project.title)}</a>` + heading("", t("Кому интересен проект"), t("Здесь только люди, которые сами разрешили показать профиль для этого проекта."));
  await paged(root, "/projects/" + encodeURIComponent(slug) + "/interested", user => html`<article class="interested-person"><a class="avatar" href="/app#profile/${user.id}">${esc((user.display_name || user.username)[0].toUpperCase())}</a><div><a class="author" href="/app#profile/${user.id}">${esc(user.display_name || user.username)}</a><p class="hint">@${esc(user.username)}</p><p>${esc(user.bio)}</p></div></article>`, stamp,
    empty(t("Пока нет открытых профилей"), t("Интерес может оставаться приватным. Это не означает, что проект никому не интересен.")));
}
async function projectEditorScreen(root, slug, stamp, query = new URLSearchParams()) {
  const project = slug ? await api("/projects/" + encodeURIComponent(slug)) : null;
  const inspirationSlug = !project && /^[a-z0-9-]+$/.test(query.get("inspired") || "") ? query.get("inspired") : null;
  const inspiration = inspirationSlug ? await api("/projects/" + encodeURIComponent(inspirationSlug)) : null;
  if (stamp !== generation) return;
  root.innerHTML = heading("", project ? t("Редактировать проект") : t("Создать проект"), t("Что вы строите и кому это может быть интересно? Черновик виден только вам.")) + (inspiration ? html`<p class="project-editor-context">${t("Вы создаёте новый проект в Круге, связанный только вашей идеей с внешним источником:")} <a href="${projectPath(inspiration)}">${esc(inspiration.title)}</a></p>` : "") + html`<form class="form project-editor">
    ${input("title", t("Название проекта"), "text", 'required maxlength="200"')}${project ? "" : input("slug", t("Адрес проекта"), "text", 'required minlength="3" maxlength="100" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="my-project"')}
    ${project ? "" : html`<span class="hint">Латинские буквы, цифры и дефисы. Адрес нельзя изменить после создания.</span>`}
    ${input("summary", t("Краткое описание"), "text", 'required maxlength="500"')}
    <label class="field">${t("Подробнее о проекте")}<textarea name="description" maxlength="20000"></textarea></label>
    <div class="project-editor-fields"><label class="field">Статус<select name="status">${[...new Set(["active", "paused", "completed", "archived", ...(project?.status ? [project.status] : [])])].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label><label class="field">Этап<select name="stage">${[...new Set(["idea", "prototype", "building", "shipped", ...(project?.stage ? [project.stage] : [])])].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label></div>
    ${input("tags", t("Теги через запятую"), "text", 'maxlength="1000" placeholder="gamedev, open-source"')}${input("skills", t("Технологии и навыки через запятую"), "text", 'maxlength="1000" placeholder="Python, Godot"')}
    ${project?.origin === "external" ? html`<p class="hint">${t("Первоисточник проекта")} <a href="${esc(project.source_url)}" target="_blank" rel="noopener noreferrer">${esc(project.source_url)}</a></p>` : input("source_url", t("Внешний источник, если есть"), "url", 'maxlength="2000" placeholder="https://…"')}<p class="hint">${t("Ссылка указывает на внешний сайт; она не связывает вас с его авторами.")}</p>
    <label class="field">Набор участников<select name="recruitment_status">${["unknown", "open", "closed"].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label>
    ${input("commitment", t("Время на участие"), "text", 'maxlength="100"')}${input("experience_level", t("Опыт участников"), "text", 'maxlength="50"')}
    <label class="checkbox"><input name="public" type="checkbox">Опубликовать проект</label><button>${project ? t("Сохранить изменения") : t("Создать проект")}</button></form>`;
  const form = root.querySelector("form");
  if (project) {
    ["title", "summary", "description", "status", "stage", ...(project.origin === "external" ? [] : ["source_url"]), "recruitment_status", "commitment", "experience_level"].forEach(key => { form.elements[key].value = project[key] || ""; });
    ["tags", "skills"].forEach(key => { form.elements[key].value = project[key].join(", "); });
    form.elements.public.checked = project.visibility === "public";
  }
  bindForm(form, async data => {
    const body = Object.fromEntries(["title", "summary", "description", "status", "stage", "recruitment_status"].map(key => [key, data.get(key)]));
    (project?.origin === "external" ? ["commitment", "experience_level"] : ["source_url", "commitment", "experience_level"]).forEach(key => { body[key] = data.get(key).trim() || null; });
    body.visibility = data.has("public") ? "public" : "draft";
    ["tags", "skills"].forEach(key => { body[key] = [...new Set(data.get(key).split(",").map(value => value.trim()).filter(Boolean))]; });
    if (!project) body.slug = data.get("slug").trim();
    if (!project && inspiration) body.derived_from_project_id = inspiration.id;
    const saved = await api(project ? "/projects/" + encodeURIComponent(slug) : "/projects", { method: project ? "PATCH" : "POST", body });
    toast(t("Проект сохранён."));
    go("project/" + saved.slug);
  });
}
async function collaborationProfileScreen(root, stamp) {
  const profile = await api("/me/collaboration-profile");
  if (stamp !== generation) return;
  root.innerHTML = heading(t("Профиль для сотрудничества"), t("Кого и что вы ищете"), t("Ссылки в профиле будут публичными при включённом поиске. Email скрыт; контакт по заявке станет виден владельцу только после принятия.")) + html`<form class="form project-editor collaboration-editor">
    <label class="field">${t("Намерение")}<select name="intent_kind"><option value="">${t("Не указывать")}</option><option value="looking_for_teammates">${t("Ищу участников в проект")}</option><option value="looking_for_project">${t("Ищу проект")}</option><option value="open_to_collaboration">${t("Открыт к сотрудничеству")}</option><option value="interested_in_event">${t("Интересуюсь мероприятиями")}</option></select></label>
    <label class="field">${t("Коротко о том, что ищете")}<textarea name="intent_text" maxlength="500"></textarea></label>
    <label class="field">${t("Навыки через запятую")}<input name="skills" maxlength="1000"></label><label class="field">${t("Интересы через запятую")}<input name="interests" maxlength="1000"></label><label class="field">${t("Какие навыки ищете через запятую")}<input name="wanted_skills" maxlength="1000"></label>
    <div class="project-editor-fields"><label class="field">${t("Часовой пояс")}<input name="timezone" maxlength="100"></label><label class="field">${t("Время на сотрудничество")}<input name="commitment" maxlength="100"></label></div>
    <label class="field">${t("Языки через запятую")}<input name="languages" maxlength="300"></label><label class="field">${t("Ссылки в публичном профиле, по одной на строку")}<textarea name="external_links" maxlength="1500"></textarea></label>
    <label class="field">${t("Статус")}<select name="status"><option value="active">${t("Активен")}</option><option value="paused">${t("На паузе")}</option></select></label>
    <label class="checkbox"><input name="discoverable" type="checkbox">${t("Показывать профиль в поиске людей")}</label><p class="hint">${t("Публичны перечисленные сведения и ссылки после включения поиска. Email не показывается; контакт для заявки остаётся приватным.")}</p><button>${t("Сохранить профиль")}</button></form>`;
  const form = root.querySelector("form");
  form.elements.intent_kind.value = profile.intent_kind || "";
  ["intent_text", "timezone", "commitment", "status"].forEach(key => { form.elements[key].value = profile[key] || (key === "status" ? "active" : ""); });
  ["skills", "interests", "wanted_skills", "languages"].forEach(key => { form.elements[key].value = (profile[key] || []).join(", "); });
  form.elements.external_links.value = (profile.external_links || []).map(link => typeof link === "string" ? link : link.url).join("\n");
  form.elements.discoverable.checked = Boolean(profile.discoverable);
  bindForm(form, async data => {
    const body = { intent_kind: data.get("intent_kind") || null, intent_text: data.get("intent_text").trim() || null, timezone: data.get("timezone").trim() || null, commitment: data.get("commitment").trim() || null, status: data.get("status"), discoverable: data.has("discoverable") };
    ["skills", "interests", "wanted_skills", "languages"].forEach(key => { body[key] = [...new Set(data.get(key).split(",").map(value => value.trim()).filter(Boolean))]; });
    body.external_links = [...new Set(data.get("external_links").split(/\r?\n/).map(value => value.trim()).filter(Boolean))];
    await api("/me/collaboration-profile", { method: "PUT", body });
    toast(t("Профиль для сотрудничества сохранён.")); go("profile/" + me.id);
  });
}
async function collaborationProfileBlock(root, id, own, stamp) {
  const block = root.querySelector("#collaboration-profile");
  if (!block) return;
  if (own) block.innerHTML = t('<p class="hint">Добавьте намерение и навыки, чтобы вас могли найти будущие участники.</p><a class="button secondary" href="/app#collaboration-profile">Настроить профиль сотрудничества</a>');
  try {
    const profile = await api("/people/" + encodeURIComponent(id));
    if (stamp !== generation) return;
    const intent = { looking_for_teammates:"Ищу участников в проект", looking_for_project:"Ищу проект", open_to_collaboration:"Открыт к сотрудничеству", interested_in_event:"Интересуюсь мероприятиями" }[profile.intent_kind] || "";
    block.innerHTML = html`<h2>${t("Сотрудничество")}</h2>${intent ? `<p class="project-card-meta">${t(intent)}</p>` : ""}${profile.intent_text ? `<p class="bio">${esc(profile.intent_text)}</p>` : ""}<div class="project-tags">${(profile.skills || []).map(value => `<span class="project-tag">${esc(value)}</span>`).join("")}</div>${profile.interests?.length ? `<p>${t("Интересы")}: ${profile.interests.map(esc).join(", ")}</p>` : ""}${profile.wanted_skills?.length ? `<p>${t("Ищет навыки")}: ${profile.wanted_skills.map(esc).join(", ")}</p>` : ""}${profile.languages?.length ? `<p class="hint">${t("Языки")}: ${profile.languages.map(esc).join(", ")}</p>` : ""}${profile.timezone ? `<p class="hint">${t("Часовой пояс")}: ${esc(profile.timezone)}</p>` : ""}${profile.commitment ? `<p class="hint">${t("Время на сотрудничество")}: ${esc(profile.commitment)}</p>` : ""}<div class="toolbar">${(profile.external_links || []).map(link => { const url = typeof link === "string" ? link : link.url; return /^https?:\/\//i.test(url) ? `<a class="text-button" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(new URL(url).hostname)}</a>` : ""; }).join("")}</div><section><h3>${t("Проекты и участие")}</h3>${[...(profile.owned_projects || []), ...(profile.memberships || [])].length ? [...(profile.owned_projects || []), ...(profile.memberships || [])].map(project => `<a class="work-project" href="/app#project/${esc(project.slug)}"><strong>${esc(project.title)}</strong><span>${esc(project.role || project.summary)}</span></a>`).join("") : `<p class="hint">${t("Пока нет публичных проектов и участий.")}</p>`}</section>${own ? t('<a class="text-button" href="/app#collaboration-profile">Редактировать профиль сотрудничества</a>') : ""}`;
  } catch (error) {
    if (stamp !== generation) return;
    try {
      const history = await api("/people/" + encodeURIComponent(id) + "/projects");
      if (stamp !== generation) return;
      block.innerHTML = html`<h2>${t("Проекты и участие")}</h2>${history.items.length ? history.items.map(project => html`<a class="work-project" href="/app#project/${esc(project.slug)}"><strong>${esc(project.title)}</strong><span>${esc(project.role || project.summary)}</span></a>`).join("") : html`<p class="hint">${t("Пока нет публичных проектов и участий.")}</p>`}${own ? t('<a class="button secondary" href="/app#collaboration-profile">Настроить профиль сотрудничества</a>') : html`<p class="hint">${t("Профиль для сотрудничества не опубликован.")}</p>`}`;
    } catch { if (own) block.innerHTML = t('<a class="button secondary" href="/app#collaboration-profile">Настроить профиль сотрудничества</a>'); else block.innerHTML = t('<p class="hint">Профиль для сотрудничества не опубликован.</p>'); }
  }
}
async function projectClaimScreen(root, slug, stamp) {
  const project = await api("/projects/" + encodeURIComponent(slug));
  if (stamp !== generation) return;
  root.innerHTML = html`<a class="back" href="${projectPath(project)}">${esc(project.title)}</a>` + heading("", t("Запросить подтверждение проекта"), t("Запрос будет рассмотрен администратором. Публичное описание и источник проекта останутся атрибутированными.")) + html`<form class="form project-editor"><label class="field">${t("Ссылка, подтверждающая вашу связь с проектом")}<input name="evidence_url" type="url" maxlength="2048" placeholder="https://…"></label><label class="field">${t("Кратко объясните связь с проектом")}<textarea name="evidence_text" maxlength="2000"></textarea></label><button>${t("Отправить на проверку")}</button></form>`;
  bindForm(root.querySelector("form"), async data => { const evidenceUrl = data.get("evidence_url").trim(); const evidenceText = data.get("evidence_text").trim(); if (!evidenceUrl && !evidenceText) throw new Error(t("Добавьте ссылку или краткое объяснение связи с проектом.")); await api("/projects/" + encodeURIComponent(slug) + "/claims", { method:"POST", body:{ evidence_url:evidenceUrl || null, evidence_text:evidenceText || null } }); toast(t("Запрос на подтверждение отправлен на проверку.")); go("project/" + slug); });
}
async function externalSubmissionScreen(root, stamp) {
  root.innerHTML = heading("", t("Предложить внешний проект"), t("Мы проверим ссылку и атрибуцию. Публикация не означает, что автор ищет участников или одобрил страницу.")) + html`<form class="form project-editor"><label class="field">${t("Название проекта")}<input name="title" required maxlength="200"></label><label class="field">${t("Краткое описание")}<input name="summary" required maxlength="500"></label><label class="field">${t("Подробнее о проекте")}<textarea name="description" maxlength="50000"></textarea></label><label class="field">${t("Теги через запятую")}<input name="tags" maxlength="1000"></label><label class="field">${t("Технологии и навыки через запятую")}<input name="skills" maxlength="1000"></label><label class="field">${t("Внешняя ссылка")}<input name="source_url" type="url" required maxlength="2048" placeholder="https://…"></label><button>${t("Отправить на проверку")}</button></form>`;
  bindForm(root.querySelector("form"), async data => { const body = { title:data.get("title"), summary:data.get("summary"), description:data.get("description"), source_url:data.get("source_url"), tags:data.get("tags").split(",").map(value=>value.trim()).filter(Boolean), skills:data.get("skills").split(",").map(value=>value.trim()).filter(Boolean) }; await api("/external-submissions", {method:"POST",body}); root.innerHTML = empty(t("Проект отправлен на проверку"), t("Он появится в каталоге только после проверки источника."), html`<a class="button" href="/app#explore">${t("Вернуться к обзору")}</a>`); });
}
async function adminReviewScreen(root, stamp) {
  const [submissionPage, claimPage] = await Promise.all([api("/admin/external-submissions"), api("/admin/project-claims")]);
  const submissions = submissionPage.items;
  const claims = claimPage.items;
  if (stamp !== generation) return;
  root.innerHTML = heading("", t("Очередь проверки"), t("Проверяйте источник и доказательства связи до одобрения.")) + html`<section class="review-queue"><h2>${t("Внешние проекты")}</h2><div id="external-queue"></div></section><section class="review-queue"><h2>${t("Запросы на владение")}</h2><div id="claim-queue"></div></section>`;
  const submissionList = root.querySelector("#external-queue");
  submissionList.innerHTML = submissions.length ? submissions.map(item => html`<article class="review-item"><h3>${esc(item.title)}</h3><p>${esc(item.summary)}</p><p class="hint">${t("Автор предложения")}: ${esc(item.submitted_by)} · ${date(item.created_at)}</p><a class="text-button" href="${/^https?:\/\//i.test(item.source_url) ? esc(item.source_url) : "#"}" target="_blank" rel="noopener noreferrer">${esc(item.source_url)}</a><p>${esc(item.description || "")}</p><div class="toolbar"><button data-review="approved" data-type="external" data-id="${item.id}">${t("Одобрить")}</button><button class="secondary" data-review="rejected" data-type="external" data-id="${item.id}">${t("Отклонить")}</button></div></article>`).join("") : `<p class="hint">${t("Нет ожидающих проектов.")}</p>`;
  const claimList = root.querySelector("#claim-queue");
  claimList.innerHTML = claims.length ? claims.map(item => html`<article class="review-item"><h3><a href="/app#project/${esc(item.project_slug)}">${esc(item.project_title)}</a></h3><p class="hint">${t("Запросивший")}: ${item.requester_id} · ${date(item.created_at)}</p>${item.evidence_url && /^https?:\/\//i.test(item.evidence_url) ? html`<a class="text-button" href="${esc(item.evidence_url)}" target="_blank" rel="noopener noreferrer">${esc(item.evidence_url)}</a>` : ""}<p>${esc(item.evidence_text || "")}</p><div class="toolbar"><button data-review="approved" data-type="claim" data-id="${item.id}">${t("Одобрить")}</button><button class="secondary" data-review="rejected" data-type="claim" data-id="${item.id}">${t("Отклонить")}</button></div></article>`).join("") : `<p class="hint">${t("Нет ожидающих запросов.")}</p>`;
  root.querySelectorAll("[data-review]").forEach(button => actionButton(button, async () => { const path = button.dataset.type === "external" ? "/admin/external-submissions/" : "/admin/project-claims/"; await api(path + button.dataset.id, {method:"PATCH",body:{status:button.dataset.review}}); await render(); }));
}
async function applicationsScreen(root, stamp) {
  const applications = await api("/me/applications");
  if (stamp !== generation) return;
  root.innerHTML = heading("", t("Мои заявки"), t("Контактные ссылки открываются только после принятия заявки.")) + (applications.length ? applications.map(application => html`<article class="project-application"><div class="project-card-meta"><a class="author" href="/app#project/${esc(application.project_slug)}">${esc(application.project_title)}</a><span>${applicationLabel(application.status)}</span></div><p>${esc(application.message)}</p>${application.status === "accepted" && application.owner_contact_url ? html`<a class="button" href="${esc(application.owner_contact_url)}" target="_blank" rel="noopener noreferrer">${t("Связаться с командой")}</a>` : ""}${application.status === "pending" ? html`<button class="secondary" data-withdraw="${application.id}">${t("Отозвать заявку")}</button>` : ""}</article>`).join("") : empty(t("Заявок пока нет"), t("Открытые роли появятся здесь после отправки отклика."), html`<a class="button" href="/app#explore?kind=openings">${t("Найти открытые роли")}</a>`));
  root.querySelectorAll("[data-withdraw]").forEach(button => actionButton(button, async () => { await api("/me/applications/" + button.dataset.withdraw + "/withdraw", {method:"POST"}); await render(); }));
}
