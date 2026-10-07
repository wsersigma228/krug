/* Native browser UI: no build step or third-party runtime. */
"use strict";
const app = document.querySelector("#app");
applyPreferences();
let accountLinkToken = new URLSearchParams(location.hash.slice(1)).get("token");
let accountLinkCompleted = false;
document.querySelector(".skip").addEventListener("click", (event) => {
  event.preventDefault();
  document.querySelector("#main")?.focus();
});
let session = null;
try {
  session = JSON.parse(sessionStorage.getItem("krug-session"));
} catch {
  sessionStorage.removeItem("krug-session");
}
let me = null,
  refreshFlight = null,
  generation = 0,
  toastTimer,
  objectURLs = [],
  postGridObserver;
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const date = (value) =>
  new Date(value).toLocaleDateString(language === "ru" ? "ru-RU" : "en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
const iconPaths = {
  feed: '<path d="M4 5h16M4 12h16M4 19h10"/>',
  explore: '<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
  posts:
    '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
  people:
    '<circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M17 14a5 5 0 0 1 4 5"/>',
  settings:
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
  comment: '<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5a9.5 9.5 0 0 1 19 0Z"/>',
};
const icon = (name) =>
  html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">${iconPaths[name]}</svg>`;

function saveSession(value) {
  session = value;
  me = null;
  if (value) sessionStorage.setItem("krug-session", JSON.stringify(value));
  else sessionStorage.removeItem("krug-session");
}
function toast(message) {
  const el = document.querySelector("#toast");
  el.textContent = message;
  el.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("visible"), 5000);
}
function errorText(error) {
  return (
    error.message ||
    t("Не удалось связаться с сервером. Проверьте подключение и попробуйте снова.")
  );
}
async function api(path, options = {}, retry = true) {
  const headers = new Headers(options.headers);
  if (session?.access_token)
    headers.set("Authorization", html`Bearer ${session.access_token}`);
  let body = options.body;
  if (body && !(body instanceof Blob)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, {
      ...options,
      body,
      headers,
      credentials: "omit",
    });
  } catch {
    throw new Error(
      t("Сервер недоступен. Проверьте подключение и попробуйте снова."),
    );
  }
  if (
    response.status === 401 &&
    session &&
    retry &&
    !["/login", "/refresh"].includes(path)
  ) {
    if (!refreshFlight) {
      const original = session;
      refreshFlight = fetch("/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: original.refresh_token }),
        credentials: "omit",
      })
        .then(async (r) => {
          if (!r.ok) {
            if (r.status === 401 && session === original) saveSession(null);
            throw new Error(
              r.status === 429
                ? t("Слишком много запросов. Подождите минуту.")
                : t("Сессия завершена. Войдите снова."),
            );
          }
          const token = await r.json();
          if (session === original) {
            session = { ...original, access_token: token.access_token };
            sessionStorage.setItem("krug-session", JSON.stringify(session));
          }
        })
        .finally(() => {
          refreshFlight = null;
        });
    }
    await refreshFlight;
    return api(path, options, false);
  }
  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    const translations = {
      "Invalid username or password": t("Неверное имя пользователя или пароль."),
      "Username already exists": t("Это имя пользователя уже занято."),
      "Email already exists": t("Этот email уже используется."),
      "Post not found": t("Публикация не найдена или недоступна."),
      "Author not found": t("Автор не найден."),
      "Invalid or expired token":
        t("Ссылка недействительна или срок её действия истёк."),
      "Verify your email before enabling notifications":
        t("Сначала подтвердите email."),
      "Account has no email": t("У аккаунта нет email."),
    };
    const detail = typeof data?.detail === "string" ? data.detail : "";
    const message =
      translations[detail] ||
      {
        401: t("Сессия завершена. Войдите снова."),
        403: t("У вас нет прав на это действие."),
        404: t("Страница не найдена или недоступна."),
        409: t("Такие данные уже используются."),
        413: t("Фото должно быть не больше 8 МиБ."),
        422: t("Проверьте заполненные поля и срок действия ссылки."),
        429: html`Слишком много запросов. Повторите через ${response.headers.get("Retry-After") || 60} сек.`,
      }[response.status] ||
      t("Не удалось выполнить действие. Попробуйте снова.");
    if (response.status === 401 && path !== "/login") saveSession(null);
    throw new Error(message);
  }
  if (options.blob) return response.blob();
  return response.status === 204 ? null : response.json();
}
function go(route) {
  if (location.pathname !== "/app" && location.pathname !== "/app/")
    location.assign("/app#" + route);
  else if (location.hash === "#" + route) render();
  else location.hash = route;
}
function shell(route) {
  const wideFeed = ["stories", "feed"].includes(route);
  const discovery = ["explore", "saved", "projects"].includes(route);
  const links = [["explore", t("Обзор")], ["explore?kind=people", t("Люди")], ["stories", t("Истории")], [session ? "settings" : "login", session ? t("Аккаунт") : t("Войти")]];
  app.innerHTML = html`<header class="topbar"><div class="topbar-inner">
      <div class="brand-block"><a class="brand" href="/app#explore" aria-label="Круг, обзор"><span class="brand-mark"></span>круг</a>
      <span class="topbar-tagline">Люди. Проекты. Возможности.</span></div>
      <nav class="nav" aria-label="Основная навигация">${links.map(([id, title]) => { const peopleTab = new URLSearchParams(location.hash.split("?")[1] || "").get("kind") === "people"; const current = id === "explore?kind=people" ? route === "explore" && peopleTab : route === id && !(id === "explore" && peopleTab); return html`<a href="/app#${id}" class="${current ? "active" : ""}" ${current ? 'aria-current="page"' : ""}>${icon({stories:"feed",settings:"settings",login:"settings"}[id] || id.split("?")[0])}<span>${title}</span></a>`; }).join("")}</nav>
      <div class="header-controls"><div class="preferences">
      <button id="ui-language" class="preference-button" aria-label="${language === "ru" ? "Switch to English" : t("Переключить на русский")}" title="Русский / English">${language.toUpperCase()}</button>
      <details class="theme-picker"><summary id="ui-theme" class="preference-button" aria-label="${t("Тема")}" title="${t("Тема")}">${themeIcon(theme)}</summary>
      <div class="theme-options">${["light", "dark", "system"].map((value, index) => html`<button class="theme-option" data-theme-choice="${value}" aria-pressed="${theme === value}">${themeIcon(value)}${t(["Светлая", "Тёмная", "Системная"][index])}</button>`).join("")}</div></details>
      </div><div class="header-actions">${me ? html`<a class="account-link" href="/app#profile/${me.id}" aria-label="${esc(me.username)}"><span class="avatar">${esc(me.username[0]?.toUpperCase())}</span><span>@${esc(me.username)}</span></a>` : ""}${session ? html`<a class="button compose" href="/app#project-new" aria-label="Создать проект">${icon("plus")}<span>Создать проект</span></a>` : t('<a class="button compose" href="/app#login">Войти в Круг</a>')}</div>
      </div></div></header><div class="layout ${wideFeed ? "layout-feed" : discovery ? "layout-discovery" : ""}">
      <main class="main" id="main" tabindex="-1">
      <div class="loading" role="status">Загрузка…</div>
      </main>
      </div>`;
  document.querySelector("#ui-language").addEventListener("click", async (event) => {
    const control = event.currentTarget;
    const selected = language === "ru" ? "en" : "ru";
    if (app.querySelector("form button:disabled")) {
      toast(t("Дождитесь завершения текущего действия."));
      return;
    }
    control.disabled = true;
    const main = document.querySelector("#main");
    main.inert = true;
    try {
      if (session) {
        await api("/me/language", { method: "PATCH", body: { language: selected } });
        if (me) me.language = selected;
      }
      language = selected;
      storePreference("krug-language", language);
      applyPreferences();
      await render({ preserve: true });
      document.querySelector("#ui-language")?.focus();
    } catch (error) { toast(errorText(error)); }
    finally { control.disabled = false; main.inert = false; }
  });
  const picker = document.querySelector(".theme-picker");
  picker.addEventListener("click", (event) => {
    const button = event.target.closest("[data-theme-choice]");
    if (!button) return;
    theme = button.dataset.themeChoice;
    storePreference("krug-theme", theme);
    applyPreferences({ transitionTheme: true });
    picker.querySelector("summary").innerHTML = themeIcon(theme);
    picker.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b === button)));
    picker.open = false;
    picker.querySelector("summary").focus();
  });
  picker.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { picker.open = false; picker.querySelector("summary").focus(); }
  });
  picker.addEventListener("focusout", () => {
    setTimeout(() => { if (!picker.contains(document.activeElement)) picker.open = false; }, 0);
  });
  return document.querySelector("#main");
}
function themeIcon(value) {
  const paths = {
    light: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
    dark: '<path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"/>',
    system: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M12 17v4m-4 0h8"/>',
  };
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[value]}</svg>`;
}
function heading(label, title, subtitle = "") {
  return html`<h1>${title}</h1>${subtitle ? html`<p class="intro">${subtitle}</p>` : ""}`;
}
function empty(title, text, link = "") {
  return html`<div class="empty">
      <h2>${title}</h2>
      <p>${text}</p>${link}</div>`;
}
function bindForm(form, action) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const buttons = [...form.querySelectorAll("button")];
    buttons.forEach((b) => (b.disabled = true));
    form.querySelector(".error")?.remove();
    try {
      await action(new FormData(form));
    } catch (error) {
      const el = document.createElement("div");
      el.className = "error";
      el.setAttribute("role", "alert");
      el.textContent = errorText(error);
      form.prepend(el);
    } finally {
      buttons.forEach((b) => (b.disabled = false));
    }
  });
}
function actionButton(button, action) {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await action();
    } catch (error) {
      toast(errorText(error));
    } finally {
      button.disabled = false;
    }
  });
}
function input(name, label, type = "text", attrs = "") {
  return html`<label class="field">${label}<input name="${name}" type="${type}" ${attrs}>
      </label>`;
}
function photoMarkup(post, cls = "") {
  return post.image_url
    ? html`<button class="post-media" type="button" aria-label="Открыть фото" disabled><img class="post-photo ${cls}" data-photo="${post.id}" alt="${post.title ? t("Фото к публикации «") + esc(post.title) + "»" : t("Фото к публикации")}" loading="lazy"></button>`
    : "";
}
function closePhotoViewer() {
  document.querySelector(".media-viewer")?.close();
}
app.addEventListener("click", (event) => {
  const opener = event.target.closest(".post-media");
  const photo = opener?.querySelector("img");
  if (!photo?.naturalWidth || document.querySelector(".media-viewer")) return;
  const dialog = document.createElement("dialog");
  dialog.className = "media-viewer";
  dialog.setAttribute("aria-label", t("Просмотр фото"));
  dialog.innerHTML = html`<button class="media-close" type="button" aria-label="Закрыть фото" autofocus>${icon("close")}</button>`;
  const image = document.createElement("img");
  image.src = photo.src;
  image.alt = photo.alt;
  dialog.append(image);
  dialog.querySelector("button").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  image.addEventListener("error", () => { dialog.close(); toast(t("Фото сейчас недоступно.")); }, { once: true });
  dialog.addEventListener("close", () => {
    dialog.remove();
    document.body.classList.remove("media-open");
    if (opener.isConnected) opener.focus({ preventScroll: true });
  }, { once: true });
  document.body.append(dialog);
  document.body.classList.add("media-open");
  dialog.showModal();
});
async function hydratePhotos(root, stamp) {
  for (const img of root.querySelectorAll(
    "[data-photo]:not([src]):not([data-loading])",
  )) {
    img.dataset.loading = "true";
    const unavailable = () => {
      if (!img.isConnected) return;
      const el = document.createElement("p");
      el.className = "hint";
      el.textContent = t("Фото сейчас недоступно.");
      (img.closest(".post-media") || img).replaceWith(el);
    };
    img.addEventListener("load", () => { img.closest(".post-media").disabled = false; }, { once: true });
    img.addEventListener("error", unavailable, { once: true });
    try {
      const blob = await api(html`/posts/${img.dataset.photo}/image`, {
        blob: true,
      });
      if (stamp !== generation || !img.isConnected) continue;
      const url = URL.createObjectURL(blob);
      objectURLs.push(url);
      img.src = url;
    } catch {
      unavailable();
    }
  }
}
function postCard(post, author) {
  const username = post.author_username || author || me?.username || t("Автор");
  return html`<article class="post-card ${post.image_url ? "with-photo" : ""}"><div class="post-card-inner">
      <div class="post-meta">
      <a class="avatar" href="/app#profile/${post.author_id}" aria-label="Профиль ${esc(username)}">${esc(username[0]?.toUpperCase())}</a>
      <a class="author" href="/app#profile/${post.author_id}">${esc(username)}</a>
      <span>· ${date(post.created_at)}</span>${!post.is_published ? t('<span class="badge">Черновик</span>') : ""}</div>
      <div class="post-content">${photoMarkup(post)}<div class="post-copy">${post.title ? html`<a class="post-title" href="/app#post/${post.id}">${esc(post.title)}</a>` : ""}
      <a class="post-excerpt" href="/app#post/${post.id}">${esc(post.content.slice(0, 260))}${post.content.length > 260 ? "…" : ""}</a></div></div><div class="toolbar">
      <button class="reaction" data-like="${post.id}" disabled>${icon("heart")} ${t("Загрузка…")}</button><a class="discussion-link" href="/app#post/${post.id}?comments=1">${icon("comment")} Комментарии</a>${post.content.length > 260 ? html`<a class="text-button read-story" href="/app#post/${post.id}">Читать дальше${icon("arrow")}</a>` : ""}${me?.id === post.author_id ? html`<a class="text-button" href="/app#edit/${post.id}">Редактировать</a>` : ""}</div>
      </div></article>`;
}
function bindLike(button, id, likes) {
  function update(result) {
    likes = result;
    button.innerHTML = html`${icon("heart")} ${likes.count}<span class="reaction-label"> · ${likes.liked ? t("Нравится") : t("Поддержать")}</span>`;
    button.setAttribute("aria-label", `${likes.count} · ${likes.liked ? t("Нравится") : t("Поддержать")}`);
    button.className = "reaction" + (likes.liked ? " liked" : "");
    button.setAttribute("aria-pressed", String(likes.liked));
  }
  update(likes);
  button.disabled = false;
  actionButton(button, async () => {
    if (!me) { go("login"); return; }
    const result = await api(`/posts/${id}/likes`, { method: likes.liked ? "DELETE" : "PUT" });
    if (button.isConnected) update(result);
  });
}
async function hydrateLikes(root, stamp) {
  // ponytail: one GET per card (12 per page); batch in the feed API if this becomes costly.
  await Promise.all([...root.querySelectorAll("[data-like]:not([data-loading])")].map(async button => {
    button.dataset.loading = "true";
    const load = async () => {
      const likes = await api(`/posts/${button.dataset.like}/likes`);
      if (stamp === generation && button.isConnected) bindLike(button, button.dataset.like, likes);
    };
    try { await load(); }
    catch {
      if (stamp !== generation || !button.isConnected) return;
      button.innerHTML = html`${icon("heart")} ${t("Попробовать снова")}`;
      button.disabled = false;
      const retry = async () => {
        button.disabled = true;
        try { await load(); button.removeEventListener("click", retry); }
        catch (error) { toast(errorText(error)); button.disabled = false; }
      };
      button.addEventListener("click", retry);
    }
  }));
}
async function paged(root, path, itemHTML, stamp, blank) {
  const list = document.createElement("div");
  root.append(list);
  const more = document.createElement("button");
  more.className = "secondary load-more";
  more.textContent = t("Показать ещё");
  root.append(more);
  let cursor = null;
  async function load() {
    more.disabled = true;
    const page = await api(
      path +
        (path.includes("?") ? "&" : "?") +
        "limit=24" +
        (cursor ? "&cursor=" + encodeURIComponent(cursor) : ""),
    );
    if (stamp !== generation) return;
    cursor = page.next_cursor;
    list.insertAdjacentHTML("beforeend", page.items.map(itemHTML).join(""));
    if (!list.childElementCount) list.innerHTML = blank;
    if (list.querySelector(".project-card")) list.className = "project-grid";
    if (list.querySelector(".post-card")) {
      list.className = "post-grid";
      // Observe intrinsic card content, never the grid item whose span we change.
      postGridObserver ||= new ResizeObserver((entries) => {
        const styles = getComputedStyle(list);
        const gap = parseFloat(styles.rowGap);
        const row = parseFloat(styles.gridAutoRows);
        for (const { target } of entries) {
          const height = target.getBoundingClientRect().height;
          target.parentElement.style.gridRowEnd = `span ${Math.ceil((height + gap) / (row + gap))}`;
        }
      });
      list.querySelectorAll(".post-card-inner").forEach((card) => postGridObserver.observe(card));
    }
    more.hidden = !page.has_more;
    more.disabled = false;
    hydratePhotos(list, stamp);
    hydrateLikes(list, stamp);
  }
  actionButton(more, load);
  await load();
}
async function authScreen(root, route, stamp) {
  const [currentRoute, currentQuery = ""] = location.hash.slice(1).split("?");
  const currentParams = new URLSearchParams(currentQuery);
  const requestedNext = currentParams.get("next") || currentRoute + (currentRoute === "project-new" && /^[a-z0-9-]+$/.test(currentParams.get("inspired") || "") ? "?inspired=" + currentParams.get("inspired") : "");
  const next = /^(project\/[a-z0-9-]+|project-new(?:\?inspired=[a-z0-9-]+)?|saved|projects|applications|collaboration-profile|external-submit|project-claim\/[a-z0-9-]+)$/.test(requestedNext) ? requestedNext : "explore";
  const register = route === "register",
    reset = route === "recover";
  root.innerHTML = html`<div class="auth">${heading(t("Добро пожаловать"), reset ? t("Вернуться в Круг") : register ? t("Начните свою историю") : t("С возвращением"), reset ? t("Отправим ссылку для нового пароля, если email связан с аккаунтом.") : register ? t("Немного о себе — и вы среди своих.") : t("Войдите, чтобы читать своих людей и делиться мыслями."))}<div class="card">
      <form class="form">${reset ? input("email", "Email", "email", 'required maxlength="100" autocomplete="email"') : input("username", t("Имя пользователя"), "text", html`required ${register ? 'minlength="3"' : ""} maxlength="50" autocomplete="username"`) + (register ? input("email", t("Email · необязательно"), "email", 'maxlength="100" autocomplete="email"') + t('<span class="hint">Нужен для восстановления пароля и писем. Без email восстановить доступ не получится.</span>') : "") + input("password", t("Пароль"), "password", html`required ${register ? 'minlength="8"' : ""} maxlength="100" autocomplete="${register ? "new-password" : "current-password"}"`)}<button>${reset ? t("Отправить ссылку") : register ? t("Создать аккаунт") : t("Войти")}</button>
      </form>
      <div class="auth-switch">${register || reset ? t('<a href="/app#login">Уже есть аккаунт? Войти</a>') : t('<span>Первый раз здесь?</span><a href="/app#register">Регистрация</a>')}</div>${!register && !reset ? t('<a class="text-button small" href="/app#recover">Забыли пароль?</a>') : ""}</div>
      </div>`;
  root.querySelectorAll('.auth-switch a').forEach(link => {
    if (next !== "explore") link.href += "?next=" + encodeURIComponent(next);
  });
  bindForm(root.querySelector("form"), async (data) => {
    if (reset) {
      await api("/auth/password-reset/request", {
        method: "POST",
        body: { email: data.get("email") },
      });
      if (stamp === generation)
        root.querySelector("form").innerHTML =
          t('<p class="success" role="status">Если аккаунт существует, письмо скоро придёт. Проверьте также папку «Спам».</p>');
      return;
    }
    const body = {
      username: data.get("username"),
      password: data.get("password"),
    };
    if (register) {
      await api("/users", {
        method: "POST",
        body: { ...body, email: data.get("email") || null, language },
      });
    }
    const tokens = await api("/login", { method: "POST", body });
    saveSession(tokens);
    toast(register ? t("Аккаунт создан. Добро пожаловать!") : t("Вы вошли в Круг."));
    go(next);
  });
}
async function tokenScreen(root, stamp) {
  const reset = location.pathname === "/reset-password";
  const token = new URLSearchParams(location.hash.slice(1)).get("token") || accountLinkToken;
  if (token !== accountLinkToken) {
    accountLinkToken = token;
    accountLinkCompleted = false;
  }
  history.replaceState(null, "", location.pathname + location.search);
  root.innerHTML = html`<div class="auth">${heading(t("Ваш аккаунт"), reset ? t("Новый пароль") : t("Подтверждение email"), t("Ссылка одноразовая. Действие выполняется только после нажатия кнопки."))}<div class="card">${
    token
      ? html`<form class="form">${reset ? input("password", t("Новый пароль"), "password", 'required minlength="8" maxlength="100" autocomplete="new-password"') : ""}<button>${reset ? t("Сохранить пароль") : t("Подтвердить email")}</button>
      </form>`
      : t('<div class="error" role="alert">В ссылке нет токена. Запросите новое письмо.</div><a class="button" href="/app#') +
        (reset ? "recover" : "settings") +
        t('">Запросить письмо</a>')
  }</div>
      </div>`;
  const completedMarkup = () => html`<p class="success" role="status">${reset ? t("Пароль сохранён. Войдите с новым паролем.") : t("Email подтверждён. Теперь можно включить уведомления.")}</p><a class="button" href="/app#${reset ? "login" : "settings"}">${reset ? t("Войти") : t("К настройкам")}</a>`;
  if (accountLinkCompleted) {
    root.querySelector(".card").innerHTML = completedMarkup();
    return;
  }
  if (token)
    bindForm(root.querySelector("form"), async (data) => {
      await api(
        "/auth/" +
          (reset ? "password-reset" : "email-verification") +
          "/confirm",
        {
          method: "POST",
          body: { token, ...(reset ? { password: data.get("password") } : {}) },
        },
      );
      accountLinkCompleted = true;
      if (reset) saveSession(null);
      if (stamp === generation)
        root.querySelector(".card").innerHTML =
          html`<p class="success" role="status">${reset ? t("Пароль сохранён. Войдите с новым паролем.") : t("Email подтверждён. Теперь можно включить уведомления.")}</p>
      <a class="button" href="/app#${reset ? "login" : "settings"}">${reset ? t("Войти") : t("К настройкам")}</a>`;
    });
}
async function listing(root, route, query, stamp) {
  const own = route === "posts",
    feed = route === "feed",
    search = query.get("search") || "",
    language = query.get("language") || "simple",
    filter = query.get("filter") || "";
  root.innerHTML =
    heading(
      feed ? t("Ваши люди") : own ? t("Личный блокнот") : t("Открытый Круг"),
      feed
        ? t("Лента")
        : own
          ? t("Мои посты")
          : t("Обзор"),
      feed
        ? t("Новые публикации авторов, на которых вы подписаны.")
        : own
          ? t("Черновики видны только вам. Публикуйте, когда будете готовы.")
          : t("Мысли, открытия и маленькие моменты. Найдите то, что откликается."),
    ) +
    (!own ? html`<div class="tabs"><a href="/app#stories" class="${feed ? "" : "active"}">Истории</a>${session ? html`<a href="/app#feed" class="${feed ? "active" : ""}">Лента</a><a href="/app#posts">Мои записи</a><a href="/app#people">Связи</a><a href="/app#new">${icon("plus")} Создать пост</a>` : ""}</div>` : "") +
    (!feed
      ? html`<form class="search" role="search">
      <label class="field">
      <span class="hint">Поиск по публикациям</span>
      <input name="search" value="${esc(search)}" maxlength="100" placeholder="Что вам интересно?" aria-label="Поиск по публикациям">
      </label>
      <label class="field">
      <span class="hint">Язык поиска</span>
      <select name="language" aria-label="Язык поиска">
      <option value="simple">Любой</option>
      <option value="russian" ${language === "russian" ? "selected" : ""}>Русский</option>
      <option value="english" ${language === "english" ? "selected" : ""}>English</option>
      </select>
      </label>
      <button>Найти</button>
      </form>`
      : "") +
    (own
      ? html`<div class="tabs">
      <a href="/app#posts" class="${!filter ? "active" : ""}">Все</a>
      <a href="/app#posts?filter=true" class="${filter === "true" ? "active" : ""}">Опубликованные</a>
      <a href="/app#posts?filter=false" class="${filter === "false" ? "active" : ""}">Черновики</a>
      <a href="/app#new">${icon("plus")} Новый пост</a>
      </div>`
      : "");
  if (!feed)
    bindForm(root.querySelector("form"), async (data) =>
      go(
        route +
          "?" +
          new URLSearchParams({
            search: data.get("search"),
            language: data.get("language"),
            ...(filter ? { filter } : {}),
          }),
      ),
    );
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (!feed) params.set("search_language", language);
  if (own && filter) params.set("is_published", filter);
  await paged(
    root,
    (feed ? "/feed" : own ? "/posts" : "/explore") + "?" + params,
    (p) => postCard(p),
    stamp,
    empty(
      search
        ? t("Ничего не нашлось")
        : feed
          ? t("Лента ждёт ваших людей")
          : own
            ? t("Начните с первой строки")
            : t("Здесь пока тихо"),
      search
        ? t("Попробуйте другое слово или язык поиска.")
        : feed
          ? t("Откройте обзор и подпишитесь на интересных авторов.")
          : t("Новые истории появятся здесь."),
      html`<a class="button" href="/app#${feed ? "explore" : session ? "new" : "register"}">${feed ? t("Найти авторов") : t("Создать пост")}</a>`,
    ),
  );
}
async function profileScreen(root, id, stamp) {
  const profile = await api("/authors/" + id);
  const own = me?.id === profile.id;
  const follow =
    me && !own ? await api("/subscriptions/" + id + "/check") : null;
  if (stamp !== generation) return;
  root.innerHTML =
    html`<section class="card">
      <div class="profile-top">
      <span class="avatar large">${esc(profile.username[0].toUpperCase())}</span>
      <div>
      <h1>${esc(profile.display_name || profile.username)}</h1>
      <span class="small">@${esc(profile.username)}</span>
      </div>
      </div>
      <p class="bio">${esc(profile.bio) || t("Пока без описания. Истории расскажут больше.")}</p>
      <div class="toolbar">${own ? t('<a class="button secondary" href="/app#settings">Редактировать профиль</a><a class="text-button" href="/app#posts">Мои истории</a>') : me ? html`<button id="follow" class="${follow.subscribed ? "secondary" : ""}">${follow.subscribed ? t("Вы подписаны · отписаться") : t("Подписаться")}</button>` : t('<a class="button" href="/app#login">Войти и подписаться</a>')}</div>
      </section><section id="collaboration-profile" class="collaboration-profile"></section>${own && me?.role === "admin" ? t('<a class="text-button" href="/app#admin-review">Очередь проверки</a>') : ""}<h2>${t("Истории")}</h2><div class="stats"><span><strong>${profile.posts_count}</strong>${t("публикаций")}</span><span><strong>${profile.subscribers_count}</strong>${t("подписчиков")}</span><span><strong>${profile.subscriptions_count}</strong>${t("подписок")}</span></div>`;
  await collaborationProfileBlock(root, id, own, stamp);
  if (follow)
    actionButton(root.querySelector("#follow"), async () => {
      await api("/subscriptions" + (follow.subscribed ? "/" + id : ""), {
        method: follow.subscribed ? "DELETE" : "POST",
        ...(!follow.subscribed ? { body: { author_id: Number(id) } } : {}),
      });
      render();
    });
  await paged(
    root,
    html`/authors/${id}/posts`,
    (p) => postCard(p, profile.username),
    stamp,
    empty(
      t("Пока нет публикаций"),
      t("Когда автор опубликует историю, она появится здесь."),
    ),
  );
}
async function peopleScreen(root, query, stamp) {
  const followers = query.get("tab") === "subscribers";
  root.innerHTML =
    heading(
      t("Быть на связи"),
      t("Свои люди"),
      t("Подписывайтесь на тех, чьи истории хотите читать."),
    ) +
    html`<div class="tabs">
      <a href="/app#people" class="${!followers ? "active" : ""}">Подписки</a>
      <a href="/app#people?tab=subscribers" class="${followers ? "active" : ""}">Подписчики</a>
      </div>
      <div class="card" id="people-list">
      </div>`;
  await paged(
    root.querySelector("#people-list"),
    followers ? "/subscribers" : "/subscriptions",
    (p) =>
      html`<div class="person">
      <a class="avatar" href="/app#profile/${p.id}">${esc(p.username[0].toUpperCase())}</a>
      <a class="author" href="/app#profile/${p.id}">${esc(p.username)}</a>
      <a class="button secondary" href="/app#profile/${p.id}">Профиль ↗</a>
      </div>`,
    stamp,
    empty(
      t("Пока никого"),
      t("Ваш Круг постепенно станет больше."),
      t('<a class="button" href="/app#explore">Открыть обзор</a>'),
    ),
  );
}
async function editorScreen(root, id, stamp, query = new URLSearchParams()) {
  let post = id ? await api("/posts/" + id) : null;
  if (stamp !== generation) return;
  if (post && post.author_id !== me.id)
    throw new Error(t("Редактировать публикацию может только её автор."));
  root.innerHTML = html`<a class="back" href="/app#${post ? "post/" + id : "posts"}">← Назад</a>${heading(t("Творческая пауза"), post ? t("Редактировать пост") : t("Новый пост"), t("Пишите просто. Иногда одной мысли достаточно."))}<div class="card">
      <form class="form">${input("title", t("Заголовок · необязательно"), "text", t('maxlength="200" placeholder="Заголовок — по желанию"'))}<label class="field">Текст<textarea class="editor" name="content" required placeholder="Начните здесь…">
      </textarea>
      </label>
      <label class="field">Одно фото · необязательно<input name="image" type="file" accept="image/jpeg,image/png,image/webp">
      <span class="hint">JPEG, PNG или WebP, не больше 8 МиБ. Фото будет сохранено с публикацией.</span>
      </label>
      <div id="preview">${post ? photoMarkup(post) : ""}</div>${post?.image_url ? t('<label class="checkbox"><input type="checkbox" name="remove_image">Удалить текущее фото</label>') : ""}<label class="checkbox">
      <input type="checkbox" name="published" ${post?.is_published ? "checked" : ""}>Опубликовать для всех</label>
      <span class="hint">Если не отмечено, запись остаётся личным черновиком.</span>
      <button>${post ? t("Сохранить изменения") : t("Сохранить пост")}</button>
      <span class="hint" id="save-status" role="status">
      </span>
      </form>
      </div>`;
  const form = root.querySelector("form");
  const projectId = post?.project_id || (/^\d+$/.test(query.get("project") || "") ? Number(query.get("project")) : null);
  if (projectId) {
    const title = root.querySelector("h1");
    if (title) title.textContent = t(post ? "Редактировать обновление" : "Новое обновление проекта");
    form.querySelector("button").textContent = t("Сохранить обновление");

    const context = document.createElement("p");
    context.className = "project-editor-context";
    context.textContent = t("Обновление проекта");
    form.before(context);
  }
  form.elements.title.value = post?.title || "";
  form.elements.content.value = post?.content || "";
  hydratePhotos(root, stamp);
  let previewURL;
  form.elements.image.addEventListener("change", () => {
    if (previewURL) URL.revokeObjectURL(previewURL);
    const file = form.elements.image.files[0];
    const preview = root.querySelector("#preview");
    preview.replaceChildren();
    if (file) {
      previewURL = URL.createObjectURL(file);
      objectURLs.push(previewURL);
      const img = document.createElement("img");
      img.className = "photo-preview";
      img.alt = t("Предпросмотр выбранного фото");
      img.src = previewURL;
      preview.append(img);
    }
  });
  bindForm(form, async (data) => {
    const file = form.elements.image.files[0];
    if (
      file &&
      (!["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
        file.size > 8 * 1024 * 1024)
    )
      throw new Error(t("Выберите JPEG, PNG или WebP размером до 8 МиБ."));
    const published = data.has("published");
    const body = {
      title: data.get("title"),
      content: data.get("content"),
      is_published: published,
    };
    // Save a new photo post as a draft first: subscribers should see the complete story.
    if (!post) {
      post = await api("/posts", {
        method: "POST",
        body: { ...body, ...(projectId ? { project_id: projectId } : {}), is_published: file ? false : published },
      });
      // Keep the saved draft identity if photo upload fails or the UI language changes.
      history.replaceState(null, "", "/app#edit/" + post.id);
      form.querySelector("#save-status").textContent =
        t("Запись создана. Завершаем сохранение…");
    } else
      await api("/posts/" + post.id, {
        method: "PUT",
        body: {
          ...body,
          is_published: file && !post.is_published ? false : published,
        },
      });
    if (file)
      await api(html`/posts/${post.id}/image`, {
        method: "PUT",
        headers: { "Content-Type": file.type },
        body: file,
      });
    else if (data.has("remove_image"))
      await api(html`/posts/${post.id}/image`, { method: "DELETE" });
    if (file && published)
      await api("/posts/" + post.id, {
        method: "PUT",
        body: { is_published: true },
      });
    toast(t("Пост сохранён."));
    go("post/" + post.id);
  });
}
async function postScreen(root, id, stamp, projectSlug = null) {
  const post = await api("/posts/" + id);
  const [author, likes] = await Promise.all([
    api("/authors/" + post.author_id),
    api(html`/posts/${id}/likes`),
  ]);
  if (stamp !== generation) return;
  const own = me?.id === post.author_id;
  const projectLink = projectSlug ? "/project/" + encodeURIComponent(projectSlug) : "/app#stories";
  root.innerHTML = html`<a class="back" href="${projectLink}">${projectSlug ? t("К проекту") : t("К историям")}</a>
      <article class="card">
      <div class="post-meta">
      <a class="avatar" href="/app#profile/${author.id}">${esc(author.username[0].toUpperCase())}</a>
      <a class="author" href="/app#profile/${author.id}">${esc(author.username)}</a>
      <span>· ${date(post.created_at)}</span>${!post.is_published ? t('<span class="badge">Личный черновик</span>') : ""}</div>
      <h1 class="${post.title ? "article-title" : "sr-only"}">${post.title ? esc(post.title) : t("Публикация")}</h1>${photoMarkup(post, "article-photo")}<div class="article-body">${esc(post.content)}</div>
      <div class="toolbar">
      <button id="like" class="${likes.liked ? "liked" : "secondary"}" aria-pressed="${likes.liked}">${icon("heart")} ${likes.count} · ${likes.liked ? t("Нравится") : t("Поддержать")}</button>
      <span class="spacer">
      </span>${
        own
          ? html`<a class="button secondary" href="/app#edit/${id}">Редактировать</a>
      <button class="danger" id="delete">Удалить</button>`
          : ""
      }</div>
      <section class="comments" id="discussion">
      <h2>Комментарии</h2>${me ? t('<form class="form"><label class="field">Ваш комментарий<textarea name="content" required maxlength="2000" placeholder="Поделитесь мыслью…"></textarea></label><button>Отправить</button></form>') : t('<p class="intro"><a class="text-button" href="/app#login">Войдите</a>, чтобы присоединиться к разговору.</p>')}<div id="comments">
      </div>
      </section></article>`;
  const photosReady = hydratePhotos(root, stamp);
  bindLike(root.querySelector("#like"), id, likes);
  if (own)
    actionButton(root.querySelector("#delete"), async () => {
      if (
        !confirm(
          t("Удалить историю, фото и все комментарии? Это действие нельзя отменить."),
        )
      )
        return;
      await api("/posts/" + id, { method: "DELETE" });
      toast(t("История удалена."));
      go("posts");
    });
  if (me)
    bindForm(root.querySelector("form"), async (data) => {
      await api(html`/posts/${id}/comments`, {
        method: "POST",
        body: { content: data.get("content") },
      });
      toast(t("Комментарий отправлен."));
      render();
    });
  await paged(
    root.querySelector("#comments"),
    html`/posts/${id}/comments`,
    (c) =>
      html`<article class="comment" data-comment="${c.id}">
      <div class="post-meta">
      <a class="author" href="/app#profile/${c.user_id}">${esc(c.username)}</a>
      <span>${date(c.created_at)}</span>${me && (me.id === c.user_id || own) ? html`<button class="text-button" data-delete-comment="${c.id}" aria-label="Удалить комментарий ${esc(c.username)}">Удалить</button>` : ""}</div>
      <p>${esc(c.content)}</p>
      </article>`,
    stamp,
    empty(t("Начните разговор"), t("Оставьте первую мысль под этой историей.")),
  );
  root.querySelector("#comments").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-delete-comment]");
    if (!button || button.disabled) return;
    if (!confirm(t("Удалить комментарий?"))) return;
    button.disabled = true;
    try {
      await api(html`/posts/${id}/comments/${button.dataset.deleteComment}`, {
        method: "DELETE",
      });
      button.closest(".comment").remove();
      toast(t("Комментарий удалён."));
    } catch (error) {
      toast(errorText(error));
      button.disabled = false;
    }
  });
  // Settle the photo height before render scrolls to the requested discussion.
  await photosReady;
  await root.querySelector(".post-photo")?.decode().catch(() => {});
}
async function settingsScreen(root, stamp) {
  const settings = await api("/me/notifications");
  if (stamp !== generation) return;
  root.innerHTML =
    heading(
      t("Ваше пространство"),
      t("Настройки"),
      t("Немного о себе и о том, как оставаться на связи."),
    ) +
    html`<nav class="account-links" aria-label="${t("Мои разделы")}"><a href="/app#projects">${t("Мои проекты")}</a><a href="/app#saved">${t("Сохранённые проекты")}</a><a href="/app#applications">${t("Мои заявки")}</a><a href="/app#collaboration-profile">${t("Профиль для сотрудничества")}</a>${me.role === "admin" ? t('<a href="/app#admin-review">Проверка внешних проектов</a>') : ""}<a href="/app#external-submit">${t("Предложить внешний проект")}</a></nav><div class="settings-grid">
      <section class="card">
      <h2>Профиль</h2>
      <p class="small">@${esc(me.username)} · открытый профиль</p>
      <form class="form" id="profile-form">${input("display_name", t("Отображаемое имя"), "text", html`maxlength="100" value="${esc(me.display_name || "")}"`)}
      <label class="field">О себе<textarea name="bio" maxlength="500" placeholder="Что вам интересно?">${esc(me.bio)}</textarea>
      <span class="hint">До 500 символов. Видно всем.</span>
      </label>
      <button>Сохранить профиль</button>
      </form>
      </section>
      <section class="card">
      <h2>Email и уведомления</h2>
      <p>${esc(me.email) || t("Email не указан при регистрации.")}</p>
      <p class="hint">${me.email_verified ? t("✓ Email подтверждён.") : me.email ? t("Email ещё не подтверждён.") : t("В этой версии добавить email после регистрации нельзя.")}</p>${me.email && !me.email_verified ? t('<button class="secondary" id="verify">Отправить письмо для подтверждения</button>') : ""}<hr class="divider">
      <form class="form" id="notifications">
      <label class="checkbox">
      <input type="checkbox" name="enabled" ${settings.email_publications ? "checked" : ""} ${!me.email_verified || !me.email ? "disabled" : ""}>Новые истории подписок по email</label>
      <span class="hint">Лента работает независимо от писем. Уведомления доступны после подтверждения email.</span>
      <button>Сохранить уведомления</button>
      </form>
      </section>
      <section class="card">
      <h2>Доступ к аккаунту</h2>
      <p class="hint">Выход завершит все сессии на всех устройствах.</p>
      <div class="toolbar">
      <button class="secondary" id="logout">Выйти на всех устройствах</button>${me.email ? t('<a class="text-button" href="/app#recover">Изменить пароль</a>') : ""}</div>
      <hr class="divider">
      <h3>Удалить аккаунт</h3>
      <p class="hint">Все ваши истории, фото, подписки и комментарии будут удалены навсегда.</p>
      <button class="danger" id="delete-account">Удалить мой аккаунт</button>
      </section>
      </div>`;
  bindForm(root.querySelector("#profile-form"), async (data) => {
    await api("/me/profile", {
      method: "PATCH",
      body: { bio: data.get("bio"), display_name: data.get("display_name") || "" },
    });
    me.bio = data.get("bio");
    me.display_name = data.get("display_name") || "";
    toast(t("Профиль сохранён."));
  });
  bindForm(root.querySelector("#notifications"), async (data) => {
    await api("/me/notifications", {
      method: "PATCH",
      body: { email_publications: data.has("enabled") },
    });
    toast(t("Настройки уведомлений сохранены."));
  });
  if (root.querySelector("#verify"))
    actionButton(root.querySelector("#verify"), async () => {
      await api("/auth/email-verification/request", { method: "POST" });
      toast(t("Письмо запрошено. Проверьте входящие и папку «Спам»."));
    });
  actionButton(root.querySelector("#logout"), async () => {
    if (!confirm(t("Завершить все сессии на всех устройствах?"))) return;
    await api("/logout", { method: "POST" });
    saveSession(null);
    toast(t("Вы вышли на всех устройствах."));
    go("login");
  });
  actionButton(root.querySelector("#delete-account"), async () => {
    if (
      !confirm(
        t("Навсегда удалить аккаунт и все ваши данные? Это нельзя отменить."),
      )
    )
      return;
    await api("/users/" + me.id, { method: "DELETE" });
    saveSession(null);
    toast(t("Аккаунт удалён."));
    go("explore");
  });
}
async function render(options = {}) {
  const scroll = window.scrollY;
  const fields = options.preserve ? [...app.querySelectorAll("#main input, #main textarea, #main select")].map((el) => ({ name: el.name, value: el.value, checked: el.checked, files: el.files, form: [...app.querySelectorAll("#main form")].indexOf(el.form) })) : [];
  const stamp = ++generation;
  closePhotoViewer();
  postGridObserver?.disconnect();
  postGridObserver = null;
  objectURLs.forEach(URL.revokeObjectURL);
  objectURLs = [];
  const special = ["/verify-email", "/reset-password"].includes(
    location.pathname,
  );
  const [path, search = ""] = location.hash.slice(1).split("?");
  const publicParts = location.pathname.split("/").filter(Boolean);
  const publicProject = publicParts[0] === "project" ? publicParts[1] : null;
  const [hashRoute = "explore", hashId] = path.split("/");
  const route = publicProject ? (publicParts[2] === "updates" ? "post" : "project") : hashRoute;
  const id = publicProject ? (route === "post" ? publicParts[3] : publicProject) : hashId;
  const query = new URLSearchParams(search);
  try {
    if (session && !me && !special) {
      const current = session;
      const profile = await api("/me");
      if (session?.refresh_token === current.refresh_token) {
        if (!profile.language) {
          const choice = await api("/me/language?initialize=true", { method: "PATCH", body: { language } });
          profile.language = choice.language;
        }
        me = profile;
        language = profile.language;
        storePreference("krug-language", language);
        applyPreferences();
      }
    }
  } catch (error) {
    if (session) toast(errorText(error));
  }
  if (stamp !== generation) return;
  const root = shell(route || "explore");
  root.inert = true;
  root.setAttribute("aria-busy", "true");
  try {
    if (special) await tokenScreen(root, stamp);
    else if (
    ["feed", "posts", "people", "settings", "new", "edit", "saved", "projects", "project-new", "project-edit", "collaboration-profile", "external-submit", "admin-review", "applications", "project-claim"].includes(route) &&
      !session
    )
      await authScreen(root, "login", stamp);
    else if (["login", "register", "recover"].includes(route))
      await authScreen(root, route, stamp);
    else if (route === "profile" && /^\d+$/.test(id))
      await profileScreen(root, id, stamp);
    else if (route === "post" && /^\d+$/.test(id))
      await postScreen(root, id, stamp, publicProject);
    else if (route === "new" || (route === "edit" && /^\d+$/.test(id)))
      await editorScreen(root, id, stamp, query);
    else if (route === "project" && /^[a-z0-9-]+$/.test(id)) await projectScreen(root, id, stamp);
    else if (route === "project-interested" && /^[a-z0-9-]+$/.test(id)) await projectInterestedScreen(root, id, stamp);
    else if (route === "project-new" || (route === "project-edit" && /^[a-z0-9-]+$/.test(id))) await projectEditorScreen(root, route === "project-new" ? null : id, stamp, query);
    else if (route === "collaboration-profile") await collaborationProfileScreen(root, stamp);
    else if (route === "external-submit") await externalSubmissionScreen(root, stamp);
    else if (route === "project-claim" && /^[a-z0-9-]+$/.test(id)) await projectClaimScreen(root, id, stamp);
    else if (route === "admin-review" && me?.role === "admin") await adminReviewScreen(root, stamp);
    else if (route === "admin-review") root.innerHTML = heading("", t("Доступ закрыт"));
    else if (route === "applications") await applicationsScreen(root, stamp);
    else if (route === "saved" || route === "projects") await projectListScreen(root, route === "saved", stamp, query);
    else if (!route || route === "explore") await discoveryScreen(root, query, stamp);
    else if (route === "people") await peopleScreen(root, query, stamp);
    else if (route === "settings") await settingsScreen(root, stamp);
    else
      await listing(
        root,
        ["feed", "posts", "stories"].includes(route) ? route : "stories",
        query,
        stamp,
      );
    if (stamp === generation) {
      for (const saved of fields) {
        const form = root.querySelectorAll("form")[saved.form];
        const el = form?.elements.namedItem(saved.name);
        if (!el || el.disabled) continue;
        if (el.type === "file") {
          if (!saved.files.length) continue;
          const transfer = new DataTransfer();
          for (const file of saved.files) transfer.items.add(file);
          el.files = transfer.files;
          el.dispatchEvent(new Event("change"));
        } else if (["checkbox", "radio"].includes(el.type)) el.checked = saved.checked;
        else el.value = saved.value;
      }
      window.scrollTo(0, options.preserve ? scroll : 0);
      if (!options.preserve && route === "post" && query.has("comments"))
        root.querySelector("#discussion")?.scrollIntoView({ block: "start" });
    }
  } catch (error) {
    if (stamp !== generation) return;
    const box = document.createElement("div");
    box.className = "error";
    box.setAttribute("role", "alert");
    box.textContent = errorText(error);
    root.querySelector(".loading")?.remove();
    root.prepend(box);
    const retry = document.createElement("button");
    retry.textContent = t("Попробовать снова");
    retry.className = "secondary";
    retry.addEventListener("click", render);
    root.append(retry);
  } finally {
    root.inert = false;
    root.removeAttribute("aria-busy");
    if (stamp === generation && !options.preserve) root.focus({ preventScroll: true });
  }
}
// Keep the header DOM stable so preferences and focused controls survive scrolling.
let lastHeaderScroll = window.scrollY;
window.addEventListener("scroll", () => {
  const y = Math.max(0, window.scrollY);
  if (y < 80) document.body.classList.remove("header-compact");
  else if (Math.abs(y - lastHeaderScroll) >= 12)
    document.body.classList.toggle("header-compact", y > lastHeaderScroll);
  if (Math.abs(y - lastHeaderScroll) >= 12 || y < 80) lastHeaderScroll = y;
}, { passive: true });
window.addEventListener("hashchange", render);
render();
