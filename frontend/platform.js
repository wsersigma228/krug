/* Real team, community and event discovery; requests use the native API directly. */
const platformConfig = {
  team: { plural: "teams", label: "Команда", list: "Команды", detail: "team", types: "/teams" },
  community: { plural: "communities", label: "Сообщество", list: "Сообщества", detail: "community", types: "/communities" },
  event: { plural: "events", label: "Событие", list: "События", detail: "event", types: "/events" },
  project: { plural: "projects", label: "Проект", detail: "project", types: "/discovery" },
};
function platformRoute(kind, slug) { return kind === "person" ? "profile/" + slug : kind === "project" ? "project/" + slug : kind + "/" + slug; }
function platformTitle(kind) { return t(platformConfig[kind]?.label || "Человек"); }
function platformUrl(kind, slug) { return "/app#" + platformRoute(kind, slug); }
function platformStatus(kind, status) {
  const labels = kind === "team" ? { recruiting: "Ищет участников", active: "Активна", archived: "В архиве" } : { scheduled: "Запланировано", active: "Идёт сейчас", ended: "Завершено", cancelled: "Отменено" };
  return t(labels[status] || status || "");
}
function platformEventType(type) {
  const labels = { hackathon: "\u0425\u0430\u043a\u0430\u0442\u043e\u043d", game_jam: "\u0414\u0436\u0435\u0439\u043c-\u0438\u0433\u0440\u0430", meetup: "\u0412\u0441\u0442\u0440\u0435\u0447\u0430", other: "\u0414\u0440\u0443\u0433\u043e\u0435" };
  return t(labels[type] || type || "");
}
function platformFormat(format) {
  const labels = { online: "Онлайн", local: "На месте", hybrid: "Гибридный", unspecified: "Не указан" };
  return t(labels[format] || format || "");
}
function platformApplicationStatus(status) {
  const labels = { pending: "Ожидает решения", accepted: "Принята", rejected: "Отклонена", withdrawn: "Отозвана" };
  return t(labels[status] || status || "");
}
function platformTags(entity) {
  const tags = [...(entity.topics || entity.tags || []), ...(entity.skills || [])];
  return tags.length ? html`<div class="project-tags">${tags.slice(0, 6).map(tag => html`<span class="project-tag">${esc(tag)}</span>`).join("")}</div>` : "";
}
function platformCover(entity, kind, compact = false) {
  const glyph = kind === "project" ? "folder" : kind === "team" ? "people" : kind === "event" ? "calendar" : "community";
  if (!entity?.cover_url) return html`<div class="platform-cover-fallback${compact ? " compact" : ""}" aria-label="${platformTitle(kind)}">${icon(glyph)}</div>`;
  const source = entity.visibility === "draft" ? 'data-private-cover="' + esc(entity.cover_url) + '" data-cover-kind="' + kind + '"' : 'src="' + esc(entity.cover_url) + '"';
  return html`<img class="platform-cover${compact ? " compact" : ""}" ${source} alt="" loading="lazy">`;
}
async function hydratePlatformCovers(root, stamp) {
  if (!root) return;
  for (const img of root.querySelectorAll("img[data-private-cover]:not([data-cover-loading])")) {
    img.dataset.coverLoading = "true";
    try {
      const blob = await api(img.dataset.privateCover, { blob: true });
      if (stamp !== generation || !img.isConnected) continue;
      const url = URL.createObjectURL(blob);
      objectURLs.push(url);
      img.src = url;
      delete img.dataset.privateCover;
      delete img.dataset.coverKind;
      delete img.dataset.coverLoading;
    } catch {
      if (stamp !== generation || !img.isConnected) continue;
      const kind = img.dataset.coverKind;
      const glyph = kind === "project" ? "folder" : kind === "team" ? "people" : kind === "event" ? "calendar" : "community";
      const fallback = document.createElement("div");
      fallback.className = "platform-cover-fallback" + (img.classList.contains("compact") ? " compact" : "");
      fallback.setAttribute("aria-label", platformTitle(kind));
      fallback.innerHTML = icon(glyph);
      img.replaceWith(fallback);
    }
  }
}
function platformCard(entity, kind) {
  if (kind === "person") {
    const name = entity.display_name || entity.username;
    const intent = { looking_for_teammates:"Ищу участников в проект", looking_for_project:"Ищу проект", open_to_collaboration:"Открыт к сотрудничеству", interested_in_event:"Интересуюсь мероприятиями" }[entity.intent_kind];
    return html`<article class="platform-card platform-person"><a class="platform-avatar" href="/app#profile/${entity.id}" aria-label="${t("Профиль")} ${esc(name)}">${entity.avatar_url ? html`<img src="${esc(entity.avatar_url)}" alt="">` : esc(name[0]?.toUpperCase())}</a><div class="platform-card-copy"><div class="platform-card-meta"><span>${t("Человек")}</span><span>@${esc(entity.username)}</span></div><h3><a href="/app#profile/${entity.id}">${esc(name)}</a></h3>${intent ? html`<p class="platform-card-meta">${t(intent)}</p>` : ""}<p class="platform-card-summary">${esc(entity.intent_text || entity.bio || "")}</p>${platformTags(entity)}<p class="hint">${[entity.timezone, entity.commitment].filter(Boolean).map(esc).join(" · ")}</p></div><a class="project-open" href="/app#profile/${entity.id}">${t("Профиль")}${icon("arrow")}</a></article>`;
  }
  if (kind === "opening") {
    const related = entity.project || entity.team;
    const relatedKind = entity.project ? "project" : "team";
    const href = related?.slug ? platformUrl(relatedKind, related.slug) : "/app#explore?kind=projects";
    const context = related ? html`<p class="hint">${entity.project ? t("Проект") : t("Команда")}: ${esc(related.title)}</p>` : "";
    return html`<article class="platform-card platform-card-opening"><div class="platform-card-meta"><span>${t("Открытая роль")}</span><span>${esc(entity.commitment || "")}</span></div>${platformCover(related, relatedKind)}<div class="platform-card-copy"><h3><a href="${href}">${esc(entity.title || entity.role)}</a></h3><p class="platform-card-summary">${esc(entity.description || related?.summary || "")}</p>${context}${platformTags(entity)}</div><a class="project-open" href="${href}">${t("Посмотреть и откликнуться")}${icon("arrow")}</a></article>`;
  }
  const href = platformUrl(kind, entity.slug);
  const count = kind === "project" ? [[entity.member_count, "участников"], [entity.open_roles_count, "открытых ролей"]] : kind === "team" ? [[entity.member_count, "участников"], [entity.openings_count, "открытых ролей"]] : kind === "community" ? [[entity.member_count, "участников"], [entity.published_posts_count, "публикаций"]] : [];
  const meta = kind === "project" ? entity.origin === "external" ? t("Внешний проект") : t("Проект") : platformTitle(kind);
  const status = kind === "event" ? entity.status : kind === "project" || kind === "team" ? entity.status : "";
  const facts = kind === "event" ? [entity.starts_at && date(entity.starts_at), entity.format && t({ online:"Онлайн", local:"На месте", hybrid:"Гибридный" }[entity.format]), entity.location].filter(Boolean) : kind === "team" ? [entity.format && t({ online:"Онлайн", local:"На месте", hybrid:"Гибридный" }[entity.format]), entity.location].filter(Boolean) : [];
  const action = kind === "event" ? t("О событии") : kind === "team" ? t("Смотреть команду") : kind === "community" ? t("Открыть сообщество") : t("Подробнее");
  const glyph = kind === "project" ? "folder" : kind === "team" ? "people" : kind === "event" ? "calendar" : "community";
  const saveButton = session && ["project", "team", "community", "event"].includes(kind) ? html`<button class="save-platform" data-platform-save="${kind}" data-slug="${esc(entity.slug)}" aria-pressed="false" aria-label="${t("Сохранить")}" title="${t("Сохранить")}">${icon("bookmark")}</button>` : "";
  return html`<article class="platform-card platform-card-${kind}" data-platform-kind="${kind}" data-platform-slug="${esc(entity.slug)}">
    <div class="platform-card-topline"><div class="platform-card-kind">${icon(glyph)}<span>${meta}</span>${status ? html`<span class="project-status" data-status="${esc(status)}">${esc(kind === "project" ? projectLabel(status) : platformStatus(kind, status))}</span>` : ""}${kind === "project" && entity.origin === "external" && entity.source_name ? html`<span>${esc(entity.source_name)}</span>` : ""}</div>${saveButton}</div>
    <div class="platform-card-media">${platformCover(entity, kind)}</div><div class="platform-card-copy">
      <h3><a href="${href}">${esc(entity.title)}</a></h3><p class="platform-card-summary">${esc(entity.summary || "")}</p>${facts.length ? html`<p class="platform-card-meta">${facts.map(esc).join(" · ")}</p>` : ""}${platformTags(entity)}
      ${count.some(([value]) => Number.isInteger(value)) ? html`<div class="platform-card-counts">${count.filter(([value]) => Number.isInteger(value) && value > 0).map(([value, label]) => html`<span>${value} ${t(label)}</span>`).join("")}</div>` : ""}
      ${kind === "project" && entity.origin === "external" ? html`<p class="hint">${t("Источник не означает, что авторы набирают команду.")}</p>` : ""}</div>
    <div class="platform-card-actions"><a class="project-open" href="${href}">${action}${icon("arrow")}</a></div>
  </article>`;
}
function platformEventRow(event) {
  return html`<article class="upcoming-event"><a class="upcoming-event-cover" href="${platformUrl("event", event.slug)}">${platformCover(event, "event", true)}</a><div><a class="upcoming-event-title" href="${platformUrl("event", event.slug)}">${esc(event.title)}</a><p class="hint">${[event.starts_at && date(event.starts_at), event.format === "online" ? t("Онлайн") : event.location].filter(Boolean).map(esc).join(" · ")}</p><a class="upcoming-find-team" href="/app#teams?event_id=${event.id}">${t("Найти команду")}</a></div></article>`;
}
async function bindPlatformSaves(root, stamp) {
  const buttons = [...root.querySelectorAll("[data-platform-save]")].filter(button => button.dataset.platformSaveBound !== "true");
  buttons.forEach(button => { button.dataset.platformSaveBound = "true"; });
  for (const button of buttons) {
    const platformSavePath = await platformState(button.dataset.platformSave, button.dataset.slug).catch(() => null);
    if (stamp !== generation || !button.isConnected) return;
    if (!platformSavePath) { button.hidden = true; continue; }
    button.dataset.path = platformSavePath.path;
    button.setAttribute("aria-pressed", String(Boolean(platformSavePath.state.saved)));
    button.classList.toggle("saved", Boolean(platformSavePath.state.saved));
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const saved = button.getAttribute("aria-pressed") !== "true";
        const state = await api(button.dataset.path, { method: "PATCH", body: { saved } });
        button.setAttribute("aria-pressed", String(state.saved));
        button.classList.toggle("saved", state.saved);
        button.title = t(state.saved ? "Сохранено" : "Сохранить");
      } catch (error) { toast(errorText(error)); }
      finally { button.disabled = false; }
    });
  }
}
async function platformState(kind, slug) {
  const config = platformConfig[kind];
  const path = `/${config.plural}/${encodeURIComponent(slug)}/engagement`;
  return { path, state: await api(path) };
}
function platformCardGrid(items, kind) {
  return items.length ? html`<div class="project-grid">${items.map(item => platformCard(item, kind)).join("")}</div>` : empty(t("Здесь пока пусто"), t("Публичные материалы появятся, когда участники их добавят."));
}
function communityPostCard(post, slug) {
  const route = `/app#post/${post.id}`;
  const context = `?community=${encodeURIComponent(slug)}`;
  return postCard(post).replaceAll(`${route}?comments=1`, `${route}${context}&comments=1`).replaceAll(`${route}"`, `${route}${context}"`).replaceAll(`/app#edit/${post.id}"`, `/app#edit/${post.id}${context}"`);
}
function platformLoadMore(container, initialPage, fetchPage, renderItems, afterAppend = async () => {}) {
  let cursor = initialPage?.next_cursor;
  if (!initialPage?.has_more || !cursor) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary load-more";
  button.textContent = t("Показать ещё");
  container.append(button);
  actionButton(button, async () => {
    button.disabled = true;
    try {
      const page = await fetchPage(cursor);
      const markup = page.items.map(renderItems).join("");
      button.insertAdjacentHTML("beforebegin", markup);
      await hydratePlatformCovers(container, generation);
      cursor = page.next_cursor;
      await afterAppend();
      if (!page.has_more || !cursor) button.remove();
      else button.disabled = false;
    } catch (error) {
      button.disabled = false;
      toast(errorText(error));
    }
  });
}
function bindCommunityModeration(container) {
  container.querySelectorAll(".post-card").forEach(card => {
    const id = card.querySelector("[data-like]")?.dataset.like;
    if (!id || card.querySelector("[data-community-moderate]")) return;
    const button = document.createElement("button"); button.type = "button"; button.className = "text-button"; button.dataset.communityModerate = id; button.textContent = t("Удалить публикацию"); card.querySelector(".toolbar")?.append(button);
    actionButton(button, async () => { await api(`/posts/${id}`, { method: "DELETE" }); card.remove(); });
  });
}
async function platformListScreen(kind, query, root, stamp) {
  const config = platformConfig[kind];
  const params = new URLSearchParams();
  for (const key of ["search", "skill", "language", "format", "event_id"]) if (query.has(key)) params.set(key, query.get(key));
  params.set("limit", "24");
  const page = await api(config.types + "?" + params);
  if (stamp !== generation) return;
  const createRoute = kind === "team" ? "team-new" : kind === "event" ? "event-new" : "community-new";
  const createLabel = kind === "team" ? t("Создать команду") : kind === "event" ? t("Создать событие") : t("Создать сообщество");
  root.innerHTML = html`<section class="platform-list-heading"><div><h1>${t(config.list)}</h1><p class="intro">${kind === "team" ? t("Найдите людей, которые работают над общей задачей.") : kind === "event" ? t("Встречи и события, опубликованные участниками.") : t("Места, где участники делятся знаниями и публикациями.")}</p></div>${session ? html`<a class="button" href="/app#${createRoute}">${icon("plus")} ${createLabel}</a>` : html`<a class="button" href="/app#login?next=${createRoute}">${t("Войти, чтобы создать")}</a>`}</section>
    <form class="discovery-search platform-list-search" role="search"><label class="field"><span>${t("Поиск")}</span><input name="search" value="${esc(query.get("search") || "")}" maxlength="100" placeholder="${t("Название, навык или тема")}"></label><button>${icon("explore")} ${t("Найти")}</button></form>
    <div class="discovery-results-heading"><h2>${t("Открытые для участников")}</h2></div><div id="platform-list-results">${platformCardGrid(page.items, kind)}</div>`;
  bindForm(root.querySelector(".platform-list-search"), async data => { const next = new URLSearchParams(query); const search = data.get("search").trim(); if (search) next.set("search", search); else next.delete("search"); go(`${kind === "team" ? "teams" : kind === "event" ? "events" : "communities"}?${next}`); });
  bindPlatformSaves(root.querySelector("#platform-list-results"), stamp);
}
function platformFormMarkup(kind, entity, events = []) {
  const team = kind === "team", event = kind === "event";
  const fields = html`<div class="platform-form-grid">${input("slug", t("Короткий адрес"), "text", `required maxlength="80" pattern="[a-z0-9-]+" ${entity ? "readonly" : ""}`)}${input("title", t("Название"), "text", 'required maxlength="160"')}</div>
    ${input("summary", t("Кратко"), "text", 'required maxlength="500"')}<label class="field">${t("Описание")}<textarea name="description" maxlength="20000"></textarea></label>
    ${input("topics", t("Темы через запятую"), "text", 'maxlength="1000"')}${input("skills", t("Навыки через запятую"), "text", 'maxlength="1000"')}${input("languages", t("Языки через запятую"), "text", 'maxlength="500"')}
    <div class="platform-form-grid"><label class="field">${t("Формат")}<select name="format"><option value="online">${t("Онлайн")}</option><option value="local">${t("На месте")}</option><option value="hybrid">${t("Гибридный")}</option></select></label>${input("location", t("Место или город"), "text", 'maxlength="160"')}</div>
    ${team ? html`<div class="platform-form-grid"><label class="field">${t("Состояние набора")}<select name="status"><option value="recruiting">${t("Ищет участников")}</option><option value="active">${t("Активна")}</option><option value="archived">${t("В архиве")}</option></select></label><label class="field">${t("Встреча или джем")}<select name="event_id"><option value="">${t("Без события")}</option>${events.map(item => html`<option value="${item.id}">${esc(item.title)} · ${date(item.starts_at)}</option>`).join("")}</select></label></div>${input("commitment", t("Время на участие"), "text", 'maxlength="100"')}` : ""}
    ${event ? html`<div class="platform-form-grid"><label class="field">${t("Тип события")}<select name="type" required><option value="hackathon">${t("Хакатон")}</option><option value="game_jam">${t("Джейм-игра")}</option><option value="meetup">${t("Встреча")}</option><option value="other">${t("Другое")}</option></select></label>${input("timezone", t("Часовой пояс"), "text", 'maxlength="80"')}</div><div class="platform-form-grid">${input("starts_at", t("Начало"), "datetime-local", "required")}${input("ends_at", t("Окончание"), "datetime-local", "required")}</div>${input("deadline", t("Дедлайн регистрации"), "datetime-local")}${input("participation_url", t("Ссылка для участия"), "url", 'maxlength="2048"')}<div class="platform-form-grid"><label class="field">${t("Происхождение") }<select name="origin" ${entity ? "disabled" : ""}><option value="native">${t("Событие участника")}</option><option value="external">${t("Внешнее событие")}</option></select></label>${input("source_name", t("Организатор или источник"), "text", 'maxlength="40"')}</div>${input("source_url", t("Страница организатора или первоисточник"), "url", 'maxlength="2048"')}<label class="field">${t("Статус")}<select name="status"><option value="scheduled">${t("Запланировано")}</option><option value="active">${t("Идёт сейчас")}</option><option value="ended">${t("Завершено")}</option><option value="cancelled">${t("Отменено")}</option></select></label>` : ""}
    <label class="field">${t("Доступность")}<select name="visibility"><option value="public">${t("Публично")}</option><option value="draft">${t("Черновик")}</option></select></label>
    <label class="field">${t("Обложка — необязательно, до 8 МиБ")}<input name="cover" type="file" accept="image/jpeg,image/png,image/webp"></label>${entity?.cover_url ? html`<div class="cover-editor">${platformCover(entity, kind)}<button type="button" class="secondary" data-remove-cover>${t("Удалить обложку")}</button></div>` : ""}`;
  return html`<form class="form project-editor platform-editor" data-platform-form="${kind}">${fields}<button>${entity ? t("Сохранить изменения") : t("Создать")}</button><p class="hint" role="status" data-cover-status></p></form>`;
}
function platformFormBody(kind, data) {
  const list = value => [...new Set(value.split(",").map(item => item.trim()).filter(Boolean))];
  const body = { title: data.get("title").trim(), summary: data.get("summary").trim(), description: data.get("description").trim(), topics: list(data.get("topics")), skills: list(data.get("skills")), languages: list(data.get("languages")), format: data.get("format"), location: data.get("location").trim() || null, visibility: data.get("visibility") };
  if (kind === "team") Object.assign(body, { status: data.get("status"), commitment: data.get("commitment").trim() || null, event_id: data.get("event_id") ? Number(data.get("event_id")) : null });
  if (kind === "event") Object.assign(body, { type: data.get("type"), timezone: data.get("timezone").trim() || null, starts_at: new Date(data.get("starts_at")).toISOString(), ends_at: new Date(data.get("ends_at")).toISOString(), deadline: data.get("deadline") ? new Date(data.get("deadline")).toISOString() : null, participation_url: data.get("participation_url").trim() || null, origin: data.get("origin") || "native", source_name: data.get("source_name").trim() || null, source_url: data.get("source_url").trim() || null, status: data.get("status") || "scheduled" });
  return body;
}
function fillPlatformForm(form, entity) {
  for (const key of ["slug", "title", "summary", "description", "format", "location", "visibility", "status", "commitment", "event_id", "type", "timezone", "starts_at", "ends_at", "deadline", "participation_url", "origin", "source_name", "source_url"]) {
    if (!form.elements[key]) continue;
    let value = entity[key];
    if (["starts_at", "ends_at", "deadline"].includes(key) && value) { const local = new Date(value); local.setMinutes(local.getMinutes() - local.getTimezoneOffset()); value = local.toISOString().slice(0, 16); }
    form.elements[key].value = value ?? (key === "visibility" ? "public" : key === "format" ? "online" : key === "origin" ? "native" : "");
  }
  for (const key of ["topics", "skills", "languages"]) if (form.elements[key]) form.elements[key].value = (entity[key] || []).join(", ");
}
async function uploadPlatformCover(kind, slug, file) {
  if (!file || !file.size) return;
  if (file.size > 8 * 1024 * 1024) throw new Error(t("Фото должно быть не больше 8 МиБ."));
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) throw new Error(t("Выберите изображение JPEG, PNG или WebP."));
  return api(`/${platformConfig[kind].plural}/${encodeURIComponent(slug)}/cover`, { method: "PUT", body: file, headers: { "Content-Type": file.type } });
}
async function platformEditorScreen(kind, slug, query, root, stamp) {
  let entity = slug ? await api(`/${platformConfig[kind].plural}/${encodeURIComponent(slug)}`) : null;
  let events = [];
  if (kind === "team") try { events = (await api("/events?upcoming=true&limit=50")).items; } catch { /* Linking remains optional when the event list is unavailable. */ }
  if (stamp !== generation) return;
  const back = kind === "team" ? "teams" : kind === "community" ? "communities" : "explore?kind=events";
  root.innerHTML = html`<a class="back" href="/app#${back}">${icon("arrow")} ${t("Назад")}</a><section class="platform-form-heading"><h1>${entity ? t("Редактировать") : t("Создать")} ${platformTitle(kind).toLocaleLowerCase(language === "ru" ? "ru-RU" : "en-US")}</h1><p class="intro">${t("Публикуйте только сведения, подтверждённые вами. Можно начать без обложки.")}</p></section>${platformFormMarkup(kind, entity, events)}`;
  const form = root.querySelector("form");
  if (entity) fillPlatformForm(form, entity);
  else {
    form.elements.slug.value = query.get("slug") || "";
    if (kind === "team" && query.get("event")) form.elements.event_id.value = query.get("event");
  }
  const remove = form.querySelector("[data-remove-cover]");
  if (remove) actionButton(remove, async () => { await api(`/${platformConfig[kind].plural}/${encodeURIComponent(entity.slug)}/cover`, { method: "DELETE" }); toast(t("Обложка удалена.")); go(kind + "-edit/" + entity.slug); });
  bindForm(form, async data => {
    const creating = !entity;
    const body = platformFormBody(kind, data);
    if (!creating && kind === "event") delete body.origin;
    if (creating) body.slug = data.get("slug").trim();
    entity = await api(`/${platformConfig[kind].plural}${creating ? "" : "/" + encodeURIComponent(entity.slug)}`, { method: creating ? "POST" : "PATCH", body });
    try { await uploadPlatformCover(kind, entity.slug, data.get("cover")); }
    catch (error) { form.querySelector("[data-cover-status]").textContent = t("Запись сохранена. Обложка не загрузилась: исправьте файл и отправьте форму ещё раз."); throw error; }
    toast(t("Изменения сохранены.")); go(kind + "/" + entity.slug);
  });
}
function platformMemberCard(member) {
  const label = member.display_name || member.username;
  return html`<a class="platform-member" href="/app#profile/${member.user_id}"><span class="platform-avatar">${member.avatar_url ? html`<img src="${esc(member.avatar_url)}" alt="">` : esc(label[0]?.toUpperCase() || "?")}</span><span><strong>${esc(label)}</strong>${member.role ? html`<small>${esc(member.role)}</small>` : ""}</span></a>`;
}
function bindPlatformEngagement(kind, slug, state, root) {
  const fields = ["team", "event"].includes(kind) ? ["saved", "interested", "interested_visible"] : ["saved"];
  root.innerHTML = html`<form class="form engagement-form platform-engagement">${fields.map(key => html`<label class="checkbox"><input type="checkbox" name="${key}" ${state[key] ? "checked" : ""} ${key === "interested_visible" && !state.interested ? "disabled" : ""}>${t({ saved:"Сохранить", interested:kind === "team" ? "Мне интересна команда" : "Планирую участвовать", interested_visible:"Показать мой интерес другим" }[key])}</label>`).join("")}<button class="secondary">${t("Сохранить выбор")}</button><span class="hint" role="status"></span></form>`;
  const form = root.querySelector("form");
  if (form.elements.interested && form.elements.interested_visible) form.elements.interested.addEventListener("change", () => { form.elements.interested_visible.disabled = !form.elements.interested.checked; if (!form.elements.interested.checked) form.elements.interested_visible.checked = false; });
  bindForm(form, async data => {
    const body = Object.fromEntries(fields.map(key => [key, data.has(key)]));
    const updated = await api(`/${platformConfig[kind].plural}/${encodeURIComponent(slug)}/engagement`, { method: "PATCH", body });
    form.querySelector('[role="status"]').textContent = t("Выбор сохранён.");
    for (const key of fields) if (form.elements[key]) form.elements[key].checked = Boolean(updated[key]);
  });
}
function openingMarkup(opening, team, own) {
  return html`<article class="team-opening"><div class="project-card-meta"><span>${esc(opening.title || opening.role)}</span><span class="badge">${t(opening.status === "open" ? "Набор открыт" : "Набор закрыт")}</span></div><p class="platform-card-summary">${esc(opening.description || "")}</p>${platformTags(opening)}${opening.commitment ? html`<p class="hint">${esc(opening.commitment)}</p>` : ""}
    ${own ? html`<button class="secondary" data-opening-toggle="${opening.id}" data-status="${opening.status === "open" ? "closed" : "open"}">${t(opening.status === "open" ? "Закрыть набор" : "Открыть набор")}</button>` : opening.status === "open" ? session ? html`<form class="form team-application-form" data-opening-apply="${opening.id}"><label class="field">${t("Почему вам интересна эта роль?")}<textarea name="message" required maxlength="5000"></textarea></label><button>${t("Отправить заявку")}</button></form>` : html`<a class="button" href="/app#login?next=${encodeURIComponent("team/" + team.slug)}">${t("Войти и откликнуться")}</a>` : html`<p class="hint">${t("Набор закрыт.")}</p>`}
  </article>`;
}
function bindTeamOpenings(container, team, own) {
  container.querySelectorAll("[data-opening-toggle]").forEach(button => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";
    actionButton(button, async () => { await api(`/team-openings/${button.dataset.openingToggle}`, { method: "PATCH", body: { status: button.dataset.status } }); go("team/" + team.slug); });
  });
  container.querySelectorAll("[data-opening-apply]").forEach(form => {
    if (form.dataset.bound === "true") return;
    form.dataset.bound = "true";
    bindForm(form, async data => { await api(`/team-openings/${form.dataset.openingApply}/applications`, { method: "POST", body: { message: data.get("message").trim() } }); form.innerHTML = `<p class="success" role="status">${t("Заявка отправлена владельцу команды.")}</p>`; });
  });
}
function bindTeamApplications(section, slug) {
  section.querySelectorAll("[data-application]").forEach(button => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";
    actionButton(button, async () => { await api(`/team-applications/${button.dataset.application}`, { method: "PATCH", body: { status: button.dataset.status } }); go("team/" + slug); });
  });
}
async function teamDetailScreen(team, root, stamp) {
  const own = me?.id === team.owner_id;
  const [openingResult, memberResult] = await Promise.allSettled([api(`/teams/${encodeURIComponent(team.slug)}/openings?limit=50`), api(`/teams/${encodeURIComponent(team.slug)}/members?limit=50`)]);
  if (stamp !== generation) return;
  const openings = openingResult.status === "fulfilled" ? openingResult.value.items : [];
  const members = memberResult.status === "fulfilled" ? memberResult.value.items : [];
  root.innerHTML = html`<a class="back" href="/app#teams">${icon("arrow")} ${t("Все команды")}</a><article class="platform-detail"><div>${platformCover(team, "team")}<div class="platform-detail-meta"><span>${t("Команда")}</span><span class="project-status" data-status="${esc(team.status)}">${platformStatus("team", team.status)}</span></div><h1>${esc(team.title)}</h1><p class="project-lead">${esc(team.summary)}</p>${platformTags(team)}<div class="platform-counts">${Number.isInteger(team.member_count) ? html`<span>${team.member_count} ${t("участников")}</span>` : ""}${Number.isInteger(team.openings_count) ? html`<span>${team.openings_count} ${t("открытых ролей")}</span>` : ""}${Number.isInteger(team.interested_count) ? html`<span>${team.interested_count} ${t("заинтересованы")}</span>` : ""}</div>${team.description ? html`<div class="project-description">${esc(team.description)}</div>` : ""}<dl class="project-facts">${team.format ? html`<div><dt>${t("Формат")}</dt><dd>${platformFormat(team.format)}</dd></div>` : ""}${team.location ? html`<div><dt>${t("Место")}</dt><dd>${esc(team.location)}</dd></div>` : ""}${team.commitment ? html`<div><dt>${t("Время на участие")}</dt><dd>${esc(team.commitment)}</dd></div>` : ""}${team.languages?.length ? html`<div><dt>${t("Языки")}</dt><dd>${team.languages.map(esc).join(", ")}</dd></div>` : ""}</dl>
      <section class="platform-detail-section"><div class="discovery-results-heading"><h2>${t("Участники")}</h2><span class="hint">${Number.isInteger(team.member_count) ? team.member_count : members.length}</span></div><div class="platform-member-list">${members.length ? members.map(platformMemberCard).join("") : `<p class="hint">${t("Пока нет участников.")}</p>`}${memberResult.status === "rejected" ? `<p class="error" role="alert">${esc(errorText(memberResult.reason))}</p>` : ""}</div></section>
      <section class="platform-detail-section"><div class="discovery-results-heading"><h2>${t("Открытые роли")}</h2>${own ? html`<a class="text-button" href="#team-opening-form">${icon("plus")} ${t("Добавить роль")}</a>` : ""}</div><div id="team-openings">${openingResult.status === "fulfilled" ? openings.length ? openings.map(opening => openingMarkup(opening, team, own)).join("") : `<p class="hint">${t("Сейчас нет открытых ролей.")}</p>` : `<p class="error" role="alert">${esc(errorText(openingResult.reason))}</p>`}</div>
        ${own ? html`<form class="form platform-inline-form" id="team-opening-form"><h3>${t("Опубликовать роль")}</h3>${input("title", t("Название роли"), "text", 'required maxlength="120"')}${input("skills", t("Навыки через запятую"), "text", 'maxlength="1000"')}<label class="field">${t("Описание роли")}<textarea name="description" maxlength="5000"></textarea></label>${input("commitment", t("Время на участие"), "text", 'maxlength="100"')}<button>${t("Опубликовать")}</button></form>` : ""}</section>
    </div><aside class="platform-side-panel"><h2>${own ? t("Управление командой") : t("Присоединяйтесь")}</h2><div id="team-engagement">${session ? `<p class="hint">${t("Загружаем…")}</p>` : html`<a class="button" href="/app#login?next=${encodeURIComponent("team/" + team.slug)}">${t("Войти, чтобы сохранить интерес")}</a>`}</div>${own ? html`<div class="platform-owner-actions"><a class="button secondary" href="/app#team-edit/${esc(team.slug)}">${t("Редактировать")}</a><details><summary>${t("Перенести команду в проект")}</summary><form class="form" id="team-project-transfer">${input("slug", t("Короткий адрес проекта"), "text", 'required maxlength="80" pattern="[a-z0-9-]+"')}${input("title", t("Название проекта"), "text", 'required maxlength="160"')}${input("summary", t("Краткое описание"), "text", 'required maxlength="500"')}<label class="field">${t("Описание")}</label><textarea name="description" maxlength="20000"></textarea><button>${t("Создать проект и перенести участников")}</button></form></details><button type="button" class="danger" id="team-delete">${t("Удалить команду")}</button></div>` : ""}</aside></article>`;
  const deleteTeam = root.querySelector("#team-delete");
  if (memberResult.status === "fulfilled") platformLoadMore(root.querySelector(".platform-member-list"), memberResult.value, cursor => api(`/teams/${encodeURIComponent(team.slug)}/members?limit=50&cursor=${encodeURIComponent(cursor)}`), platformMemberCard);
  if (openingResult.status === "fulfilled") platformLoadMore(root.querySelector("#team-openings"), openingResult.value, cursor => api(`/teams/${encodeURIComponent(team.slug)}/openings?limit=50&cursor=${encodeURIComponent(cursor)}`), opening => openingMarkup(opening, team, own), async () => bindTeamOpenings(root.querySelector("#team-openings"), team, own));
  if (deleteTeam) actionButton(deleteTeam, async () => { if (!confirm(`${t("Удалить команду")}: «${team.title}»?\n\n${t("Страница, роли, заявки и состав будут удалены.")}`)) return; await api(`/teams/${encodeURIComponent(team.slug)}`, { method: "DELETE" }); toast(t("Команда удалена.")); go("teams"); });
  bindTeamOpenings(root.querySelector("#team-openings"), team, own);
  const openingForm = root.querySelector("#team-opening-form");
  if (openingForm) bindForm(openingForm, async data => { await api(`/teams/${encodeURIComponent(team.slug)}/openings`, { method: "POST", body: { title: data.get("title").trim(), role: data.get("title").trim(), skills: data.get("skills").split(",").map(value => value.trim()).filter(Boolean), commitment: data.get("commitment").trim() || null, description: data.get("description").trim() } }); go("team/" + team.slug); });
  if (session) try { const state = await api(`/teams/${encodeURIComponent(team.slug)}/engagement`); if (stamp === generation) bindPlatformEngagement("team", team.slug, state, root.querySelector("#team-engagement")); } catch (error) { if (stamp === generation) root.querySelector("#team-engagement").innerHTML = `<p class="error" role="alert">${esc(errorText(error))}</p>`; }
  if (own) {
    const [applicationResult] = await Promise.allSettled([api(`/teams/${encodeURIComponent(team.slug)}/applications?limit=50`)]);
    if (stamp !== generation) return;
    const section = document.createElement("section"); section.className = "platform-detail-section team-owner-applications";
    section.innerHTML = html`<h2>${t("Заявки на роли")}</h2>${applicationResult.status === "fulfilled" ? applicationResult.value.items.length ? applicationResult.value.items.map(application => html`<article class="team-application"><strong>${esc(application.opening_title)}</strong><p>${esc(application.message)}</p><p class="hint"><a href="/app#profile/${application.applicant_id}">${t("Профиль участника")}</a> · ${platformApplicationStatus(application.status)}</p>${application.status === "pending" ? html`<button data-application="${application.id}" data-status="accepted">${t("Принять")}</button><button class="secondary" data-application="${application.id}" data-status="rejected">${t("Отклонить")}</button>` : ""}</article>`).join("") : `<p class="hint">${t("Новых заявок пока нет.")}</p>` : `<p class="error" role="alert">${esc(errorText(applicationResult.reason))}</p>`}`;
    root.querySelector(".platform-detail").append(section);
    bindTeamApplications(section, team.slug);
    if (applicationResult.status === "fulfilled") platformLoadMore(section, applicationResult.value, cursor => api(`/teams/${encodeURIComponent(team.slug)}/applications?limit=50&cursor=${encodeURIComponent(cursor)}`), application => html`<article class="team-application"><strong>${esc(application.opening_title)}</strong><p>${esc(application.message)}</p><p class="hint"><a href="/app#profile/${application.applicant_id}">${t("Профиль участника")}</a> · ${platformApplicationStatus(application.status)}</p>${application.status === "pending" ? html`<button data-application="${application.id}" data-status="accepted">${t("Принять")}</button><button class="secondary" data-application="${application.id}" data-status="rejected">${t("Отклонить")}</button>` : ""}</article>`, async () => bindTeamApplications(section, team.slug));
  }
  const transfer = root.querySelector("#team-project-transfer");
  if (transfer) bindForm(transfer, async data => { const project = await api(`/teams/${encodeURIComponent(team.slug)}/project`, { method: "POST", body: { slug: data.get("slug").trim(), title: data.get("title").trim(), summary: data.get("summary").trim(), description: data.get("description").trim(), status: "active", stage: "idea", visibility: "public", recruitment_status: "unknown", tags: [], skills: team.skills || [], languages: team.languages || [], format: ["online", "local", "hybrid"].includes(team.format) ? team.format : "unspecified", location: team.location } }); toast(t("Проект создан, участников перенесли.")); go("project/" + project.slug); });
}
async function communityDetailScreen(community, root, stamp) {
  const [memberResult, postResult, membershipResult] = await Promise.allSettled([api(`/communities/${encodeURIComponent(community.slug)}/members?limit=100`), api(`/communities/${encodeURIComponent(community.slug)}/posts?limit=24`), session ? api(`/communities/${encodeURIComponent(community.slug)}/membership`) : Promise.resolve(null)]);
  if (stamp !== generation) return;
  const members = memberResult.status === "fulfilled" ? memberResult.value.items : [];
  const posts = postResult.status === "fulfilled" ? postResult.value.items : [];
  const membership = membershipResult.status === "fulfilled" ? membershipResult.value : null;
  const own = membership?.is_owner ?? me?.id === community.owner_id;
  const joined = Boolean(membership?.is_member);
  root.innerHTML = html`<a class="back" href="/app#communities">${icon("arrow")} ${t("Все сообщества")}</a><article class="platform-detail"><div>${platformCover(community, "community")}<div class="platform-detail-meta"><span>${t("Сообщество")}</span></div><h1>${esc(community.title)}</h1><p class="project-lead">${esc(community.summary)}</p>${platformTags(community)}<div class="platform-counts">${Number.isInteger(community.member_count) ? html`<span>${community.member_count} ${t("участников")}</span>` : ""}${Number.isInteger(community.published_posts_count) ? html`<span>${community.published_posts_count} ${t("публикаций")}</span>` : ""}</div>${community.description ? html`<div class="project-description">${esc(community.description)}</div>` : ""}<dl class="project-facts">${community.format ? html`<div><dt>${t("Формат")}</dt><dd>${platformFormat(community.format)}</dd></div>` : ""}${community.location ? html`<div><dt>${t("Место")}</dt><dd>${esc(community.location)}</dd></div>` : ""}${community.languages?.length ? html`<div><dt>${t("Языки")}</dt><dd>${community.languages.map(esc).join(", ")}</dd></div>` : ""}</dl>
      <section class="platform-detail-section"><div class="discovery-results-heading"><h2>${t("Участники")}</h2><span class="hint">${Number.isInteger(community.member_count) ? community.member_count : members.length}</span></div><div class="platform-member-list">${members.length ? members.map(platformMemberCard).join("") : `<p class="hint">${t("Пока нет участников.")}</p>`}${memberResult.status === "rejected" ? `<p class="error" role="alert">${esc(errorText(memberResult.reason))}</p>` : ""}</div></section>
      <section class="community-post-section"><div class="discovery-results-heading"><h2>${t("Публикации")}</h2>${joined ? html`<a class="button" href="/app#new?community_id=${community.id}&community=${encodeURIComponent(community.slug)}">${icon("plus")} ${t("Написать публикацию")}</a>` : ""}</div><div id="community-posts" class="post-grid">${posts.length ? posts.map(post => communityPostCard(post, community.slug)).join("") : postResult.status === "fulfilled" ? `<p class="hint">${t("Пока нет публикаций.")}</p>` : `<p class="error" role="alert">${esc(errorText(postResult.reason))}</p>`}</div></section>
    </div><aside class="platform-side-panel"><h2>${t("Сообщество")}</h2><p class="hint">${t("Публиковать могут только участники. Фото, комментарии и реакции доступны через редактор и карточки публикаций.")}</p>${own ? html`<p class="hint" role="status">${t("Вы владелец сообщества и остаетесь его участником.")}</p>` : session ? html`<button id="community-membership" class="${joined ? "secondary" : ""}" data-joined="${joined}">${joined ? t("Покинуть сообщество") : t("Присоединиться")}</button>` : html`<a class="button" href="/app#login?next=${encodeURIComponent("community/" + community.slug)}">${t("Войти, чтобы присоединиться")}</a>`}${session ? html`<div id="community-engagement"><p class="hint">${t("Загружаем…")}</p></div>` : ""}${own ? html`<a class="button secondary" href="/app#community-edit/${esc(community.slug)}">${t("Редактировать")}</a><button type="button" class="danger" id="community-delete">${t("Удалить сообщество")}</button>` : ""}</aside></article>`;
  const deleteCommunity = root.querySelector("#community-delete");
  if (deleteCommunity) actionButton(deleteCommunity, async () => { if (!confirm(`${t("Удалить сообщество")}: «${community.title}»?\n\n${t("Страница, публикации и комментарии будут удалены.")}`)) return; await api(`/communities/${encodeURIComponent(community.slug)}`, { method: "DELETE" }); toast(t("Сообщество удалено.")); go("communities"); });
  if (memberResult.status === "fulfilled") platformLoadMore(root.querySelector(".platform-member-list"), memberResult.value, cursor => api(`/communities/${encodeURIComponent(community.slug)}/members?limit=100&cursor=${encodeURIComponent(cursor)}`), platformMemberCard);
  if (session) {
    const membership = root.querySelector("#community-membership");
    if (membership) actionButton(membership, async () => { await api(`/communities/${encodeURIComponent(community.slug)}/membership`, { method: membership.dataset.joined === "true" ? "DELETE" : "PUT" }); go("community/" + community.slug); });
    try { const state = await api(`/communities/${encodeURIComponent(community.slug)}/engagement`); if (stamp === generation) bindPlatformEngagement("community", community.slug, state, root.querySelector("#community-engagement")); } catch (error) { if (stamp === generation) root.querySelector("#community-engagement").innerHTML = `<p class="error" role="alert">${esc(errorText(error))}</p>`; }
  }
  if (stamp !== generation) return;
  if (posts.length) { await hydratePhotos(root.querySelector("#community-posts"), stamp); await hydrateLikes(root.querySelector("#community-posts"), stamp); }
  if (own) bindCommunityModeration(root.querySelector("#community-posts"));
  if (postResult.status === "fulfilled") platformLoadMore(root.querySelector("#community-posts"), postResult.value, cursor => api(`/communities/${encodeURIComponent(community.slug)}/posts?limit=24&cursor=${encodeURIComponent(cursor)}`), post => communityPostCard(post, community.slug), async () => {
    const container = root.querySelector("#community-posts");
    await hydratePhotos(container, stamp);
    await hydrateLikes(container, stamp);
    if (own) bindCommunityModeration(container);
  });
}
async function eventDetailScreen(event, root, stamp) {
  const own = me?.id === event.owner_id;
  const [teamResult] = await Promise.allSettled([api(`/teams?event_id=${event.id}&limit=24`)]);
  if (stamp !== generation) return;
  const teams = teamResult.status === "fulfilled" ? teamResult.value.items : [];
  const source = event.source_url && /^https?:\/\//i.test(event.source_url) ? html`<a class="text-button" href="${esc(event.source_url)}" target="_blank" rel="noopener noreferrer">${t("Первоисточник")}: ${esc(event.source_name || new URL(event.source_url).hostname)} ${icon("arrow")}</a>` : "";
  root.innerHTML = html`<a class="back" href="/app#explore?kind=events">${icon("arrow")} ${t("Все события")}</a><article class="platform-detail"><div>${platformCover(event, "event")}<div class="platform-detail-meta"><span>${esc(event.source_name || t("Событие Круга"))}</span><span class="project-status" data-status="${esc(event.status)}">${platformStatus("event", event.status)}</span></div><h1>${esc(event.title)}</h1><p class="project-lead">${esc(event.summary)}</p>${platformTags(event)}<div class="platform-counts">${Number.isInteger(event.interested_count) ? html`<span>${event.interested_count} ${t("участников")}</span>` : ""}</div>${event.description ? html`<div class="project-description">${esc(event.description)}</div>` : ""}<dl class="project-facts"><div><dt>${t("Начало")}</dt><dd>${date(event.starts_at)} · ${new Date(event.starts_at).toLocaleTimeString(language === "ru" ? "ru-RU" : "en-US", { hour: "2-digit", minute: "2-digit" })} ${esc(event.timezone || "")}</dd></div><div><dt>${t("Окончание")}</dt><dd>${date(event.ends_at)}</dd></div>${event.deadline ? html`<div><dt>${t("Регистрация до")}</dt><dd>${date(event.deadline)}</dd></div>` : ""}${event.type ? html`<div><dt>${t("\u0422\u0438\u043f \u0441\u043e\u0431\u044b\u0442\u0438\u044f")}</dt><dd>${platformEventType(event.type)}</dd></div>` : ""}${event.format ? html`<div><dt>${t("Формат")}</dt><dd>${platformFormat(event.format)}</dd></div>` : ""}${event.location ? html`<div><dt>${t("Место")}</dt><dd>${esc(event.location)}</dd></div>` : ""}</dl>${source}</div><aside class="platform-side-panel"><h2>${t("Участвовать")}</h2><p class="hint">${t("Отметьте участие, чтобы сохранить событие в своём списке.")}</p>${event.participation_url && /^https?:\/\//i.test(event.participation_url) ? html`<a class="button" href="${esc(event.participation_url)}" target="_blank" rel="noopener noreferrer">${t("Открыть ссылку участия")} ${icon("arrow")}</a>` : `<p class="hint">${t("Ссылка для участия пока не добавлена.")}</p>`}${session ? html`<div id="event-engagement"><p class="hint">${t("Загружаем…")}</p></div>` : html`<a class="button secondary" href="/app#login?next=${encodeURIComponent("event/" + event.slug)}">${t("Войти, чтобы сохранить")}</a>`}${own ? html`<a class="button secondary" href="/app#event-edit/${esc(event.slug)}">${t("Редактировать событие")}</a><button type="button" class="danger" id="event-delete">${t("Удалить событие")}</button>` : ""}<a class="text-button" href="/app#teams?event_id=${event.id}">${t("Найти команду на событие")}${icon("arrow")}</a><a class="text-button" href="/app#team-new?event=${event.id}">${t("Создать команду")}${icon("plus")}</a></aside></article>
    <section class="platform-detail-section"><div class="discovery-results-heading"><h2>${t("Команды для участия")}</h2><a class="button secondary" href="/app#team-new?event=${event.id}">${icon("plus")} ${t("Создать команду")}</a></div><div id="event-teams">${teamResult.status === "fulfilled" ? platformCardGrid(teams, "team") : `<p class="error" role="alert">${esc(errorText(teamResult.reason))}</p>`}</div></section>`;
  const deleteEvent = root.querySelector("#event-delete");
  if (deleteEvent) actionButton(deleteEvent, async () => { if (!confirm(`${t("Удалить событие")}: «${event.title}»?\n\n${t("Страница и обложка будут удалены, связь команд с событием будет снята.")}`)) return; await api(`/events/${encodeURIComponent(event.slug)}`, { method: "DELETE" }); toast(t("Событие удалено.")); go("explore?kind=events"); });
  if (session) try { const state = await api(`/events/${encodeURIComponent(event.slug)}/engagement`); if (stamp === generation) bindPlatformEngagement("event", event.slug, state, root.querySelector("#event-engagement")); } catch (error) { if (stamp === generation) root.querySelector("#event-engagement").innerHTML = `<p class="error" role="alert">${esc(errorText(error))}</p>`; }
  if (stamp === generation) bindPlatformSaves(root.querySelector("#event-teams"), stamp);
}
async function platformScreen(route, id, query, root, stamp) {
  if (route === "teams") return platformListScreen("team", query, root, stamp);
  if (route === "communities") return platformListScreen("community", query, root, stamp);
  if (route === "team-new" || route === "team-edit") return platformEditorScreen("team", route === "team-edit" ? id : null, query, root, stamp);
  if (route === "community-new" || route === "community-edit") return platformEditorScreen("community", route === "community-edit" ? id : null, query, root, stamp);
  if (route === "event-new" || route === "event-edit") return platformEditorScreen("event", route === "event-edit" ? id : null, query, root, stamp);
  if (route === "events") return platformListScreen("event", query, root, stamp);
  const kind = route === "team" ? "team" : route === "community" ? "community" : "event";
  if (!/^[a-z0-9-]+$/.test(id || "")) { root.innerHTML = empty(t("Страница не найдена"), t("Проверьте ссылку и попробуйте снова.")); return; }
  const entity = await api(`/${platformConfig[kind].plural}/${encodeURIComponent(id)}`);
  if (stamp !== generation) return;
  if (kind === "team") return teamDetailScreen(entity, root, stamp);
  if (kind === "community") return communityDetailScreen(entity, root, stamp);
  return eventDetailScreen(entity, root, stamp);
}
