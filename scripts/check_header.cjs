/* Check scroll direction, trackpad jitter and the return to the page top. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('frontend/app.js', 'utf8');
const start = source.indexOf('// Keep the header DOM stable');
const end = source.indexOf('window.addEventListener("hashchange"', start);
assert(start >= 0 && end > start, 'Header behavior is present');
const classes = new Set();
let onScroll;
const window = { scrollY: 0, addEventListener(event, callback, options) {
  assert.equal(event, 'scroll'); assert.equal(options.passive, true); onScroll = callback;
} };
vm.runInNewContext(source.slice(start, end), { window, document: { body: { classList: {
  remove: name => classes.delete(name),
  toggle: (name, force) => force ? classes.add(name) : classes.delete(name),
} } } });
for (const [y, compact] of [[79, false], [300, true], [296, true], [270, false], [274, false], [460, true], [400, false], [-2, false]]) {
  window.scrollY = y; onScroll();
  assert.equal(classes.has('header-compact'), compact, `Header state at scroll ${y}`);
}
console.log('Header direction, jitter tolerance and page-top recovery passed.');
