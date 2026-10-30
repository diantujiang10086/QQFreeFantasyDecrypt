"""Build out/tile/index.html: a browser page for the decoded official\\tile containers."""
import glob
import json
import os

import tile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tile')
PAGE = os.path.join(OUT, 'index.html')

HTML = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>tile 容器浏览器</title>
<style>
:root{--bg:#16181d;--fg:#e6e8ee;--dim:#98a0b3;--acc:#5aa9e6;--card:#1e222b}
*{box-sizing:border-box}
body{margin:0;font:13px/1.5 "Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{display:flex;gap:12px;align-items:center;padding:10px 14px;background:#12141a;border-bottom:1px solid #262b36;position:sticky;top:0;z-index:5}
h1{font-size:15px;margin:0;font-weight:600}
input,select{background:#0f1116;color:var(--fg);border:1px solid #2b3140;border-radius:5px;padding:5px 8px;font:inherit}
input{width:220px}
#meta{color:var(--dim);margin-left:auto;font-variant-numeric:tabular-nums}
main{display:grid;grid-template-columns:340px 1fr;height:calc(100vh - 47px)}
#list{overflow:auto;border-right:1px solid #262b36;padding:6px}
.row{display:flex;gap:8px;align-items:center;padding:5px 7px;border-radius:6px;cursor:pointer}
.row:hover{background:#20252f}
.row.cur{background:#26303f;outline:1px solid var(--acc)}
.row img{width:34px;height:34px;image-rendering:pixelated;background:
  repeating-conic-gradient(#22262e 0 25%,#191c22 0 50%) 0 0/10px 10px}
.row .nm{overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.row .n{color:var(--dim);font-size:11px}
#pane{overflow:auto;padding:12px}
#pane h2{font-size:14px;margin:0 0 8px}
#grid{display:flex;flex-wrap:wrap;gap:10px}
.cell{background:var(--card);border:1px solid #262b36;border-radius:6px;padding:6px;text-align:center}
.cell img{display:block;image-rendering:pixelated;background:
  repeating-conic-gradient(#22262e 0 25%,#191c22 0 50%) 0 0/16px 16px;max-width:200px;max-height:200px}
.cell span{display:block;color:var(--dim);font-size:11px;margin-top:4px}
</style></head><body>
<header>
  <h1>official\\tile</h1>
  <input id="q" placeholder="搜索地形 / 图素名">
  <select id="kind"><option value="">全部</option><option value="til">.til 地形过渡</option><option value="img">tileimg 图素</option></select>
  <span id="meta"></span>
</header>
<main><div id="list"></div><div id="pane"><h2>点左侧选一个容器</h2><div id="grid"></div></div></main>
<script>
const M = __MANIFEST__;
const list = M.items;
let cur = -1;
const $ = s => document.querySelector(s);
const el = (t,c,h) => { const e=document.createElement(t); if(c) e.className=c; if(h!==undefined) e.textContent=h; return e; };

function thumb(it){ return it.dir + '/' + (it.kind==='til' ? 'e00.png' : 'e0000.png'); }

function render(){
  const q = $('#q').value.trim().toLowerCase();
  const k = $('#kind').value;
  const box = $('#list'); box.innerHTML='';
  let n=0;
  for (let i=0;i<list.length;i++){
    const it=list[i];
    if (k && it.kind!==k) continue;
    if (q && !(it.name.toLowerCase().includes(q)||String(it.id).includes(q))) continue;
    n++;
    const row=el('div','row'+(i===cur?' cur':''));
    const im=el('img'); im.src=thumb(it); im.loading='lazy';
    const t=el('div'); t.appendChild(el('div','nm',it.name));
    t.appendChild(el('div','n',(it.kind==='til'?'.til #'+it.id:'tileimg')+' · '+it.n+' 帧'));
    row.appendChild(im); row.appendChild(t);
    row.onclick=()=>{ cur=i; render(); show(it); };
    box.appendChild(row);
  }
  $('#meta').textContent = n + ' / ' + list.length + ' 个容器 · ' + M.entries + ' 帧';
}

function show(it){
  const g=$('#grid'); g.innerHTML='';
  const h=document.createElement('h2');
  h.textContent = it.name + ' — ' + (it.kind==='til'?'地形过渡块 128×128':'图素块 64×64') + '，' + it.n + ' 帧';
  g.parentNode.insertBefore(h, g.nextSibling ? g : null);
  for (let i=0;i<it.n;i++){
    const c=el('div','cell');
    const im=el('img'); im.loading='lazy';
    im.src=it.dir+'/'+(it.kind==='til'?'e'+String(i).padStart(2,'0'):'e'+String(i).padStart(4,'0'))+'.png';
    c.appendChild(im); c.appendChild(el('span','#'+i));
    g.appendChild(c);
  }
}
$('#q').oninput=render; $('#kind').onchange=render;
render();
</script></body></html>
"""


def main():
    names = tile.ini_tile_names()
    items = []
    for p in tile.til_files():
        stem = os.path.basename(p)[:-4]
        d = open(p, 'rb').read(16)
        n = int.from_bytes(d[12:16], 'little')
        tid = names.get(stem, 0)
        dname = 'til_%04d' % tid if tid else 'til_x_' + stem.encode('unicode_escape').decode('ascii').replace('\\', '')
        items.append({'kind': 'til', 'name': stem, 'id': tid, 'n': n, 'dir': dname})
    for p in tile.img_files():
        stem = os.path.basename(p)[:-4]
        d = open(p, 'rb').read(32)
        n = int.from_bytes(d[28:32], 'little')
        items.append({'kind': 'img', 'name': stem, 'id': 0, 'n': n, 'dir': 'img_' + stem})
    items.sort(key=lambda x: (x['kind'] != 'til', x['id'] or 9999, x['name']))
    entries = sum(i['n'] for i in items)
    man = {'items': items, 'entries': entries}
    html = HTML.replace('__MANIFEST__', json.dumps(man, ensure_ascii=False))
    with open(PAGE, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('items', len(items), 'entries', entries)
    print('->', PAGE, os.path.getsize(PAGE), 'bytes')


if __name__ == '__main__':
    main()
