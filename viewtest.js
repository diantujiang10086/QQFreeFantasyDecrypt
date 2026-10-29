/* Smoke test for the viewer's overview paging logic.
 *
 * Runs the real <script> from out/view/index.html against a minimal fake DOM
 * (extracted by the python one-liner into out/view/_check.js) and checks how
 * many thumbnail cards each page builds.
 *
 *   node viewtest.js
 */
const fs = require('fs');

const src = fs.readFileSync('out/view/_check.js', 'utf8');

function mkEl(tag) {
  const e = {
    tagName: String(tag || 'div').toUpperCase(), children: [], dataset: {}, style: {},
    value: '', checked: false, disabled: false, placeholder: '', max: 0, min: 0,
    scrollTop: 0, naturalWidth: 0, naturalHeight: 0, loading: '', decoding: '',
    _cls: new Set(),
  };
  e.classList = {
    add: (...c) => c.forEach(x => e._cls.add(x)),
    remove: (...c) => c.forEach(x => e._cls.delete(x)),
    contains: c => e._cls.has(c),
    toggle: (c, on) => {
      const has = e._cls.has(c);
      const want = on === undefined ? !has : !!on;
      if (want) e._cls.add(c); else e._cls.delete(c);
      return want;
    },
  };
  e.appendChild = c => {                     // fragments splice their children in
    if (c && c.tagName === '#FRAG') { e.children.push(...c.children); return c; }
    e.children.push(c); return c;
  };
  e.querySelector = () => mkEl('div');
  e.querySelectorAll = () => [];
  e.removeAttribute = () => {};
  e.setAttribute = () => {};
  e.addEventListener = () => {};
  Object.defineProperty(e, 'className',
    { get: () => [...e._cls].join(' '),
      set: v => { e._cls = new Set(String(v).split(/\s+/).filter(Boolean)); } });
  Object.defineProperty(e, 'innerHTML',
    { get: () => e._html || '', set: v => { e._html = v; e.children = []; } });
  Object.defineProperty(e, 'textContent',
    { get: () => e._txt || '', set: v => { e._txt = v; } });
  return e;
}

const reg = {};
global.document = {
  createElement: t => mkEl(t),
  createDocumentFragment: () => mkEl('#frag'),
  querySelector: s => reg[s] || (reg[s] = mkEl('div')),
  querySelectorAll: () => [],
  addEventListener: () => {},
};
global.Image = function () { return mkEl('img'); };
const manifest = JSON.parse(fs.readFileSync('out/view/manifest.json', 'utf8'));
global.fetch = () => Promise.resolve({ json: () => Promise.resolve(manifest) });
global.setInterval = () => 0;
global.clearInterval = () => {};

const api = new Function(src + `
return { applyFilter, renderOverview, gotoPage, nPages, build, badge,
         set M(v) { M = v; }, get M() { return M; },
         set perPage(v) { perPage = v; },
         get state() { return { page, perPage, n: list.length }; } };
`)();

api.M = manifest;
api.applyFilter();

let bad = 0;
const cards = () => reg['#grid'].children.length;
const meta = () => reg['#meta'].textContent;
const chk = (name, got, want) => {
  const ok = got === want;
  if (!ok) bad++;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
};

// The page's own default (the <select id="perPage"> first option) drives the
// expectations, so changing that option must not break this test.
const PP = api.state.perPage;
const N = manifest.entries.length;
chk('total entries', api.state.n, N);
chk('pages @default', api.nPages(), Math.ceil(N / PP));
chk('page 0 cards', cards(), PP);
chk('page 0 prev disabled', reg['#pgPrev'].disabled, true);
chk('page 0 next enabled', reg['#pgNext'].disabled, false);

api.gotoPage(1);
chk('page 1 cards', cards(), Math.min(PP, N - PP) === 0 ? 0 : PP);
chk('page 1 text', reg['#pgInfo'].textContent, `第 2 / ${api.nPages()} 页`);
chk('page 1 prev enabled', reg['#pgPrev'].disabled, false);

api.gotoPage(9999);
chk('clamped to last page', api.state.page, api.nPages() - 1);
chk('last page cards', cards(), N - (api.nPages() - 1) * PP);
chk('last page next disabled', reg['#pgNext'].disabled, true);

api.perPage = 1000;
api.renderOverview();
chk('perPage 1000 clamps page', api.state.page, Math.ceil(N / 1000) - 1);
chk('perPage 1000 cards', cards(), N - api.state.page * 1000);

api.gotoPage(0);
chk('page 0 with perPage 1000', cards(), 1000);
chk('meta mentions page', /第 1\/\d+ 页/.test(meta()), true);

// --- anchor-only tables (no pixel data anywhere) ------------------------------
// npc573201t: 60 records, every one pixel-less; the viewer must show the record
// prefixes as a table instead of a grid of broken thumbnails, and its badge must
// read 纯锚点表 rather than 未导出.
const anchor = manifest.entries.find(e => e.n === 'npc573201t');
chk('anchor entry is empty', anchor && anchor.st, 'empty');
chk('anchor badge text', api.badge(anchor).textContent, '纯锚点表');
const af = Array.from({ length: 60 }, (_, k) => ({
  dir: 1 + Math.floor(k / 12), k: k % 12, w: 0, h: 0, pre: 60 + 40 * k,
  px: null, bpp: 0, v: [0, 0, 0, -139, -229, 256],
  png: `d${1 + Math.floor(k / 12)}_${String(k % 12).padStart(3, '0')}.png`,
}));
api.build(anchor, { status: 'ok', frames: af });
const atab = reg['#grid'].children[0];
chk('anchor renders a table', atab && atab.tagName, 'TABLE');
chk('anchor table rows', atab.children.length, 61);        // header + 60 records
chk('anchor table cols', atab.children[0].children.length, 9);  // #,dir,k + 6 words
chk('anchor meta', meta(), '锚点表 · 60 条记录 · 0 张 PNG');

console.log(bad ? `\n${bad} FAILED` : '\nall paging checks passed');
process.exit(bad ? 1 : 0);
