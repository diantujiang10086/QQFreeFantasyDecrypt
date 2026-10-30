"""Build out/eff/index.html: gallery + per-effect layer inspector.

    python mkeff.py

Each card shows the static preview rendered by effrender.py; clicking selects the
effect and lists its layers (sprite, rate, blend, offset) and keyframe track.
"""
import json
import os
import re

from PIL import Image

import eff

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
PREV = os.path.join(OUT, 'eff')


def norm(name):
    m = re.fullmatch(r'(magic)(\d+)', name or '')
    return '%s%04d' % (m.group(1), int(m.group(2))) if m else name


def main():
    have = set(os.path.splitext(f)[0] for f in os.listdir(eff.MAGIC))
    items = []
    for name in sorted(os.listdir(eff.EFF)):
        if not name.lower().endswith(('.eff', '.eff_')):
            continue
        stem = os.path.splitext(name)[0]
        tree = eff.load(os.path.join(eff.EFF, name))
        if tree is None:
            continue
        ls = eff.layers(tree)
        png = os.path.join(PREV, stem + '.png')
        w = h = 0
        if os.path.exists(png):
            im = Image.open(png)
            w, h = im.width, im.height
        layers = []
        miss = 0
        for head, sprite, kfs in ls:
            rate = head[1][2] if len(head) > 1 and len(head[1]) > 2 else ''
            mode = head[1][3] if len(head) > 1 and len(head[1]) > 3 else ''
            ok = norm(sprite) in have
            miss += 0 if ok else 1
            layers.append({
                'id': head[0],
                's': sprite,
                'have': ok,
                'rate': rate,
                'mode': mode,
                'blend': head[2][0] if len(head) > 2 and head[2] else '',
                'flag': head[3][0] if len(head) > 3 and head[3] else '',
                'r4': head[4] if len(head) > 4 else '',
                'off': head[5] if len(head) > 5 else '',
                'keys': [[k[0]] + [k[1]] for k in kfs if isinstance(k, list) and len(k) >= 2],
            })
        items.append({'n': stem + os.path.splitext(name)[1], 'st': stem,
                      'kind': tree[0], 'w': w, 'h': h, 'miss': miss,
                      'size': os.path.getsize(os.path.join(eff.EFF, name)),
                      'layers': layers})
    os.makedirs(PREV, exist_ok=True)
    with open(os.path.join(OUT, 'eff', 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump({'items': items}, fh, ensure_ascii=False)
    html = HTML.replace('/*DATA*/null', json.dumps({'items': items}, ensure_ascii=False))
    path = os.path.join(OUT, 'eff', 'index.html')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('wrote', path, len(items), 'effects')


HTML = r"""<!doctype html>
<meta charset="utf-8">
<title>效果文件 .eff 浏览器</title>
<style>
 :root{--bg:#15171c;--fg:#d8dae0;--dim:#8b90a0;--line:#2a2e37;--acc:#6ea8fe}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.5 system-ui,"Segoe UI",sans-serif}
 header{padding:10px 14px;border-bottom:1px solid var(--line);position:sticky;top:0;background:#15171cee;z-index:5}
 h1{font-size:15px;margin:0 0 6px}
 input,select{background:#1b1e25;color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 8px;font:inherit}
 .sub{color:var(--dim);font-size:12px;margin-top:4px}
 main{display:grid;grid-template-columns:1fr 380px;gap:0;align-items:start}
 #grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(128px,1fr));gap:8px;padding:12px}
 .c{border:1px solid var(--line);border-radius:8px;background:#1b1e25;overflow:hidden;cursor:pointer}
 .c.cur{border-color:var(--acc)}
 .c .box{height:110px;display:flex;align-items:center;justify-content:center;background:
   linear-gradient(45deg,#23272f 25%,transparent 25%,transparent 75%,#23272f 75%),
   linear-gradient(45deg,#23272f 25%,#1b1e25 25%,#1b1e25 75%,#23272f 75%);
   background-size:16px 16px;background-position:0 0,8px 8px}
 .c img{image-rendering:pixelated;max-width:100%;max-height:100%}
 .c .nm{padding:3px 6px;font-size:11px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 aside{border-left:1px solid var(--line);padding:12px;position:sticky;top:64px;max-height:calc(100vh - 64px);overflow:auto}
 h2{font-size:13px;margin:0 0 6px}
 table{border-collapse:collapse;width:100%;font-size:11px;font-family:ui-monospace,Consolas,monospace}
 td,th{border-bottom:1px solid var(--line);padding:2px 4px;text-align:left;vertical-align:top}
 th{color:var(--dim);font-weight:400}
 .k{color:#ffd479}
 code{color:#cfe0ff}
</style>
<header>
 <h1>.eff 效果文件（1596 个）</h1>
 <input id="q" placeholder="搜索名字（回车）" size="28">
 <select id="kind"><option value="">全部类型</option></select>
 <label style="color:#8b90a0"><input type="checkbox" id="onlymiss"> 只看有缺失精灵的</label>
 <div class="sub">缩略图 = <code>effrender.py</code> 按每层首个关键帧（位置/缩放/旋转/颜色/透明度）合成的静态预览。</div>
</header>
<main>
 <div id="grid"></div>
 <aside id="side"><h2>选一个效果</h2><div style="color:#8b90a0">左侧点卡片查看层次与关键帧。</div></aside>
</main>
<script>
const DATA = /*DATA*/null;
const grid = document.getElementById('grid');
const side = document.getElementById('side');
const q = document.getElementById('q'), ksel = document.getElementById('kind'), onlymiss = document.getElementById('onlymiss');
const kinds = [...new Set(DATA.items.map(e => e.kind))].sort((a,b)=>a-b);
for (const k of kinds) { const o = document.createElement('option'); o.value = k; o.textContent = '类型 ' + k; ksel.appendChild(o); }
let list = DATA.items.slice(), cur = null;
function missing(e){ return e.miss > 0; }
function apply(){
  const t = q.value.trim().toLowerCase();
  list = DATA.items.filter(e => (!t || e.n.toLowerCase().includes(t)) &&
                                (ksel.value === '' || String(e.kind) === ksel.value) &&
                                (!onlymiss.checked || missing(e)));
  render();
}
function render(){
  grid.innerHTML = '';
  for (const e of list){
    const c = document.createElement('div'); c.className = 'c' + (cur === e ? ' cur' : '');
    const box = document.createElement('div'); box.className = 'box';
    const im = document.createElement('img'); im.loading = 'lazy'; im.src = '../eff/' + e.st + '.png';
    box.appendChild(im); c.appendChild(box);
    const nm = document.createElement('div'); nm.className = 'nm';
    nm.textContent = e.n + ' · ' + e.layers.length + '层';
    c.appendChild(nm);
    c.onclick = () => select(e);
    grid.appendChild(c);
  }
  document.querySelector('h1').textContent = '.eff 效果文件（' + list.length + ' / ' + DATA.items.length + '）';
}
function fmt(v){ return JSON.stringify(v); }
function select(e){
  cur = e; render();
  side.innerHTML = '';
  const h = document.createElement('h2'); h.textContent = e.n; side.appendChild(h);
  const meta = document.createElement('div');
  meta.style.cssText = 'color:#8b90a0;font-size:12px;margin-bottom:8px';
  meta.textContent = '类型 ' + e.kind + ' · ' + e.size + ' B · ' + e.w + '×' + e.h + ' · ' + e.layers.length + ' 层';
  side.appendChild(meta);
  const big = document.createElement('img');
  big.src = '../eff/' + e.st + '.png';
  big.style.cssText = 'image-rendering:pixelated;max-width:100%;background:#23272f;border:1px solid #2a2e37;border-radius:6px;margin-bottom:10px';
  side.appendChild(big);
  const tb = document.createElement('table');
  tb.innerHTML = '<tr><th>#</th><th>精灵</th><th>速率</th><th>混合</th><th>偏移</th><th>关键帧</th></tr>';
  e.layers.forEach((L, i) => {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td>' + (i+1) + '</td>' +
      '<td>' + L.s + '</td>' +
      '<td>' + L.rate + (L.mode !== '' ? ' / ' + L.mode : '') + '</td>' +
      '<td>' + L.blend + (L.flag !== '' ? ',' + L.flag : '') + '</td>' +
      '<td>' + fmt(L.off) + '</td>' +
      '<td>' + L.keys.length + '</td>';
    tb.appendChild(tr);
    const kr = document.createElement('tr');
    const td = document.createElement('td'); td.colSpan = 6;
    td.style.cssText = 'color:#a8adba;font-size:10px;padding-bottom:6px';
    td.textContent = L.keys.map(k => k[0] + 'ms ' + fmt(k[1])).join('  |  ');
    kr.appendChild(td); tb.appendChild(kr);
  });
  side.appendChild(tb);
}
q.addEventListener('keydown', ev => { if (ev.key === 'Enter') { apply(); } });
q.addEventListener('input', apply);
ksel.addEventListener('change', apply);
apply();
</script>
"""


if __name__ == '__main__':
    main()
