/* html`` escapes interpolated values by default; SafeHtml, esc() and arrays are not escaped twice. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({
  URLSearchParams, location: { search: '' }, navigator: { languages: ['ru'] },
  localStorage: { getItem: () => null, setItem() {} },
  matchMedia: () => ({ matches: true, addEventListener() {} }),
  document: { documentElement: { dataset: {} }, querySelector: () => ({}) },
});
vm.runInContext(fs.readFileSync('frontend/i18n.js', 'utf8'), context);
const run = code => String(vm.runInContext(code, context));
const hostile = '<img src=x onerror=alert(1)>&"\'';
const escaped = '&lt;img src=x onerror=alert(1)&gt;&amp;&quot;&#39;';

assert.equal(run('html`<p>${' + JSON.stringify(hostile) + '}</p>`'), '<p>' + escaped + '</p>', 'Plain strings are escaped');
assert.equal(run('html`<p title="${' + JSON.stringify(hostile) + '}"></p>`'), '<p title="' + escaped + '"></p>', 'Attribute values are escaped');
assert.equal(run('html`<p>${7} ${0}</p>`'), '<p>7 0</p>', 'Numbers, including zero, are kept');
assert.equal(run('html`<i>${html`<b>${"a&b"}</b>`}</i>`'), '<i><b>a&amp;b</b></i>', 'Nested html is not escaped twice');
assert.equal(run('html`<p>${esc(' + JSON.stringify(hostile) + ')}</p>`'), '<p>' + escaped + '</p>', 'esc() output is not escaped twice');
assert.equal(run('esc("<b>") + "&"'), '&lt;b&gt;&', 'esc() still concatenates as a string');
assert.equal(run('esc(null) + esc(undefined)'), '', 'esc() of null and undefined is empty');
assert.equal(run('html`<ul>${["a<", html`<li>b</li>`, esc("c>"), null, false, ["d&"]]}</ul>`'), '<ul>a&lt;<li>b</li>c&gt;d&amp;</ul>', 'Arrays are processed item by item and nested');
assert.equal(run('html`<p>${null}${undefined}${false}</p>`'), '<p></p>', 'null, undefined and false render nothing');
assert.equal(run('html`<p>${true}</p>`'), '<p>true</p>');
assert.equal(run('html`<p>${[].map(String)}</p>`'), '<p></p>', 'Empty array renders nothing');
assert.equal(run('html`<p>${' + JSON.stringify(hostile) + '}</p>`.constructor.name'), 'SafeHtml');
assert.equal(run('raw("<br>") instanceof html``.constructor'), 'true', 'raw() marks trusted markup');
assert.equal(run('html`<p>${raw("<br>")}</p>`'), '<p><br></p>', 'raw() markup is inserted as is');
// A joined array is a plain string again and gets escaped: the reason call sites pass arrays directly.
assert.equal(run('html`<p>${[html`<b>x</b>`].join("")}</p>`'), '<p>&lt;b&gt;x&lt;/b&gt;</p>');
// Static parts keep their translation behavior; interpolated values are never translated.
assert.equal(run('html`<p>Привет ${"Привет"}</p>`'), '<p>Привет Привет</p>');
console.log('html`` escapes values by default, keeps SafeHtml, arrays and esc() intact.');
