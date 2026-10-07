/* Static UI translations must be complete and must not touch template values. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function runtime(locale, saved = {}, query = '', systemDark = true) {
  const context = vm.createContext({
    URLSearchParams, location: { search: query }, navigator: { languages: Array.isArray(locale) ? locale : [locale] },
    localStorage: { getItem: key => saved[key] || null, setItem: (key, value) => saved[key] = value },
    matchMedia: () => ({ matches: systemDark, addEventListener() {} }),
    document: { documentElement: { dataset: {} }, querySelector: () => ({}) },
  });
  vm.runInContext(fs.readFileSync('frontend/i18n.js', 'utf8'), context);
  return code => vm.runInContext(code, context);
}
function transitionRuntime() {
  const root = { dataset: {}, style: { values: {}, setProperty(name, value) { this.values[name] = value; } } };
  const motion = { matches: false };
  const state = { starts: 0, skips: 0, readyRejections: 0 };
  const meta = {};
  const context = vm.createContext({
    URLSearchParams, location: { search: '' }, navigator: { languages: ['en-US'] },
    localStorage: { getItem: key => key === 'krug-theme' ? 'light' : null, setItem() {} },
    matchMedia: query => query.includes('reduced-motion') ? motion : { matches: true, addEventListener() {} },
    document: {
      documentElement: root, title: '', querySelector: selector => selector === '#ui-theme' ? { getBoundingClientRect: () => ({ left: 10, top: 20, width: 44, height: 44 }) } : meta,
      startViewTransition(update) {
        state.starts++;
        let finish;
        let rejectReady;
        const transition = {
          ready: new Promise((resolve, reject) => { rejectReady = reject; }),
          finished: new Promise(resolve => { finish = resolve; }),
          skipTransition() { state.skips++; update(); finish(); state.readyRejections++; rejectReady(new Error('Transition was skipped')); },
        };
        return transition;
      },
    },
  });
  vm.runInContext(fs.readFileSync('frontend/i18n.js', 'utf8'), context);
  return { run: code => vm.runInContext(code, context), root, motion, state, context };
}
const en = runtime('en-US');
assert.equal(en('language'), 'en');
assert.equal(en('document.documentElement.dataset.theme'), 'dark');
assert.equal(runtime('en-US', {}, '', false)('document.documentElement.dataset.theme'), 'dark');
assert.equal(runtime('en-US', { 'krug-theme': 'system' }, '', false)('document.documentElement.dataset.theme'), 'light');
assert.equal(runtime('en-US', { 'krug-theme': 'light' })('document.documentElement.dataset.theme'), 'light');
assert.equal(runtime('ru-RU')('language'), 'ru');
assert.equal(runtime(['en-US', 'ru'])('language'), 'en');
assert.equal(runtime(['ru-RU', 'en'])('language'), 'ru');
assert.equal(runtime(['fr-FR', 'ru', 'en'])('language'), 'ru');
assert.equal(runtime('ru-RU', { 'krug-language': 'en' })('language'), 'en');
assert.equal(runtime('en-US', {}, '?lang=ru')('language'), 'ru');
assert.equal(runtime('fr-FR', { 'krug-language': 'bad' })('language'), 'en');
const preferences = transitionRuntime();
preferences.run("theme = 'dark'; applyPreferences({ transitionTheme: true });");
assert.equal(preferences.state.starts, 1);
assert.equal(preferences.root.style.values['--theme-origin-x'], '32px');
assert.equal(preferences.root.style.values['--theme-origin-y'], '42px');
preferences.run("theme = 'light'; applyPreferences({ transitionTheme: true });");
assert.equal(preferences.state.skips, 1, 'Returning to the rendered theme interrupts its pending transition');
assert.equal(preferences.root.dataset.theme, 'light');
preferences.run("theme = 'dark'; applyPreferences({ transitionTheme: true });");
preferences.motion.matches = true;
preferences.run("theme = 'dark'; applyPreferences({ transitionTheme: true });");
assert.equal(preferences.state.skips, 2, 'Reduced motion cancels a pending transition');
assert.equal(preferences.root.dataset.theme, 'dark');
preferences.motion.matches = false;
preferences.context.document.startViewTransition = undefined;
preferences.run("theme = 'light'; applyPreferences({ transitionTheme: true });");
assert.equal(preferences.root.dataset.theme, 'light', 'Unsupported browsers apply the theme immediately');
assert.equal(en('t("Неверное имя пользователя или пароль.")'), 'Incorrect username or password.');
assert.equal(en('html`<p>Автор ${"Автор Настройки <b>user text</b>"}</p>`'), '<p>Author Автор Настройки <b>user text</b></p>');
const source = ['frontend/app.js', 'frontend/projects.js'].map(path => fs.readFileSync(path, 'utf8')).join('\n');
for (const fragment of source.match(/[\u0400-\u04ff][^<>"'`{}\n]*/g) || []) {
  const copy = fragment.trim().replace(/\$$/, '').trim();
  if (copy === 'Русский / English' || copy === 'Русский') continue;
  const translated = en(`t(${JSON.stringify(copy)})`);
  assert(!/[\u0400-\u04ff]/.test(translated), `Missing translation: ${copy} → ${translated}`);
}
const unhandledTransitionErrors = [];
const trackUnhandled = error => unhandledTransitionErrors.push(error);
process.on('unhandledRejection', trackUnhandled);
setImmediate(() => {
  process.off('unhandledRejection', trackUnhandled);
  assert(preferences.state.readyRejections > 0, 'The transition mock rejects ready when a transition is skipped');
  assert.deepEqual(unhandledTransitionErrors, [], 'Skipped transition ready rejections are consumed');
  console.log('UI language defaults, translation coverage and user-content isolation passed.');
});
