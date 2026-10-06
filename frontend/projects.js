"use strict";
// Discovery and project screens share the existing account, pagination and post UI.
function projectLabel(value) {
  return t({ native: "В Круге", external: "Внешний проект", active: "Активен", paused: "На паузе", completed: "Завершён", archived: "В архиве", stale: "Возможно устарел", idea: "Идея", prototype: "Прототип", building: "В разработке", shipped: "Выпущен", unknown: "Не указано", open: "Набор открыт", closed: "Набор закрыт" }[value] || value);
}
function projectPath(project) {
  return "/project/" + encodeURIComponent(project.slug);
}
function projectTags(project) {
  const tags = project.tags.map(value => ({ value, filter: "tag" }));
  const skills = project.skills.filter(value => !project.tags.includes(value)).map(value => ({ value, filter: "skill" }));
  return [...tags, ...skills].slice(0, 8).map(({ value, filter }) => html`<a class="project-tag" href="/app#explore?${filter}=${encodeURIComponent(value)}">${esc(value)}</a>`).join("");
}
function projectCard(project) {
  return html`<article class="project-card">
    <div class="project-card-meta"><span>${esc(project.source_name || projectLabel(project.origin))}</span><span class="project-status" data-status="${esc(project.status)}">${projectLabel(project.status)}</span></div>
    <h2><a href="/app#project/${esc(project.slug)}">${esc(project.title)}</a></h2>
    <p class="project-summary">${esc(project.summary)}</p>
    <div class="project-tags">${projectTags(project)}</div>
    <div class="project-card-bottom"><span class="hint">${projectLabel(project.stage)}${project.recruitment_status === "open" ? " · " + projectLabel("open") : ""}${project.visibility === "draft" ? " · " + t("Черновик") : ""}</span><a class="project-open" href="/app#project/${esc(project.slug)}" aria-label="${t("Открыть проект")} ${esc(project.title)}">${t("Открыть проект")}${icon("arrow")}</a></div>
  </article>`;
}
async function discoveryScreen(root, query, stamp) {
  root.innerHTML = html`<section class="discovery-intro"><div><h1>Найдите то, что хочется строить.</h1><p class="intro">Проекты, открытый код и новые возможности для разработчиков. Исследуйте без регистрации.</p></div><a class="text-button" href="/project/krug">Как строится Круг ${icon("arrow")}</a></section>
    <div class="discovery-workspace"><aside class="discovery-sidebar"><form class="discovery-search" role="search"><div class="discovery-search-main"><label class="field"><span>Поиск проектов</span><input name="search" maxlength="100" placeholder="Godot, Python, open source…" value="${esc(query.get("search") || "")}"></label><button>${icon("explore")} Найти</button></div>
    <details class="discovery-filters" ${matchMedia("(min-width: 851px)").matches || ["tag", "skill", "source", "status", "active"].some(key => query.has(key)) ? "open" : ""}><summary>Фильтры</summary><div class="filter-fields">
    ${input("tag", t("Тег"), "text", 'maxlength="50"')}${input("skill", t("Навык"), "text", 'maxlength="50"')}${input("source", t("Источник"), "text", 'maxlength="40"')}
    <label class="field">Статус<select name="status"><option value="">Все статусы</option>${["active", "paused", "completed", "archived", "stale"].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label>
    <label class="checkbox"><input name="active" type="checkbox">Только активные</label><a class="text-button" href="/app#explore">Сбросить фильтры</a></div></details></form></aside>
    <section class="discovery-results"><div class="discovery-results-heading"><h2>Исследуйте проекты</h2><span class="hint">В Круге и за его пределами</span></div><div id="discovery-results"></div></section></div>`;
  const form = root.querySelector("form");
  ["tag", "skill", "source", "status"].forEach(key => { form.elements[key].value = query.get(key) || ""; });
  form.elements.active.checked = query.get("active") === "true";
  bindForm(form, async data => {
    const params = new URLSearchParams();
    ["search", "tag", "skill", "source", "status"].forEach(key => { const value = data.get(key).trim(); if (value) params.set(key, value); });
    if (data.has("active")) params.set("active", "true");
    go("explore?" + params);
  });
  const params = new URLSearchParams();
  ["search", "tag", "skill", "source", "status", "active"].forEach(key => { if (query.has(key)) params.set(key, query.get(key)); });
  await paged(root.querySelector("#discovery-results"), "/discovery?" + params, projectCard, stamp,
    empty(t("Пока нет подходящих проектов"), t("Попробуйте другой запрос или сбросьте фильтры. Новые проекты появятся здесь после публикации."), html`<a class="button secondary" href="/app#explore">Сбросить фильтры</a>`));
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
  root.innerHTML = html`<a class="back" href="/app#explore">${icon("arrow")} Все проекты</a>
    <article class="project-detail"><div class="project-detail-main"><div class="project-card-meta"><span>${esc(project.source_name || projectLabel(project.origin))}</span><span class="project-status" data-status="${esc(project.status)}">${projectLabel(project.status)}</span>${project.visibility === "draft" ? html`<span class="badge">Черновик</span>` : ""}</div><h1>${esc(project.title)}</h1><p class="project-lead">${esc(project.summary)}</p><div class="project-tags">${projectTags(project)}</div>
    ${project.description ? html`<div class="project-description">${esc(project.description)}</div>` : ""}
    <dl class="project-facts"><div><dt>Этап</dt><dd>${projectLabel(project.stage)}</dd></div><div><dt>Последнее обновление</dt><dd>${project.last_activity_at ? date(project.last_activity_at) : projectLabel("unknown")}</dd></div>${project.last_verified_at ? html`<div><dt>Проверен</dt><dd>${date(project.last_verified_at)}</dd></div>` : ""}${project.recruitment_status ? html`<div><dt>Набор участников</dt><dd>${projectLabel(project.recruitment_status)}</dd></div>` : ""}${project.commitment ? html`<div><dt>Время на участие</dt><dd>${esc(project.commitment)}</dd></div>` : ""}${project.experience_level ? html`<div><dt>Опыт участников</dt><dd>${esc(project.experience_level)}</dd></div>` : ""}</dl>
    ${project.origin === "external" ? html`<p class="hint">Внешний проект. Данные об активности не подтверждают, что автор сейчас ищет участников.</p>` : ""}
    <div class="toolbar">${project.source_url ? html`<a class="button" href="${esc(project.source_url)}" target="_blank" rel="noopener noreferrer">Открыть источник ${icon("arrow")}</a>` : ""}${project.visibility === "public" ? html`<a class="button secondary" href="${projectPath(project)}">Публичная ссылка</a>` : ""}${own ? html`<a class="text-button" href="/app#project-edit/${esc(project.slug)}">Редактировать проект</a><a class="button" href="/app#new?project=${project.id}">${icon("plus")} Написать обновление</a>` : ""}</div></div>
    <aside class="project-engagement" aria-label="${t("Ваш интерес к проекту")}"><h2>Оставайтесь рядом</h2><p class="hint">Сохраните проект или отметьте интерес. Подписка сохраняет ваш выбор; письма об обновлениях пока не отправляются.</p><div id="engagement">${session ? html`<p class="hint" role="status">Загрузка…</p>` : html`<a class="button" href="/app#login?next=${encodeURIComponent("project/" + slug)}">Войти, чтобы сохранить</a><p class="hint">Просмотр проекта и обновлений остаётся открытым.</p>`}</div><a class="text-button" href="/app#project-interested/${esc(project.slug)}">Кому интересен проект ${icon("arrow")}</a></aside></article>
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
async function projectInterestedScreen(root, slug, stamp) {
  const project = await api("/projects/" + encodeURIComponent(slug));
  if (stamp !== generation) return;
  root.innerHTML = html`<a class="back" href="${projectPath(project)}">${esc(project.title)}</a>` + heading("", t("Кому интересен проект"), t("Здесь только люди, которые сами разрешили показать профиль для этого проекта."));
  await paged(root, "/projects/" + encodeURIComponent(slug) + "/interested", user => html`<article class="interested-person"><a class="avatar" href="/app#profile/${user.id}">${esc((user.display_name || user.username)[0].toUpperCase())}</a><div><a class="author" href="/app#profile/${user.id}">${esc(user.display_name || user.username)}</a><p class="hint">@${esc(user.username)}</p><p>${esc(user.bio)}</p></div></article>`, stamp,
    empty(t("Пока нет открытых профилей"), t("Интерес может оставаться приватным. Это не означает, что проект никому не интересен.")));
}
async function projectEditorScreen(root, slug, stamp) {
  const project = slug ? await api("/projects/" + encodeURIComponent(slug)) : null;
  if (stamp !== generation) return;
  root.innerHTML = heading("", project ? t("Редактировать проект") : t("Создать проект"), t("Что вы строите и кому это может быть интересно? Черновик виден только вам.")) + html`<form class="form project-editor">
    ${input("title", t("Название проекта"), "text", 'required maxlength="200"')}${project ? "" : input("slug", t("Адрес проекта"), "text", 'required minlength="3" maxlength="100" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" placeholder="my-project"')}
    ${project ? "" : html`<span class="hint">Латинские буквы, цифры и дефисы. Адрес нельзя изменить после создания.</span>`}
    ${input("summary", t("Краткое описание"), "text", 'required maxlength="500"')}
    <label class="field">Подробнее о проекте<textarea name="description" maxlength="20000"></textarea></label>
    <div class="project-editor-fields"><label class="field">Статус<select name="status">${["active", "paused", "completed", "archived"].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label><label class="field">Этап<select name="stage">${["idea", "prototype", "building", "shipped"].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label></div>
    ${input("tags", t("Теги через запятую"), "text", 'maxlength="1000" placeholder="gamedev, open-source"')}${input("skills", t("Технологии и навыки через запятую"), "text", 'maxlength="1000" placeholder="Python, Godot"')}
    ${input("source_url", t("Ссылка на проект"), "url", 'maxlength="2000" placeholder="https://github.com/…"')}
    <label class="field">Набор участников<select name="recruitment_status">${["unknown", "open", "closed"].map(value => html`<option value="${value}">${projectLabel(value)}</option>`).join("")}</select></label>
    ${input("commitment", t("Время на участие"), "text", 'maxlength="100"')}${input("experience_level", t("Опыт участников"), "text", 'maxlength="50"')}
    <label class="checkbox"><input name="public" type="checkbox">Опубликовать проект</label><button>${project ? t("Сохранить изменения") : t("Создать проект")}</button></form>`;
  const form = root.querySelector("form");
  if (project) {
    ["title", "summary", "description", "status", "stage", "source_url", "recruitment_status", "commitment", "experience_level"].forEach(key => { form.elements[key].value = project[key] || ""; });
    ["tags", "skills"].forEach(key => { form.elements[key].value = project[key].join(", "); });
    form.elements.public.checked = project.visibility === "public";
  }
  bindForm(form, async data => {
    const body = Object.fromEntries(["title", "summary", "description", "status", "stage", "recruitment_status"].map(key => [key, data.get(key)]));
    ["source_url", "commitment", "experience_level"].forEach(key => { body[key] = data.get(key).trim() || null; });
    body.visibility = data.has("public") ? "public" : "draft";
    ["tags", "skills"].forEach(key => { body[key] = [...new Set(data.get(key).split(",").map(value => value.trim()).filter(Boolean))]; });
    if (!project) body.slug = data.get("slug").trim();
    const saved = await api(project ? "/projects/" + encodeURIComponent(slug) : "/projects", { method: project ? "PATCH" : "POST", body });
    toast(t("Проект сохранён."));
    go("project/" + saved.slug);
  });
}
