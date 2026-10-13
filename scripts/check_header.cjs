/* The header has no scroll state: no scroll listener, no compact body class in the app or CSS. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const app = fs.readFileSync('frontend/app.js', 'utf8');
const css = fs.readFileSync('frontend/style.css', 'utf8');
assert(!app.includes('header-compact') && !css.includes('header-compact'), 'No header-compact state remains');
assert(!app.includes('addEventListener("scroll"'), 'App adds no scroll listener that could change the header');
assert(app.includes('window.addEventListener("hashchange", render);'), 'Route changes still re-render the page');
console.log('Header is static: no scroll listener and no compact state in app or CSS.');
