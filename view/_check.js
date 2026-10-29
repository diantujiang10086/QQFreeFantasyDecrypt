
const IMG = '../export/';
const SRCDIR = 'F:\\WG自由幻想\\自由幻想\\data\\data\\official\\avatar\\npc\\';
let M = null, list = [];
let cur = null, meta = null, frames = [], groups = [], gi = 0, idx = 0;
let playing = false, timer = null, zoom = 0, bg = 'checker';
let viewMode = 'grid';
let page = 0, perPage = 52;

const $ = s => document.querySelector(s);
const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c;
  if (h !== undefined) e.textContent = h; return e; };
const kb = n => n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KiB'
  : n < 1073741824 ? (n / 1048576).toFixed(2) + ' MiB' : (n / 1073741824).toFixed(2) + ' GiB';
const pad = (n, w) => String(n).padStart(w, '0');
const firstPng = e => (e.d && e.d.length) ? 'd1_000.png' : 'f0000.png';

/* ---- thumbnail loading: bounded concurrency + retry ----------------------
   One page builds up to 300 <img> at once. Left to the browser they all fire
   together, and a local static server that is still busy with the previous
   page's (now cancelled) requests can fail some of them; an un-retried failure
   is then indistinguishable from a genuinely missing file, so the card shows
   "缩略图缺失". Load a handful at a time, retry with back-off, and only report
   missing after every attempt failed. */
const LOAD = { max: 8, cur: 0, q: [] };
let gen = 0;                        // bumped on every re-render: drops stale jobs
function pumpLoad() {
  while (LOAD.cur < LOAD.max && LOAD.q.length) {
    const job = LOAD.q.shift();
    LOAD.cur++;
    job(() => { LOAD.cur--; pumpLoad(); });
  }
}
function loadOnce(url, cb) {
  const im = new Image();
  let done = false;
  const fin = ok => {
    if (done) return;
    done = true; im.onload = im.onerror = null;
    cb(ok ? im : null);
  };
  im.onload = () => fin(true);
  im.onerror = () => fin(false);
  im.src = url;
}
const THUMB_TRIES = 3;
/* try every candidate `urls` in order, THUMB_TRIES times each, backing off */
function loadThumb(urls, onOk, onFail) {
  const myGen = gen;
  let ci = 0, n = 0;
  const step = () => {
    if (myGen !== gen) return;                 // the page/view changed meanwhile
    const url = urls[ci];
    const attempt = n;
    const bust = attempt ? (url.includes('?') ? '&' : '?') + 'r=' + attempt : '';
    LOAD.q.push(release => {
      if (myGen !== gen) { release(); return; }
      loadOnce(url + bust, im => {
        release();
        if (myGen !== gen) return;
        if (im) { onOk(im); return; }
        if (attempt + 1 < THUMB_TRIES) {
          n = attempt + 1;
          setTimeout(step, 200 * (attempt + 1));
        } else if (ci + 1 < urls.length) {
          ci++; n = 0;
          setTimeout(step, 100);
        } else {
          onFail(urls);
        }
      });
    });
    pumpLoad();
  };
  step();
}
/* only start loading a card once it is near the viewport */
const nearView = (typeof IntersectionObserver === 'function')
  ? new IntersectionObserver(ents => {
      for (const en of ents) {
        if (!en.isIntersecting) continue;
        const f = en.target.__load;
        if (f) { en.target.__load = null; nearView.unobserve(en.target); f(); }
      }
    }, { rootMargin: '400px' })
  : null;
function whenNear(node, fn) {
  if (!nearView) { fn(); return; }
  node.__load = fn;
  nearView.observe(node);
}

function setView(m) {
  viewMode = m;
  $('#viewSingle').classList.toggle('on', m === 'single');
  $('#viewGrid').classList.toggle('on', m === 'grid');
  $('#stage').style.display = m === 'single' ? '' : 'none';
  $('#frameCtl').style.display = m === 'single' ? '' : 'none';
  $('#gridCtl').style.display = m === 'single' ? 'none' : '';
  if (m === 'grid' && cur !== null) page = Math.floor(cur / perPage);
  renderPane();
}

function renderPane() {
  if (viewMode === 'grid') { renderOverview(); return; }
  if (!list.length) { $('#grid').innerHTML = ''; return; }
  if (cur === null || !list[cur]) cur = 0;
  select(cur);
}

const nPages = () => Math.max(1, Math.ceil(list.length / perPage));

function updatePager() {
  const np = nPages();
  $('#pgInfo').textContent = list.length ? `第 ${page + 1} / ${np} 页` : '无匹配';
  $('#pgFirst').disabled = $('#pgPrev').disabled = page <= 0;
  $('#pgNext').disabled = $('#pgLast').disabled = page >= np - 1;
  $('#pgJump').max = np;
  $('#pgJump').placeholder = `1-${np}`;
}

function gotoPage(p) {
  page = Math.max(0, Math.min(p | 0, nPages() - 1));
  renderOverview();
  $('#grid').scrollTop = 0;
  $('#pgJump').value = '';
}

/* overview: the first frame of every NPC, one card each -- one page at a time */
let missCells = [];                  // cards whose thumbnails failed, for 重试缺失
function renderOverview() {
  const box = $('#grid');
  box.classList.add('ov');
  gen++;                             // cancel anything still loading for the old page
  LOAD.q.length = 0;
  missCells = [];
  box.innerHTML = '';
  $('#stage').style.display = 'none';
  $('#frameCtl').style.display = 'none';
  const np = nPages();
  page = Math.max(0, Math.min(page, np - 1));
  const base = page * perPage, end = Math.min(base + perPage, list.length);
  const frag = document.createDocumentFragment();
  for (let i = base; i < end; i++) {
    const e = list[i];
    const c = el('div', 'npc' + (cur === i ? ' cur' : ''));
    const th = el('div', 'th');
    if (e.c) {
      // Show the folder's real first frame (e.f0, from mkview's disk scan); the
      // conventional name is only a fallback for manifests without e.f0.
      const names = [e.f0 || firstPng(e)];
      if (!names.includes(firstPng(e))) names.push(firstPng(e));
      const urls = names.map(n => IMG + e.n + '/' + n);
      th.__start = () => {
        th.className = 'th';
        th.textContent = '';
        th.removeAttribute('title');
        loadThumb(urls, im => {
          im.loading = 'lazy'; im.decoding = 'async';
          th.textContent = '';
          th.appendChild(im);
          const s = c.querySelector('.wh');
          if (s) s.textContent = `${im.naturalWidth}x${im.naturalHeight}`;
        }, tries => {
          th.className = 'th miss';
          th.textContent = '缩略图缺失';
          th.title = `重试 ${THUMB_TRIES} 次仍失败：\n${tries.join('\n')}`;
          if (!missCells.includes(th)) missCells.push(th);
          $('#retryMiss').disabled = false;
          const m = $('#meta');
          m.textContent = m.textContent.replace(/ · 缩略图缺失 \d+/, '') +
            ` · 缩略图缺失 ${missCells.length}`;
        });
      };
      whenNear(th, th.__start);
    } else {
      th.className = 'th miss';
      th.textContent = e.st === 'empty' ? '纯锚点表' : (e.st === 'fail' ? '解析失败' : '未导出');
    }
    c.appendChild(th);
    c.appendChild(el('div', 'nm', e.n));
    c.appendChild(el('div', 'sub', `v${e.v} · ${e.f}帧${e.k ? ' 空' + e.k : ''}`));
    const lo = el('div', 'sub');
    lo.appendChild(badge(e));
    lo.appendChild(el('span', 'wh dim'));
    c.appendChild(lo);
    c.addEventListener('click', () => { cur = i; setView('single'); });
    frag.appendChild(c);
  }
  box.appendChild(frag);
  updatePager();
  $('#meta').textContent = list.length
    ? `总览：第 ${page + 1}/${np} 页 · 本页 ${end - base} 个 / 共 ${list.length} 个 NPC`
    : '总览：没有匹配的 NPC';
  $('#retryMiss').disabled = true;
}

function badge(e) {
  // `e.c` is the number of PNGs on disk: an anchor-only table has none, but it
  // is *not* an export failure, so it must not fall through to "未导出".
  const cls = e.st === 'empty' ? 'b-empty'
    : (e.c ? ({ ok: 'b-ok', partial: 'b-partial', fail: 'b-fail' }[e.st] || 'b-ok')
           : 'b-none');
  const txt = e.st === 'empty' ? '纯锚点表'
    : (e.c ? ({ ok: '正常', partial: '部分', fail: '失败' }[e.st] || e.st)
           : (e.st === 'fail' ? '失败' : '未导出'));
  const b = el('span', 'badge ' + cls, txt);
  return b;
}

fetch('manifest.json').then(r => r.json()).then(m => {
  M = m;
  const t = m.totals;
  $('#totals').textContent = `${t.files} 文件 · ${t.frames} 帧 · ${t.pngs} PNG · ${kb(t.bytes)}` +
    ` · 生成 ${t.generated}`;
  const vers = [...new Set(m.entries.map(e => e.v))].sort();
  for (const v of vers) { const o = el('option', null, v); o.value = v; $('#ver').appendChild(o); }
  applyFilter();
}).catch(err => { $('#info').textContent = '读取 manifest.json 失败: ' + err; });

function applyFilter() {
  const q = $('#q').value.trim(), st = $('#status').value, ver = $('#ver').value;
  list = M.entries.filter(e => {
    if (q && !e.n.includes(q) && !(e.v || '').includes(q)) return false;
    if (st && e.st !== st) return false;
    if (ver && e.v !== ver) return false;
    if ($('#onlyExported').checked && !e.c) return false;
    if ($('#onlyBad').checked && !['fail', 'partial', 'empty'].includes(e.st)) return false;
    return true;
  });
  page = 0;
  renderPane();
}
['q', 'status', 'ver', 'onlyExported', 'onlyBad'].forEach(id =>
  $('#' + id).addEventListener('input', applyFilter));
$('#viewGrid').addEventListener('click', () => setView('grid'));
$('#viewSingle').addEventListener('click', () => setView('single'));
$('#pgFirst').addEventListener('click', () => gotoPage(0));
$('#pgPrev').addEventListener('click', () => gotoPage(page - 1));
$('#pgNext').addEventListener('click', () => gotoPage(page + 1));
$('#pgLast').addEventListener('click', () => gotoPage(nPages() - 1));
$('#perPage').addEventListener('change', () => {
  perPage = +$('#perPage').value || 300; page = 0;
  if (viewMode === 'grid') renderOverview();
});
$('#retryMiss').addEventListener('click', () => {        // re-fetch what failed
  const cells = missCells.slice();
  missCells = [];
  $('#retryMiss').disabled = true;
  $('#meta').textContent = $('#meta').textContent.replace(/ · 缩略图缺失 \d+/, '');
  cells.forEach(th => { if (th.__start) th.__start(); });
});
$('#pgJump').addEventListener('change', () => {
  const v = parseInt($('#pgJump').value, 10);
  if (v >= 1) gotoPage(v - 1);
});

function select(i) {
  stop();
  const e = list[i];
  cur = i;
  meta = null; frames = []; groups = []; gi = 0; idx = 0;
  $('#big').removeAttribute('src');
  info(e, null);
  build(e, null);
  fetch('/api/frames/' + e.n).then(r => r.json()).then(m => {
    if (!cur || list[cur].n !== e.n) return;
    meta = m; info(e, m); build(e, m);
  }).catch(err => { $('#meta').textContent = 'API 失败: ' + err; });
}

function info(e, m) {
  const L = [];
  L.push(`${e.n}.gsn   版本 v${e.v}   状态 ${e.st}   体积 ${e.s} B` + '   源文件: ' + SRCDIR + e.n + '.gsn');
  // L.push(`帧数 ${e.f}   空帧 ${e.k}   方向数 ${e.d.length || '?'}   ` +
  //        `dir表 ${e.d.length ? e.d.join(' / ') : '(空)'}   oh=${e.o} first_px=${e.p} method=${e.m}`);
  // L.push(`磁盘 PNG ${e.c || 0} 个 (${kb(e.b || 0)})`);
  // if (e.e) L.push('记录: ' + e.e);
  // if (m && m.status === 'ok') L.push(`复核(dimg): oh=${m.oh} first_px=${m.first_px} ` +
  //   `tail=${m.tail} end=${m.end} skipped=${m.skipped} method=${m.method}`);
  // if (m && m.status !== 'ok') L.push('复核(dimg)失败: ' + (m.tried || []).join(' ; '));
  // L.push('源文件: ' + SRCDIR + e.n + '.gsn');
  $('#info').textContent = L.join('\n');
}

function build(e, m) {
  frames = [];
  if (m && m.frames && m.frames.length) {
    frames = m.frames.slice();
  } else if (m && m.status === 'fail') {
    frames = [];
  } else {
    const dirs = (e.d && e.d.length) ? e.d : (e.st === 'empty' ? [] : [e.f]);
    const flat = !(e.d && e.d.length);
    dirs.forEach((c, di) => {
      for (let k = 0; k < c; k++)
        frames.push({ dir: di + 1, k, png: flat ? `f${pad(k, 4)}.png` : `d${di + 1}_${pad(k, 3)}.png` });
    });
  }
  // Anchor-only table: every record is pixel-less, so there is no image at all.
  // Show the record prefixes (the anchor values) instead of an empty frame grid.
  if (frames.length && frames.every(f => f.px === null) && frames.some(f => Array.isArray(f.v))) {
    renderAnchor(e, frames);
    return;
  }
  groups = [];
  const byDir = new Map();
  for (const f of frames) {
    if (!byDir.has(f.dir)) { byDir.set(f.dir, []); groups.push(f.dir); }
    byDir.get(f.dir).push(f);
  }
  groups = groups.map(d => ({ d, items: byDir.get(d) }));
  if (!groups.length) {
    const note = e.st === 'empty'
      ? '这个文件是纯锚点表：' + e.f + ' 帧全部无像素，因此没有 PNG。'
      : (m && m.status === 'fail' ? 'dimg 解析失败，无法列出帧。' : '没有可显示的帧。');
    $('#dirs').innerHTML = `<span class="dim">${note}</span>`;
    $('#grid').innerHTML = '';
    $('#meta').textContent = '';
    return;
  }
  gi = Math.min(gi, groups.length - 1);
  renderDirs(); renderGrid(); show(0);
}

function renderAnchor(e, frames) {
  stop();
  groups = [];
  const img = $('#big');
  img.removeAttribute('src');
  img.style.width = 'auto';
  const nv = Math.max.apply(null, frames.map(f => (f.v || []).length));
  const box = $('#dirs'); box.innerHTML = '';
  const n = el('div', 'dim');
  n.innerHTML = `纯锚点表：<b>${frames.length}</b> 条记录<b>全部无像素</b>（记录签名 4 个字全 0），` +
    `文件里没有任何图像数据，所以不会产生 PNG —— 不是导出失败。` +
    `每条记录的 <b>${nv}</b> 个 32 位前缀整数就是锚点数值（有符号十进制，括号内为补码十六进制）。`;
  box.appendChild(n);
  const t = document.createElement('table');
  t.className = 'anchors';
  const hr = document.createElement('tr');
  ['#', '方向', '帧号'].forEach(h => hr.appendChild(el('th', null, h)));
  for (let i = 0; i < nv; i++) hr.appendChild(el('th', null, `前缀字${i}`));
  t.appendChild(hr);
  frames.forEach(f => {
    const r = document.createElement('tr');
    r.appendChild(el('td', 'dim', String(f.k + 1)));
    r.appendChild(el('td', 'dim', `方向 ${f.dir}`));
    r.appendChild(el('td', 'dim', String(f.k)));
    (f.v || []).forEach(x => {
      const td = document.createElement('td');
      td.className = 'num';
      td.innerHTML = `${x}<span class="dim"> (0x${(x >>> 0).toString(16)})</span>`;
      r.appendChild(td);
    });
    t.appendChild(r);
  });
  const g = $('#grid'); g.classList.remove('ov'); g.innerHTML = '';
  g.appendChild(t);
  $('#meta').textContent = `锚点表 · ${frames.length} 条记录 · 0 张 PNG`;
}

function renderDirs() {
  const box = $('#dirs'); box.innerHTML = '';
  groups.forEach((g, i) => {
    const b = el('button', i === gi ? 'on' : '', `方向 ${g.d} (${g.items.length})`);
    b.addEventListener('click', () => { gi = i; idx = 0; renderDirs(); renderGrid(); show(0); });
    box.appendChild(b);
  });
}

function renderGrid() {
  const box = $('#grid'); box.classList.remove('ov'); box.innerHTML = '';
  gen++; LOAD.q.length = 0;                  // frame view: same bounded loader
  const frag = document.createDocumentFragment();
  groups[gi].items.forEach((f, k) => {
    const c = el('div', 'cell' + (k === idx ? ' cur' : ''));
    c.dataset.k = k;
    if (f.px === null) {                     // pixel-less frame: nothing to show
      c.classList.add('emptycell');
      c.appendChild(el('div', 'lb', `#${f.k} 空帧`));
      c.addEventListener('click', () => { stop(); show(k); });
      frag.appendChild(c);
      return;
    }
    const url = IMG + cur0().n + '/' + f.png;
    loadThumb([url], im => {
      im.loading = 'lazy';
      c.insertBefore(im, c.firstChild);
    }, tries => {
      c.classList.add('missing');
      c.title = `重试 ${THUMB_TRIES} 次仍失败：\n${tries.join('\n')}`;
    });
    c.appendChild(el('div', 'lb', `#${f.k}${f.w ? ' ' + f.w + 'x' + f.h : ''}`));
    c.addEventListener('click', () => { stop(); show(k); });
    frag.appendChild(c);
  });
  box.appendChild(frag);
}
const cur0 = () => list[cur];

function show(k) {
  const g = groups[gi];
  idx = Math.max(0, Math.min(k, g.items.length - 1));
  const f = g.items[idx];
  const img = $('#big');
  if (f.px === null) {                       // pixel-less frame (reuses the previous one)
    img.removeAttribute('src');
    img.style.width = 'auto';
    $('#meta').innerHTML = `方向 ${f.dir} 第 ${f.k} 帧 (组内 ${idx + 1}/${g.items.length}) · ` +
      `<span class="dim">空帧：无像素数据，4 字签名全 0，仍计入帧数/方向表</span>`;
    [...document.querySelectorAll('.cell')].forEach((c, j) => c.classList.toggle('cur', j === idx));
    return;
  }
  img.src = IMG + cur0().n + '/' + f.png;
  img.onload = () => {
    const z = zoom || (f.w ? Math.min(4, Math.max(1, 380 / Math.max(f.w, f.h))) : 1);
    img.style.width = (zoom ? img.naturalWidth * zoom : (f.w ? f.w * z : img.naturalWidth)) + 'px';
    img.style.height = 'auto';
    const exp = f.w ? `${f.w}x${f.h}` : '?';
    const act = `${img.naturalWidth}x${img.naturalHeight}`;
    const same = !f.w || (img.naturalWidth === f.w && img.naturalHeight === f.h);
    $('#meta').innerHTML =
      `方向 ${f.dir} 第 ${f.k} 帧 (组内 ${idx + 1}/${g.items.length}) · ` +
      `期望 ${exp} / 实际 ${act} <span class="${same ? 'ok' : 'bad'}">${same ? '✓ 一致' : '✗ 不一致'}</span>` +
      (f.px !== undefined ? ` · 像素偏移 ${f.px} · ${f.png}` : ` · ${f.png}`);
  };
  img.onerror = () => {                      // one retry before calling it missing
    $('#meta').innerHTML = `<span class="bad">图像加载失败: ${f.png}（重试中…）</span>`;
    loadThumb([IMG + cur0().n + '/' + f.png],
      () => { if (groups[gi] && g.items[idx] === f) show(idx); },
      () => { $('#meta').innerHTML = `<span class="bad">图像缺失: ${f.png}</span>`; });
  };
  [...document.querySelectorAll('.cell')].forEach((c, j) => c.classList.toggle('cur', j === idx));
  preload();
}

function preload() {
  const g = groups[gi], n = cur0().n;
  for (let d = -2; d <= 2; d++) {
    const k = idx + d;
    if (k < 0 || k >= g.items.length) continue;
    const im = new Image(); im.src = IMG + n + '/' + g.items[k].png;
  }
}

function step(d) {
  const g = groups[gi];
  if (!g) return;
  let k = idx + d;
  if (k >= g.items.length) { k = 0; }
  if (k < 0) k = g.items.length - 1;
  show(k);
}

function toggle() { playing ? stop() : play(); }
function play() {
  if (!groups.length) return;
  playing = true; $('#play').textContent = '⏸ 暂停'; $('#play').classList.add('on');
  const ms = 1000 / Math.max(1, +$('#fps').value || 8);
  timer = setInterval(() => step(1), ms);
}
function stop() {
  playing = false; if (timer) clearInterval(timer); timer = null;
  $('#play').textContent = '▶ 播放'; $('#play').classList.remove('on');
}
$('#play').addEventListener('click', toggle);
document.querySelectorAll('[data-zoom]').forEach(b => b.addEventListener('click', () => {
  zoom = b.dataset.zoom === 'fit' ? 0 : +b.dataset.zoom; show(idx);
}));
document.querySelectorAll('[data-bg]').forEach(b => b.addEventListener('click', () => {
  bg = b.dataset.bg; $('#stage').className = bg;
}));
$('#prevnpc').addEventListener('click', () => { if (cur > 0) select(cur - 1); });
$('#nextnpc').addEventListener('click', () => { if (cur < list.length - 1) select(cur + 1); });
document.addEventListener('keydown', ev => {
  if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT') return;
  if (ev.key === ' ') { ev.preventDefault(); toggle(); }
  else if (ev.key === 'ArrowRight') { stop(); step(1); }
  else if (ev.key === 'ArrowLeft') { stop(); step(-1); }
  else if (ev.key === 'ArrowDown') { ev.preventDefault(); if (cur < list.length - 1) select(cur + 1); }
  else if (ev.key === 'ArrowUp') { ev.preventDefault(); if (cur > 0) select(cur - 1); }
  else if (viewMode === 'grid' && ev.key === 'PageDown') { ev.preventDefault(); gotoPage(page + 1); }
  else if (viewMode === 'grid' && ev.key === 'PageUp') { ev.preventDefault(); gotoPage(page - 1); }
  else if (viewMode === 'grid' && ev.key === 'Home') { ev.preventDefault(); gotoPage(0); }
  else if (viewMode === 'grid' && ev.key === 'End') { ev.preventDefault(); gotoPage(nPages() - 1); }
});
