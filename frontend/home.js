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
// Colour order of segments: done or current is filled, future is outlined. Widths are applied by homeStyle (CSP forbids inline style attributes).
function homePhase(event, now) {
  const { stages, from, to, at } = homeStages(event, now), total = to - from;
  const text = stages.filter(stage => stage.label).map(stage => stage.kind === "reg" ? html`${t(stage.label)} ${homeShortDate(stage.to)}` : html`${t(stage.label)} ${homeShortDate(stage.from)}${event.ends_at ? html` – ${homeShortDate(Date.parse(event.ends_at))}` : ""}`);
  return html`<span class="sr-only">${text.map((line, index) => html`${index ? "; " : ""}${line}`)}</span><div class="hm-phase" aria-hidden="true">${stages.map(stage => html`<i class="hm-seg ${stage.kind}${stage.from <= now ? " done" : ""}" data-grow="${Math.max(stage.to - stage.from, total * .05)}"></i>`)}<i class="hm-tick" data-at="${at}"></i></div>`;
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
