"""Build out/gsa/index.html — browser for every `res\\*.gsa` decoded frame.

    python mkgsa.py

Scans `out/gsa/` (produced by `gsa.py png out\\gsa`) plus `out/gsa.csv`, and writes a
single self-contained page: left = sub-directory filter + file list, right = the
frames of the selected file, plus header facts (size, frames, tiles, pixel format).
Served by `viewer_server.py` at /gsa/index.html.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
PNGS = os.path.join(OUT, 'gsa')
CSV = os.path.join(OUT, 'gsa.csv')


def load():
    rows = {}
    if os.path.exists(CSV):
        for r in csv.DictReader(open(CSV, encoding='utf-8')):
            rows[r['file'].replace('\\', '/')] = r
    items = []
    for root, dirs, files in os.walk(PNGS):
        pngs = sorted(f for f in files if f.lower().endswith('.png'))
        if not pngs:
            continue
        rel = os.path.relpath(root, PNGS).replace(os.sep, '/')
        disp = rel.replace('__', '/')
        meta = rows.get(disp + '.gsa', {})
        sub = disp.split('/')[0]
        items.append({
            'n': disp,
            'd': rel,
            's': sub,
            'sub': disp.rsplit('/', 1)[0] if '/' in disp else sub,
            'w': int(meta.get('w') or 0),
            'h': int(meta.get('h') or 0),
            'f': len(pngs),
            'b': int(meta.get('bpp') or 0),
            't': int(meta.get('tiles') or 0),
            'z': int(meta.get('size') or 0),
            'p': pngs,
        })
    items.sort(key=lambda e: e['n'])
    return items


def main():
    items = load()
    subs = {}
    for e in items:
        subs[e['s']] = subs.get(e['s'], 0) + 1
    data = {'items': items, 'subs': subs}
    os.makedirs(os.path.join(OUT, 'gsa'), exist_ok=True)
    html = HTML.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    path = os.path.join(OUT, 'gsa', 'index.html')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('wrote', path, len(items), 'files', sum(len(e['p']) for e in items), 'frames')


HTML = r"""<!doctype html>
<html lang="zh"><meta charset="utf-8">
<title>res\  ——  .gsa 浏览</title>
<style>
 :root{--bg:#15171c;--fg:#d8dae0;--dim:#8b90a0;--line:#2a2e37;--acc:#6ea8fe}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.5 system-ui,"Segoe UI",sans-serif;display:flex;height:100vh;overflow:hidden}
 aside{width:330px;border-right:1px solid var(--line);display:flex;flex-direction:column}
 .top{padding:8px 10px;border-bottom:1px solid var(--line)}
 input,select{width:100%;background:#1b1e25;border:1px solid var(--line);color:var(--fg);padding:5px 7px;border-radius:6px;font:inherit}
 .row{display:flex;gap:6px;margin-top:6px}
 #list{overflow:auto;flex:1}
 .it{padding:5px 10px;cursor:pointer;border-bottom:1px solid #1e222a;display:flex;justify-content:space-between;gap:6px}
 .it:hover{background:#1b1e25}
 .it.cur{background:#233046;color:#fff}
 .it small{color:var(--dim)}
 main{flex:1;display:flex;flex-direction:column;overflow:hidden}
 #bar{padding:6px 10px;border-bottom:1px solid var(--line);color:var(--dim);font-size:12px;white-space:nowrap;overflow:auto}
 #pane{flex:1;overflow:auto;padding:12px;display:flex;flex-wrap:wrap;gap:12px;align-content:flex-start}
 .cell{background:
   linear-gradient(45deg,#23272f 25%,transparent 25%,transparent 75%,#23272f 75%),
   linear-gradient(45deg,#23272f 25%,#1b1e25 25%,#1b1e25 75%,#23272f 75%);
   background-size:16px 16px;background-position:0 0,8px 8px;border:1px solid var(--line);border-radius:6px;padding:6px;display:flex;flex-direction:column;align-items:center;gap:4px}
 .cell img{image-rendering:pixelated;display:block;max-width:512px;max-height:512px}
 .cell span{font-size:11px;color:var(--dim)}
 .hint{color:var(--dim);padding:10px}
</style>
<aside>
 <div class="top">
  <input id="q" placeholder="搜索文件名（支持子目录，如 uires/titleui）">
  <div class="row"><select id="sub"><option value="">全部子目录</option></select></div>
 </div>
 <div id="list"></div>
</aside>
<main>
 <div id="bar">选择一个文件…</div>
 <div id="pane"><div class="hint">左侧点文件名 → 这里显示它的全部帧。</div></div>
</main>
<script>
const DATA = /*DATA*/null;
const IMG = '/gsa/';
const $ = s => document.querySelector(s);
const items = DATA.items;
let list = items.slice(), cur = -1;

const sub = $('#sub');
for (const k of Object.keys(DATA.subs).sort()) {
  const o = document.createElement('option');
  o.value = k; o.textContent = `${k}（${DATA.subs[k]}）`; sub.appendChild(o);
}

function render(){
  const box = $('#list'); box.textContent = '';
  const frag = document.createDocumentFragment();
  list.forEach((e, i) => {
    const d = document.createElement('div');
    d.className = 'it'; d.dataset.i = e.n;
    const a = document.createElement('span'); a.textContent = e.n.split('/').pop();
    const b = document.createElement('small'); b.textContent = `${e.w}×${e.h} · ${e.f}帧`;
    d.appendChild(a); d.appendChild(b);
    d.onclick = () => select(e.n);
    frag.appendChild(d);
  });
  box.appendChild(frag);
  $('#bar').textContent = `${list.length} / ${items.length} 个文件`;
}

function select(name){
  cur = items.findIndex(e => e.n === name);
  document.querySelectorAll('.it').forEach(el => el.classList.toggle('cur', el.dataset.i === name));
  const e = items[cur];
  if (!e) return;
  $('#bar').textContent = `${e.n}   ${e.w}×${e.h}  ${e.f} 帧  ${e.t} 块  ${e.b === 4 ? '4 字节/像素' : '2 字节/像素'}  ${(e.z/1024).toFixed(1)} KB`;
  const pane = $('#pane'); pane.textContent = '';
  e.p.forEach(p => {
    const c = document.createElement('div'); c.className = 'cell';
    const im = document.createElement('img'); im.loading = 'lazy'; im.src = IMG + e.d + '/' + p;
    const s = document.createElement('span'); s.textContent = p;
    c.appendChild(im); c.appendChild(s); pane.appendChild(c);
  });
}

function apply(){
  const q = $('#q').value.trim().toLowerCase();
  const s = sub.value;
  list = items.filter(e => (!s || e.s === s) && (!q || e.n.toLowerCase().includes(q)));
  render();
}
$('#q').oninput = apply;
sub.onchange = apply;
render();
</script>
"""


if __name__ == '__main__':
    main()
