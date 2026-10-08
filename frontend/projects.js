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
  return platformCard(project, "project");
}
function personCard(person) {
  return platformCard(person, "person");
}
function openingCard(opening) {
  return platformCard(opening, "opening");
}
function applicationLabel(value) {
  return projectLabel(value);
}
async function discoveryScreen(root, query, stamp) {
  const kinds = ["all", "projects", "teams", "events", "communities", "people"];
  const kind = kinds.includes(query.get("kind")) ? query.get("kind") : "all";
  const filters = ["search", "skill", "language", "format"];
  const supportedFilters = kind === "people" ? filters.filter(key => key !== "format") : filters;
  const hrefFor = (value, reset = false) => { const params = new URLSearchParams(); if (query.has("search")) params.set("search", query.get("search")); if (!reset) for (const key of filters.slice(1)) if (key !== "format" || value !== "people") if (query.has(key)) params.set(key, query.get(key)); params.set("kind", value); return "/app#explore?" + params; };
  const mobile = matchMedia("(max-width: 850px)");
  root.innerHTML = html`<div class="discovery-shell">
    <aside class="discovery-sidebar"><form class="discovery-filter-form"><input type="hidden" name="search" value="${esc(query.get("search") || "")}"><input type="hidden" name="kind" value="${kind}">
      <details class="discovery-filters" ${!mobile.matches || filters.slice(1).some(key => query.has(key)) ? "open" : ""}><summary>${icon("filter")} ${t("Фильтры")}</summary><div class="filter-fields">
        ${input("skill", t("Навык"), "text", 'maxlength="80"')}${input("language", t("Язык"), "text", 'maxlength="80" placeholder="Русский, English"')}
        ${kind === "people" ? "" : html`<label class="field">${t("Формат")}<select name="format"><option value="">${t("Любой")}</option><option value="online">${t("Онлайн")}</option><option value="local">${t("На месте")}</option><option value="hybrid">${t("Гибридный")}</option></select></label>`}
        <button type="submit" class="secondary">${t("Применить фильтры")}</button><a class="text-button" href="${hrefFor(kind, true)}">${t("Сбросить фильтры")}</a>
      </div></details></form></aside>
    <main class="discovery-center"><section class="discovery-intro"><h1>${t("Найдите, с кем создавать дальше")}</h1><p class="intro">${t("Проекты, команды, встречи и сообщества для совместной работы.")}</p></section>
      <form class="discovery-search" role="search"><label class="field"><span>${t("Поиск по Кругу")}</span><input name="search" maxlength="100" placeholder="${t("Проект, навык или человек")}" value="${esc(query.get("search") || "")}"></label><button>${icon("explore")} ${t("Найти")}</button></form>
      <nav class="discovery-tabs" aria-label="${t("Тип результатов")}">${[["all", "Всё"], ["projects", "Проекты"], ["teams", "Команды"], ["events", "События"], ["communities", "Сообщества"], ["people", "Люди"]].map(([value, label]) => html`<a href="${hrefFor(value)}" class="${kind === value ? "active" : ""}" ${kind === value ? 'aria-current="page"' : ""}>${t(label)}</a>`).join("")}</nav>
      <div class="discovery-results-heading"><h2>${t({ all:"Все результаты", projects:"Проекты", teams:"Команды", events:"События", communities:"Сообщества", people:"Люди" }[kind])}</h2><div class="toolbar">${kind === "projects" || kind === "all" ? html`<a class="text-button" href="/app#roles">${t("Открытые роли")}</a>` : ""}${session && ["all", "projects"].includes(kind) ? html`<a class="text-button" href="/app#project-new">${icon("plus")} ${t("Новый проект")}</a>` : ""}</div></div><div id="discovery-results"></div>
    </main><aside class="upcoming-rail"><div class="upcoming-heading"><h2>${t("Скоро")}</h2><a href="${hrefFor("events")}">${t("Все события")}</a></div><div id="upcoming-events"><p class="hint">${t("Загружаем события…")}</p></div></aside>
  </div>`;
  const form = root.querySelector(".discovery-filter-form");
  const disclosure = root.querySelector(".discovery-filters");
  let manualDisclosure = false;
  disclosure.querySelector("summary").addEventListener("click", () => { manualDisclosure = true; });
  mobile.addEventListener("change", event => { if (!manualDisclosure && !filters.slice(1).some(key => query.has(key))) disclosure.open = !event.matches; });
  supportedFilters.slice(1).forEach(key => { if (form.elements[key]) form.elements[key].value = query.get(key) || ""; });
  bindForm(root.querySelector(".discovery-search"), async data => {
    const params = new URLSearchParams(query), value = data.get("search")?.trim();
    if (value) params.set("search", value); else params.delete("search");
    params.set("kind", kind); go("explore?" + params);
  });
  bindForm(form, async data => {
    const params = new URLSearchParams(query);
    for (const key of supportedFilters.slice(1)) { const value = data.get(key)?.trim(); if (value) params.set(key, value); else params.delete(key); }
    params.set("kind", kind); go("explore?" + params);
  });
  const params = new URLSearchParams(); supportedFilters.forEach(key => { if (query.has(key)) params.set(key, query.get(key)); });
  const sources = {
    projects: [["Проекты", "/discovery?source=native", item => projectCard(item)], ["Внешние проекты", "/discovery?source=external", item => projectCard(item)]],
    teams: [["Команды", "/teams", item => platformCard(item, "team")]],
    events: [["События", "/events", item => platformCard(item, "event")]],
    communities: [["Сообщества", "/communities", item => platformCard(item, "community")]],
    people: [["Люди", "/people", item => personCard(item)]],
  };
  const specs = kind === "all" ? Object.values(sources).flat() : sources[kind];
  if (kind !== "all") {
    const results = root.querySelector("#discovery-results");
    const filteredPath = path => path + (path.includes("?") ? "&" : "?") + params;
    if (kind === "projects") {
      results.innerHTML = specs.map(([label]) => html`<section class="discovery-source"><div class="discovery-results-heading"><h3>${t(label)}</h3></div><div class="discovery-source-results"></div></section>`).join("");
      const groups = results.querySelectorAll(".discovery-source-results");
      await Promise.all(specs.map(async ([label, path, renderCard], index) => {
        try { await paged(groups[index], filteredPath(path), renderCard, stamp, empty(t("Пока нет результатов"), t("Измените запрос или попробуйте позже. Здесь показывается только актуальное содержимое участников."))); }
        catch (error) { groups[index].innerHTML = `<p class="error" role="alert">${t(label)}: ${esc(errorText(error))}</p>`; }
      }));
    } else {
      try { await paged(results, filteredPath(specs[0][1]), specs[0][2], stamp, empty(t("Пока нет результатов"), t("Измените запрос или попробуйте позже. Здесь показывается только актуальное содержимое участников."))); }
      catch (error) { results.innerHTML = `<p class="error" role="alert">${esc(errorText(error))}</p>`; }
    }
    bindPlatformSaves(results, stamp);
    try {
      const upcoming = await api("/events?upcoming=true&limit=3");
      if (stamp === generation) root.querySelector("#upcoming-events").innerHTML = upcoming.items.length ? upcoming.items.map(platformEventRow).join("") : `<p class="hint">${t("Событий пока нет.")}</p>`;
    } catch (error) { if (stamp === generation) root.querySelector("#upcoming-events").innerHTML = `<p class="hint">${esc(errorText(error))}</p>`; }
    return;
  }
  const formatDoesNotApply = params.has("format");
  const pages = await Promise.all(specs.map(async ([label, path, renderCard]) => {
    if (label === "Люди" && formatDoesNotApply) return { label, items: [], hint: t("Фильтр формата применяется к проектам, командам, событиям и сообществам; для поиска людей снимите его.") };
    const listParams = new URLSearchParams(params); listParams.set("limit", kind === "all" ? "3" : "24");
    try { return { label, items: (await api(path + (path.includes("?") ? "&" : "?") + listParams)).items.map(renderCard) }; }
    catch (error) { return { label, error: errorText(error) }; }
  }));
  if (stamp !== generation) return;
  const cards = [];
  for (let index = 0; index < Math.max(0, ...pages.map(page => page.items?.length || 0)); index++) for (const page of pages) if (page.items?.[index]) cards.push(page.items[index]);
  const errors = pages.filter(page => page.error).map(page => `<p class="error" role="alert">${t(page.label)}: ${esc(page.error)}</p>`).join("");
  const hints = pages.filter(page => page.hint).map(page => `<p class="hint">${page.hint}</p>`).join("");
  const results = root.querySelector("#discovery-results");
  results.innerHTML = `${cards.length ? `<div class="project-grid">${cards.join("")}</div>` : errors ? "" : empty(t("Пока нет результатов"), t("Измените запрос или попробуйте позже. Здесь показывается только актуальное содержимое участников."))}${errors}${hints}`;
  bindPlatformSaves(results, stamp);
  try {
    const upcoming = await api("/events?upcoming=true&limit=3");
    if (stamp === generation) root.querySelector("#upcoming-events").innerHTML = upcoming.items.length ? upcoming.items.map(platformEventRow).join("") : `<p class="hint">${t("Событий пока нет.")}</p>`;
  } catch (error) { if (stamp === generation) root.querySelector("#upcoming-events").innerHTML = `<p class="hint">${esc(errorText(error))}</p>`; }
}

function projectOpeningCard(opening) {
  const project = opening.project;
  const href = project?.slug ? projectPath(project) : "/app#projects";
  return html`<article class="platform-card platform-card-opening">
    ${platformCover(project, "project")}<div class="platform-card-copy"><div class="platform-card-meta"><span>${t("Открытая роль")}</span>${opening.commitment ? html`<span>${esc(opening.commitment)}</span>` : ""}</div>
      <h3><a href="${href}">${esc(opening.title || opening.role)}</a></h3>${project ? html`<p class="hint">${t("Проект")}: ${esc(project.title)}</p><p class="platform-card-summary">${esc(project.summary)}</p>` : ""}<p class="platform-card-summary">${esc(opening.description || "")}</p>${platformTags(opening)}
    </div><a class="project-open" href="${href}">${t("О проекте")}${icon("arrow")}</a>
  </article>`;
}

async function openRolesScreen(root, query, stamp) {
  const params = new URLSearchParams();
  for (const key of ["search", "skill"]) if (query.has(key)) params.set(key, query.get(key));
  root.innerHTML = heading(t("Открытые роли"), t("Роли в проектах"), t("Просматривайте актуальные роли и откликайтесь на странице проекта.")) + html`<form class="discovery-search" role="search"><label class="field"><span>${t("Поиск")}</span><input name="search" value="${esc(query.get("search") || "")}" maxlength="100" placeholder="${t("Название роли или навык")}"></label><button>${icon("explore")} ${t("Найти")}</button></form><div id="open-roles-results"></div>`;
  bindForm(root.querySelector(".discovery-search"), async data => { const next = new URLSearchParams(query); const search = data.get("search").trim(); if (search) next.set("search", search); else next.delete("search"); go("roles?" + next); });
  if (stamp !== generation) return;
  await paged(root.querySelector("#open-roles-results"), "/openings?" + params, projectOpeningCard, stamp, empty(t("Пока нет открытых ролей"), t("Открытые роли появятся здесь, когда проекты начнут набор."), html`<a class="button" href="/app#explore?kind=projects">${t("Найти проекты")}</a>`));
}

async function projectListScreen(root, saved, stamp, query = new URLSearchParams()) {
  const following = saved && query.get("following") === "true";
  if (saved && !following) {
    const savedKinds = { projects: ["/me/saved-projects", "project"], teams: ["/teams?saved=true", "team"], communities: ["/communities?saved=true", "community"], events: ["/events?saved=true", "event"] };
    const selectedKind = savedKinds[query.get("kind")];
    if (selectedKind) {
      const kind = query.get("kind");
      root.innerHTML = heading("", t("Сохранённое"), t("Вы просматриваете сохранённые материалы этого типа.")) + html`<div class="tabs"><a href="/app#saved">${t("Всё сохранённое")}</a><a href="/app#saved?following=true">${t("Подписки на проекты")}</a></div><a class="back" href="/app#saved">${t("Назад ко всему сохранённому")}</a><div id="saved-kind-results"></div>`;
      await paged(root.querySelector("#saved-kind-results"), selectedKind[0], item => platformCard(item, selectedKind[1]), stamp, empty(t("Пока ничего не сохранено"), t("Откройте интересующую страницу и сохраните её.")));
      bindPlatformSaves(root.querySelector("#saved-kind-results"), stamp);
      return;
    }
    root.innerHTML = heading("", t("Сохранённое"), t("Сохраняйте команды, сообщества, события и проекты, чтобы вернуться к ним позже.")) +
      html`<div class="tabs"><a href="/app#saved" class="active">${t("Всё сохранённое")}</a><a href="/app#saved?following=true">${t("Подписки на проекты")}</a></div><div id="saved-results"></div>`;
    const endpoints = [
      ["/me/saved-projects?limit=8", "project", "projects"], ["/teams?saved=true&limit=8", "team", "teams"],
      ["/communities?saved=true&limit=8", "community", "communities"], ["/events?saved=true&limit=8", "event", "events"],
    ];
    const pages = await Promise.all(endpoints.map(async ([path, kind, route]) => {
      try { return { kind, route, ...(await api(path)) }; }
      catch (error) { return { kind, route, error: errorText(error) }; }
    }));
    if (stamp !== generation) return;
    const items = [];
    for (let index = 0; index < Math.max(0, ...pages.map(page => page.items?.length || 0)); index++) {
      for (const page of pages) if (page.items?.[index]) items.push(platformCard(page.items[index], page.kind));
    }
    const errors = pages.filter(page => page.error).map(page => `<p class="error" role="alert">${t(page.kind)}: ${esc(page.error)}</p>`).join("");
    const more = pages.filter(page => page.has_more).map(page => html`<a class="text-button" href="/app#saved?kind=${page.route}">${t("Показать больше")}: ${t(page.kind)} ${icon("arrow")}</a>`).join("");
    root.querySelector("#saved-results").innerHTML = items.length ? `<div class="project-grid">${items.join("")}</div>${more}${errors}` : errors || empty(t("Пока ничего не сохранено"), t("Откройте интересующую страницу и сохраните её."), html`<a class="button" href="/app#explore">${t("Исследовать")}</a>`);
    bindPlatformSaves(root.querySelector("#saved-results"), stamp);
    return;
  }
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
  root.querySelector(".project-detail-main").insertAdjacentHTML("afterbegin", platformCover(project, "project"));
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
  let project = slug ? await api("/projects/" + encodeURIComponent(slug)) : null;
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
    <div class="project-editor-fields"><label class="field">${t("Формат")}<select name="format"><option value="unspecified">${t("Не указан")}</option><option value="online">${t("Онлайн")}</option><option value="local">${t("На месте")}</option><option value="hybrid">${t("Гибридный")}</option></select></label>${input("location", t("Место или город"), "text", 'maxlength="160"')}</div>
    ${input("languages", t("Языки через запятую"), "text", 'maxlength="500"')}
    ${project?.origin === "external" ? html`<p class="hint">${t("Первоисточник проекта")} <a href="${esc(project.source_url)}" target="_blank" rel="noopener noreferrer">${esc(project.source_url)}</a></p>` : input("source_url", t("Внешний источник, если есть"), "url", 'maxlength="2000" placeholder="https://…"')}<p class="hint">${t("Ссылка указывает на внешний сайт; она не связывает вас с его авторами.")}</p>
    <label class="field">Набор участников<select name="recruitment_status">${["unknown", "open", "closed"].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label>
    ${input("commitment", t("Время на участие"), "text", 'maxlength="100"')}${input("experience_level", t("Опыт участников"), "text", 'maxlength="50"')}
    <label class="field">${t("Обложка — необязательно, до 8 МиБ")}<input name="cover" type="file" accept="image/jpeg,image/png,image/webp"></label>${project?.cover_url ? html`<div class="cover-editor">${platformCover(project, "project")}<button type="button" class="secondary" data-remove-cover>${t("Удалить обложку")}</button></div>` : ""}
    <label class="checkbox"><input name="public" type="checkbox">Опубликовать проект</label><button>${project ? t("Сохранить изменения") : t("Создать проект")}</button><p class="hint" role="status" data-cover-status></p></form>`;
  const form = root.querySelector("form");
  if (project) {
    ["title", "summary", "description", "status", "stage", ...(project.origin === "external" ? [] : ["source_url"]), "recruitment_status", "commitment", "experience_level", "format", "location"].forEach(key => { form.elements[key].value = project[key] || ""; });
    ["tags", "skills"].forEach(key => { form.elements[key].value = project[key].join(", "); });
    form.elements.languages.value = (project.languages || []).join(", ");
    form.elements.public.checked = project.visibility === "public";
  }
  const removeCover = form.querySelector("[data-remove-cover]");
  if (removeCover) actionButton(removeCover, async () => { await api(`/projects/${encodeURIComponent(project.slug)}/cover`, { method: "DELETE" }); toast(t("Обложка удалена.")); go("project-edit/" + project.slug); });
  bindForm(form, async data => {
    const body = Object.fromEntries(["title", "summary", "description", "status", "stage", "recruitment_status"].map(key => [key, data.get(key)]));
    (project?.origin === "external" ? ["commitment", "experience_level"] : ["source_url", "commitment", "experience_level"]).forEach(key => { body[key] = data.get(key).trim() || null; });
    body.visibility = data.has("public") ? "public" : "draft";
    ["tags", "skills"].forEach(key => { body[key] = [...new Set(data.get(key).split(",").map(value => value.trim()).filter(Boolean))]; });
    body.languages = [...new Set(data.get("languages").split(",").map(value => value.trim()).filter(Boolean))];
    body.format = data.get("format"); body.location = data.get("location").trim() || null;
    if (!project) body.slug = data.get("slug").trim();
    if (!project && inspiration) body.derived_from_project_id = inspiration.id;
    project = await api(project ? "/projects/" + encodeURIComponent(project.slug) : "/projects", { method: project ? "PATCH" : "POST", body });
    const cover = data.get("cover");
    if (cover?.size) {
      if (cover.size > 8 * 1024 * 1024) throw new Error(t("Фото должно быть не больше 8 МиБ."));
      if (!["image/jpeg", "image/png", "image/webp"].includes(cover.type)) throw new Error(t("Выберите изображение JPEG, PNG или WebP."));
      try { await api(`/projects/${encodeURIComponent(project.slug)}/cover`, { method: "PUT", body: cover, headers: { "Content-Type": cover.type } }); }
      catch (error) { form.querySelector("[data-cover-status]").textContent = t("Проект сохранён. Обложка не загрузилась; выберите её и отправьте форму ещё раз."); throw error; }
    }
    toast(t("Проект сохранён."));
    go("project/" + project.slug);
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
  const [projectResult, teamResult] = await Promise.allSettled([api("/me/applications"), api("/team-applications?limit=100")]);
  if (stamp !== generation) return;
  const projects = projectResult.status === "fulfilled" ? projectResult.value : [];
  const teams = teamResult.status === "fulfilled" ? teamResult.value.items : [];
  const projectError = projectResult.status === "rejected" ? `<p class="error" role="alert">${esc(errorText(projectResult.reason))}</p>` : "";
  const teamError = teamResult.status === "rejected" ? `<p class="error" role="alert">${esc(errorText(teamResult.reason))}</p>` : "";
  root.innerHTML = heading("", t("Мои заявки"), t("Контактные ссылки открываются только после принятия заявки.")) +
    `<section class="platform-detail-section"><h2>${t("Проекты")}</h2>${projectError}${projects.length ? projects.map(application => html`<article class="project-application"><div class="project-card-meta"><a class="author" href="/app#project/${esc(application.project_slug)}">${esc(application.project_title)}</a><span>${applicationLabel(application.status)}</span></div><p>${esc(application.message)}</p>${application.status === "accepted" && application.owner_contact_url ? html`<a class="button" href="${esc(application.owner_contact_url)}" target="_blank" rel="noopener noreferrer">${t("Связаться с командой")}</a>` : ""}${application.status === "pending" ? html`<button class="secondary" data-withdraw-project="${application.id}">${t("Отозвать заявку")}</button>` : ""}</article>`).join("") : projectError ? "" : `<p class="hint">${t("Заявок пока нет")}</p>`}</section>` +
    `<section class="platform-detail-section"><h2>${t("Команды")}</h2>${teamError}${teams.length ? teams.map(application => html`<article class="project-application"><div class="project-card-meta"><a class="author" href="/app#team/${esc(application.team_slug)}">${esc(application.team_title)} · ${esc(application.opening_title)}</a><span>${applicationLabel(application.status)}</span></div><p>${esc(application.message)}</p>${application.status === "pending" ? html`<button class="secondary" data-withdraw-team="${application.id}">${t("Отозвать заявку")}</button>` : ""}</article>`).join("") : teamError ? "" : `<p class="hint">${t("Заявок пока нет")}</p>`}<a class="button secondary" href="/app#explore?kind=teams">${t("Найти команды")}</a></section>`;
  root.querySelectorAll("[data-withdraw-project]").forEach(button => actionButton(button, async () => { await api("/me/applications/" + button.dataset.withdrawProject + "/withdraw", {method:"POST"}); await render(); }));
  root.querySelectorAll("[data-withdraw-team]").forEach(button => actionButton(button, async () => { await api("/team-applications/" + button.dataset.withdrawTeam, {method:"PATCH", body:{status:"withdrawn"}}); await render(); }));
}
