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
assert.equal(en('t("Неверное имя пользователя или пароль.")'), 'Incorrect username or password.');
assert.equal(en('html`<p>Автор ${"Автор Настройки <b>user text</b>"}</p>`'), '<p>Author Автор Настройки <b>user text</b></p>');
const source = fs.readFileSync('frontend/app.js', 'utf8');
for (const fragment of source.match(/[\u0400-\u04ff][^<>"'`{}\n]*/g) || []) {
  const copy = fragment.trim().replace(/\$$/, '').trim();
  if (copy === 'Русский / English' || copy === 'Русский') continue;
  const translated = en(`t(${JSON.stringify(copy)})`);
  assert(!/[\u0400-\u04ff]/.test(translated), `Missing translation: ${copy} → ${translated}`);
}
console.log('UI language defaults, translation coverage and user-content isolation passed.');
