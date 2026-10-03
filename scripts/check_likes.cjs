/* Exercise the shared feed/article like control with the existing API contract. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('frontend/app.js', 'utf8');
let action, fail = false, route;
const calls = [];
const context = vm.createContext({
  me: { id: 1 }, t: value => value, icon: () => '<svg></svg>',
  html: (parts, ...values) => parts.reduce((text, part, i) => text + part + (values[i] ?? ''), ''),
  actionButton: (button, callback) => { action = callback; },
  go: value => { route = value; },
  api: async (path, options) => {
    calls.push([path, options.method]);
    if (fail) throw new Error('offline');
    return { count: options.method === 'PUT' ? 3 : 2, liked: options.method === 'PUT' };
  },
});
vm.runInContext(source.slice(source.indexOf('function bindLike('), source.indexOf('async function hydrateLikes(')), context);
const attrs = {};
const button = { isConnected: true, setAttribute: (key, value) => attrs[key] = value };
context.button = button;
async function main() {
  vm.runInContext('bindLike(button, 42, { count: 2, liked: false })', context);
  assert.equal(attrs['aria-pressed'], 'false');
  await action();
  assert.equal(attrs['aria-pressed'], 'true');
  assert(button.innerHTML.includes('3'));
  await action();
  assert.equal(attrs['aria-pressed'], 'false');
  fail = true;
  await assert.rejects(action, /offline/);
  assert.equal(attrs['aria-pressed'], 'false', 'Failed mutation keeps the confirmed state');
  fail = false;
  button.isConnected = false;
  await action();
  assert.equal(attrs['aria-pressed'], 'false', 'Detached screens are not updated');
  context.me = null;
  const before = calls.length;
  await action();
  assert.equal(route, 'login');
  assert.equal(calls.length, before);
  assert.deepEqual(calls.slice(0, 2), [['/posts/42/likes', 'PUT'], ['/posts/42/likes', 'DELETE']]);
  console.log('Like/unlike, failed mutation, detached screen and guest checks passed.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
