"use strict";
// Discovery home (the "all" tab without a search): data helpers. Everything shown comes from the API;
// a block whose data is empty or failed to load is left out. Rendering lives below.
const HOME_HOUR = 3600e3, HOME_DAY = 24 * HOME_HOUR;
// forms: [one, few, many] in Russian; English uses forms[0] for 1 and forms[2] otherwise.
function pluralForm(count, forms) {
  const last = count % 10, tens = count % 100;
  const index = language === "ru" ? (last === 1 && tens !== 11 ? 0 : last >= 2 && last <= 4 && (tens < 12 || tens > 14) ? 1 : 2) : (count === 1 ? 0 : 2);
  return count + " " + t(forms[index]);
}
function homeShortDate(ms) {
  return new Date(ms).toLocaleDateString(language === "ru" ? "ru-RU" : "en-US", { day: "numeric", month: "short" });
}
// Chip and countdown target for an event. Deadline chip only inside the last 72 hours.
function homeClock(event, now) {
  const starts = Date.parse(event.starts_at), ends = event.ends_at ? Date.parse(event.ends_at) : null, deadline = event.deadline ? Date.parse(event.deadline) : null;
  if (event.status === "active") return { chip: "live", text: "идёт", target: ends && ends > now ? ends : null, label: "до конца" };
  if (deadline && deadline > now && deadline - now <= 72 * HOME_HOUR) return { chip: "soon", text: "дедлайн", target: deadline, label: "до дедлайна" };
  if (deadline && deadline > now) return { chip: "reg", text: "регистрация", target: starts, label: "до старта" };
  return { chip: "wait", text: "скоро", target: starts, label: "до старта" };
}
// Countdown markup: days and hours, or hours and minutes under a day. Refreshed by homeTick.
function homeCountdown(ms) {
  const minutes = Math.max(0, Math.floor(ms / 60000)), days = Math.floor(minutes / 1440), hours = Math.floor(minutes % 1440 / 60), rest = minutes % 60;
  const two = value => String(value).padStart(2, "0");
  return days ? html`${days}<small>д</small>${two(hours)}<small>ч</small>` : html`${hours}<small>ч</small>${two(rest)}<small>м</small>`;
}
function homeCount(target, now) {
  return html`<span class="hm-count num" data-target="${target}">${homeCountdown(target - now)}</span>`;
}
// Phase segments an event honestly has: registration until the deadline, then the event itself.
// Registration start, voting etc. are not in the data, so they are not drawn.
function homeStages(event, now) {
  const starts = Date.parse(event.starts_at), ends = event.ends_at ? Date.parse(event.ends_at) : null, deadline = event.deadline ? Date.parse(event.deadline) : null;
  const active = event.status === "active", begin = active ? Math.min(starts, now) : now;
  const stages = [];
  if (!active && deadline && deadline > now && deadline < starts) stages.push({ kind: "reg", from: now, to: deadline, label: "Регистрация до" });
  const runFrom = stages.length ? deadline : begin;
  const runTo = ends && ends > starts ? ends : starts + HOME_DAY;
  if (starts > runFrom) stages.push({ kind: "wait", from: runFrom, to: starts, label: "" });
  stages.push({ kind: "run", from: Math.max(starts, runFrom), to: runTo, label: "Идёт" });
  return { stages, from: stages[0].from, to: runTo, at: Math.min(1, Math.max(0, (now - stages[0].from) / (runTo - stages[0].from))) };
}
// Visually hidden description of the same segments, because the bars carry meaning only by position and colour.
function homePhaseText(event, stages) {
  const lines = stages.filter(stage => stage.label).map(stage => stage.kind === "reg" ? html`${t(stage.label)} ${homeShortDate(stage.to)}` : html`${t(stage.label)} ${homeShortDate(stage.from)}${event.ends_at ? html` – ${homeShortDate(Date.parse(event.ends_at))}` : ""}`);
  return html`<span class="sr-only">${lines.map((line, index) => html`${index ? "; " : ""}${line}`)}</span>`;
}
// Past or current segments are filled, future ones outlined. Widths are applied by homeStyle (CSP forbids inline style attributes).
function homePhase(event, now) {
  const { stages, from, to, at } = homeStages(event, now), total = to - from;
  return html`${homePhaseText(event, stages)}<div class="hm-phase" aria-hidden="true">${stages.map(stage => html`<i class="hm-seg ${stage.kind}${stage.from <= now ? " done" : ""}" data-grow="${Math.max(stage.to - stage.from, total * .05)}"></i>`)}<i class="hm-tick" data-at="${at}"></i></div>`;
}
// Apply data-driven geometry through CSSOM; inline style attributes in markup are blocked by the CSP.
function homeStyle(root) {
  root.querySelectorAll("[data-grow]").forEach(node => { node.style.flexGrow = node.dataset.grow; });
  root.querySelectorAll("[data-at]").forEach(node => { node.style.left = node.dataset.at * 100 + "%"; });
  root.querySelectorAll("[data-col]").forEach(node => { node.style.gridColumn = node.dataset.col; });
  root.querySelectorAll("[data-k]").forEach(node => { node.style.setProperty("--k", node.dataset.k); });
}
// Refresh countdowns once a minute while this screen is on; stops itself when the screen is replaced.
function homeTick(root, stamp) {
  const timer = setInterval(() => {
    if (!root.isConnected || stamp !== generation) { clearInterval(timer); return; }
    const now = Date.now();
    root.querySelectorAll(".hm-count[data-target]").forEach(node => { node.innerHTML = homeCountdown(Number(node.dataset.target) - now); });
  }, 60000);
}
async function homeData(now, signedIn) {
  const iso = ms => new Date(ms).toISOString();
  const list = path => api(path).then(page => page.items ?? page);
  const jobs = {
    active: list("/events?status=active&limit=3"),
    soon: list("/events?upcoming=true&limit=3"),
    week: list(`/events?upcoming=true&starts_before=${iso(now + 7 * HOME_DAY)}&limit=100`),
    month: list(`/events?upcoming=true&starts_before=${iso(now + 28 * HOME_DAY)}&limit=6`),
    projectRoles: list("/openings?limit=3"), teamRoles: list("/team-openings?limit=3"),
    projects: list("/discovery?source=native&limit=2"), communities: list("/communities?limit=1"), people: list("/people?limit=1"),
    ...(signedIn ? { projectApplications: list("/me/applications"), teamApplications: list("/team-applications?limit=100") } : {}),
  };
  const keys = Object.keys(jobs), settled = await Promise.allSettled(Object.values(jobs));
  if (settled.every(result => result.status === "rejected")) throw settled[0].reason;
  return Object.fromEntries(keys.map((key, index) => [key, settled[index].status === "fulfilled" ? settled[index].value : []]));
}
// Events for the strip and calendar: active first, then by start, without repeats.
function homeEvents(...lists) {
  const seen = new Set();
  return lists.flat().filter(event => !seen.has(event.id) && seen.add(event.id));
}

function homeSearchForm(className) {
  return html`<form class="discovery-search ${className}" role="search"><label>${icon("explore")}<span class="sr-only">${t("Поиск по Кругу")}</span><input name="search" maxlength="100" placeholder="${t("Проект, навык или человек")}" autocomplete="off"></label><button>${t("Найти")}</button></form>`;
}
function homeTile(event, now, lead = false) {
  const clock = homeClock(event, now);
  const meta = homeEventMeta(event);
  return html`<a class="hm-tile${lead ? " lead" : ""}" href="${platformUrl("event", event.slug)}"><div class="hm-row"><span class="hm-chip ${clock.chip}">${t(clock.text)}</span><span class="hm-kind">${meta}</span></div><h3>${event.title}</h3>${clock.target ? html`<div class="hm-row"><span class="hm-big">${homeCount(clock.target, now)}</span><span class="hm-kind">${t(clock.label)}</span></div>` : ""}${homePhase(event, now)}</a>`;
}
function homeTabs() {
  const tabs = [["all", "Всё", ""], ["projects", "Проекты", "project"], ["teams", "Команды", "team"], ["events", "События", "event"], ["communities", "Сообщества", "community"], ["people", "Люди", "person"]];
  return html`<div class="hm-types"><div class="hm-wrap"><nav class="discovery-tabs hm-tabs" aria-label="${t("Тип результатов")}">${tabs.map(([value, label, type]) => html`<a href="/app#explore?kind=${value}" class="${type ? "type-" + type : ""}${value === "all" ? " active" : ""}" ${value === "all" ? html`aria-current="page"` : ""}>${type ? html`<i></i>` : ""}${t(label)}</a>`)}</nav></div></div>`;
}
// Signed-in band: greeting, summary of real counts, and the "now and soon" strip.
function homeBand(data, tiles, now) {
  const name = me.display_name || me.username;
  const accepted = [...data.projectApplications, ...data.teamApplications].filter(item => item.status === "accepted").length;
  const week = homeEvents(data.active, data.week).length;
  const parts = [];
  if (accepted) parts.push(html`<b>${pluralForm(accepted, ["заявка принята", "заявки приняты", "заявок принято"])}</b>`);
  if (week) parts.push(pluralForm(week, ["событие на неделе", "события на неделе", "событий на неделе"]));
  return html`<section class="hm-band"><div class="hm-wrap"><div class="hm-top"><h1 class="hm-hello">${t("Привет,")} ${name}<span>${parts.length ? parts.map((part, index) => html`${index ? " · " : ""}${part}`) : t("Проекты, команды, встречи и сообщества для совместной работы.")}</span></h1>${homeSearchForm("hm-msearch")}</div>
    ${tiles.length ? html`<div class="hm-strip" aria-label="${t("Сейчас и скоро")}">${tiles.map((event, index) => homeTile(event, now, index === 0))}</div>` : ""}</div></section>`;
}
// Guest hero: headline, search, static skill shortcuts and the next live or upcoming event.
function homeHero(tile, now) {
  const skills = ["Python", "Godot", "Unity", "Figma", "Blender", "JavaScript"];
  return html`<section class="hm-band hm-hero"><div class="hm-wrap hm-hero-grid"><div><h1 class="hm-headline">${t("Найди, с кем и что делать")}</h1><p class="hm-lead">${t("Проекты, команды, события и сообщества: найдите, где нужны ваши навыки.")}</p>
    ${homeSearchForm("hm-search")}<div class="hm-quick"><span>${t("Часто ищут")}</span>${skills.map(skill => html`<a href="/app#explore?kind=all&search=${encodeURIComponent(skill)}">${skill}</a>`)}</div></div>
    ${tile ? html`<div class="hm-featured">${homeTile(tile, now, true)}</div>` : ""}</div></section>`;
}
function homeSectionHead(id, title, link, linkText) {
  return html`<div class="hm-sec-head"><h2 id="${id}">${t(title)}</h2>${link ? html`<a href="${link}">${t(linkText)}</a>` : ""}</div>`;
}
// Entity colour field with the first letter of its title; the kind label sits on top.
function homeCover(title, label) {
  return html`<div class="hm-cover"><span class="hm-mono" aria-hidden="true">${[...title.trim()][0]?.toUpperCase() || ""}</span><span class="hm-kind-l">${t(label)}</span></div>`;
}
// Open roles from projects and teams, newest first; roles of one project or team share a card.
function homeRoleGroups(data) {
  const roles = [
    ...data.projectRoles.filter(opening => opening.project).map(opening => ({ kind: "project", entity: opening.project, opening })),
    ...data.teamRoles.filter(opening => opening.team).map(opening => ({ kind: "team", entity: opening.team, opening })),
  ].sort((a, b) => Date.parse(b.opening.created_at) - Date.parse(a.opening.created_at));
  const groups = new Map();
  for (const role of roles) {
    const key = role.kind + "/" + role.entity.slug;
    if (!groups.has(key)) groups.set(key, { kind: role.kind, entity: role.entity, openings: [] });
    groups.get(key).openings.push(role.opening);
  }
  return [...groups.values()].slice(0, 3);
}
function homeRoleCard({ kind, entity, openings }, signedIn) {
  const route = kind + "/" + entity.slug, first = openings[0];
  const meta = [first.commitment, ...first.skills.slice(0, 2)].filter(Boolean).join(" · ");
  const href = signedIn ? "/app#" + route : "/app#login?next=" + encodeURIComponent(route);
  return html`<article class="hm-fcard type-${kind}">${homeCover(entity.title, kind === "team" ? "Команда" : "Проект")}<div class="hm-in"><h3><a href="/app#${route}">${entity.title}</a></h3><p>${entity.summary}</p>
    <div class="hm-slots">${openings.slice(0, 4).map(opening => html`<span class="hm-slot"><i></i>${opening.title || opening.role}</span>`)}</div>
    <div class="hm-foot"><span>${meta}</span><a class="hm-btn" href="${href}">${t("Откликнуться")}</a></div></div></article>`;
}
function homeRoles(data, signedIn) {
  const groups = homeRoleGroups(data);
  return groups.length ? html`<section aria-labelledby="hm-roles-h">${homeSectionHead("hm-roles-h", "Ищут людей", "/app#roles", "Все роли")}<div class="hm-feature">${groups.map(group => homeRoleCard(group, signedIn))}</div></section>` : "";
}

function homeEventMeta(event) {
  return [platformEventType(event.type), event.format === "unspecified" ? "" : event.location || platformFormat(event.format)].filter(Boolean).join(" · ");
}
// Four-week timeline: registration until the deadline and the event itself, one column per day.
function homeCalendar(data, now) {
  const events = homeEvents(data.active, data.month).sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at)).slice(0, 6);
  if (!events.length) return "";
  const days = 28, begin = new Date(now);
  begin.setHours(0, 0, 0, 0);
  const first = begin.getTime();
  const columns = (from, to) => {
    const start = Math.min(days + 1, Math.max(1, Math.floor((from - first) / HOME_DAY) + 1));
    return start + " / " + Math.min(days + 1, Math.max(start + 1, Math.ceil((to - first) / HOME_DAY) + 1));
  };
  const row = event => {
    const clock = homeClock(event, now), { stages } = homeStages(event, now), starts = Date.parse(event.starts_at), ends = event.ends_at ? Date.parse(event.ends_at) : null;
    const range = homeShortDate(starts) + (ends && homeShortDate(ends) !== homeShortDate(starts) ? " – " + homeShortDate(ends) : "");
    const segments = stages.filter(stage => stage.kind !== "wait" && stage.from < first + days * HOME_DAY);
    return html`<a class="hm-r" href="${platformUrl("event", event.slug)}"><div class="hm-name"><b>${event.title}</b><span>${[range, homeEventMeta(event)].filter(Boolean).join(" · ")}</span></div>
      <div class="hm-track">${homePhaseText(event, stages)}${segments.map(stage => html`<i class="hm-seg ${stage.kind}" aria-hidden="true" data-col="${columns(stage.from, stage.to)}"></i>`)}</div>
      <div class="hm-cd">${clock.target ? homeCount(clock.target, now) : ""}<span class="hm-status ${clock.chip}">${t(clock.text)}</span></div></a>`;
  };
  // A date label that sits under the "today" line would be crossed by it, so that label is left out.
  const today = (now - first) / (days * HOME_DAY);
  const axis = Array.from({ length: days }, (_, index) => html`<span>${index % 7 === 0 && Math.abs(index / days - today) >= 0.06 ? homeShortDate(first + index * HOME_DAY) : ""}</span>`);
  return html`<section class="type-event" aria-labelledby="hm-cal-h">${homeSectionHead("hm-cal-h", "Календарь событий", "/app#explore?kind=events", "Все события")}
    <div class="hm-calendar"><div class="hm-legend"><span><i class="hm-sw reg"></i>${t("регистрация")}</span><span><i class="hm-sw run"></i>${t("событие")}</span></div>
      <div class="hm-tl"><div></div><div class="hm-axis" aria-hidden="true">${axis}</div><div></div>${events.map(row)}<i class="hm-now" aria-hidden="true" data-k="${today}"><b>${t("сегодня")}</b></i></div></div></section>`;
}

// A few compact cards from the existing project, community and people lists.
function homeMixedCards(data) {
  const cards = [
    ...data.projects.map(project => ({ type: "project", label: project.origin === "external" ? "Внешний проект" : "Проект", title: project.title, text: project.summary, href: "/app#project/" + project.slug,
      foot: [project.member_count ? pluralForm(project.member_count, ["участник", "участника", "участников"]) : "", project.open_roles_count ? pluralForm(project.open_roles_count, ["роль", "роли", "ролей"]) : ""] })),
    ...data.communities.map(community => ({ type: "community", label: "Сообщество", title: community.title, text: community.summary, href: "/app#community/" + community.slug,
      foot: [community.member_count ? pluralForm(community.member_count, ["участник", "участника", "участников"]) : "", community.published_posts_count ? pluralForm(community.published_posts_count, ["публикация", "публикации", "публикаций"]) : ""] })),
    ...data.people.map(person => ({ type: "person", label: "Человек", title: person.display_name || person.username, text: person.bio || person.intent_text || "", href: "/app#profile/" + person.id,
      foot: [person.skills.slice(0, 3).join(", "), person.timezone || ""] })),
  ];
  return cards.length ? html`<section aria-labelledby="hm-mix-h">${homeSectionHead("hm-mix-h", "Проекты, сообщества и люди", "/app#explore?kind=projects", "Смотреть всё")}<div class="hm-grid">${cards.slice(0, 4).map(card => html`<article class="hm-card type-${card.type}">${homeCover(card.title, card.label)}<div class="hm-in"><h3><a href="${card.href}">${card.title}</a></h3><p>${card.text}</p><div class="hm-foot">${card.foot.map(text => html`<span>${text}</span>`)}</div></div></article>`)}</div></section>` : "";
}
// "Your applications": the latest three from project and team applications.
function homeRail(data) {
  const statuses = { pending: ["reg", "на рассмотрении"], accepted: ["live", "принята"], rejected: ["wait", "отклонена"], withdrawn: ["wait", "отозвана"] };
  const applications = [
    ...data.projectApplications.map(item => ({ kind: "project", slug: item.project_slug, title: item.project_title, role: item.opening_title || item.role, status: item.status, at: item.created_at })),
    ...data.teamApplications.map(item => ({ kind: "team", slug: item.team_slug, title: item.team_title, role: item.opening_title, status: item.status, at: item.created_at })),
  ].sort((a, b) => Date.parse(b.at) - Date.parse(a.at)).slice(0, 3);
  if (!applications.length) return "";
  return html`<aside class="hm-side" aria-labelledby="hm-apps-h"><section class="hm-panel"><h2 id="hm-apps-h">${t("Ваши заявки")}<a href="/app#applications">${t("Все")}</a></h2>
    ${applications.map(item => { const [chip, label] = statuses[item.status] || ["wait", item.status]; return html`<a class="hm-p-row type-${item.kind}" href="/app#${item.kind}/${item.slug}"><b>${item.title}</b><span class="hm-status ${chip}">${t(label)}</span><span>${[item.role, date(item.at)].filter(Boolean).join(" · ")}</span></a>`; })}</section></aside>`;
}

async function homeScreen(root, query, stamp) {
  const signedIn = Boolean(session && me), now = Date.now();
  const data = await homeData(now, signedIn);
  if (stamp !== generation) return;
  data.projectApplications ||= []; data.teamApplications ||= [];
  const tiles = homeEvents(data.active, data.soon).slice(0, 3);
  root.closest(".layout")?.classList.replace("layout-discovery", "layout-home");
  const sections = [homeRoles(data, signedIn), homeCalendar(data, now), homeMixedCards(data)];
  const rail = signedIn ? homeRail(data) : "";
  root.innerHTML = html`${signedIn ? homeBand(data, tiles, now) : homeHero(tiles[0], now)}${homeTabs()}<div class="hm-wrap hm-body${rail ? " with-rail" : ""}"><div class="hm-main">${sections.some(Boolean) ? sections : empty(t("Пока нет результатов"), t("Измените запрос или попробуйте позже. Здесь показывается только актуальное содержимое участников."))}</div>${rail}</div>`;
  root.querySelectorAll(".discovery-search").forEach(form => bindForm(form, async data => {
    const params = new URLSearchParams({ kind: "all" }), value = data.get("search")?.trim();
    if (value) params.set("search", value);
    go("explore?" + params);
  }));
  homeStyle(root);
  homeTick(root, stamp);
}
