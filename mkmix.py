"""Build a small gallery page for out/mix/*.png  ->  out/mix/index.html

The viewer server (port 8791) serves out/ as its static root, so the gallery is
reachable at http://127.0.0.1:8791/mix/index.html
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
DST = os.path.join(OUT, 'mix')

HTML = """<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>npc body + head 合成</title>
<style>
  :root { --bg:#1b1c20; --fg:#d6dae3; --dim:#8b93a3; --acc:#6ea8fe; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:13px/1.5 "Segoe UI",system-ui,sans-serif; }
  header { position:sticky; top:0; z-index:5; background:#22242a;
           border-bottom:1px solid #33363d; padding:10px 14px;
           display:flex; gap:14px; align-items:center; flex-wrap:wrap; }
  h1 { font-size:14px; margin:0; font-weight:600; }
  input[type=search] { background:#17181c; color:var(--fg); border:1px solid #3a3d45;
                       border-radius:6px; padding:5px 8px; width:220px; }
  button { background:#2b2e35; color:var(--fg); border:1px solid #3a3d45;
           border-radius:6px; padding:5px 9px; cursor:pointer; }
  button:hover { border-color:var(--acc); }
  .chk { display:inline-flex; gap:5px; align-items:center; color:var(--dim); cursor:pointer; }
  #grid { display:grid; gap:14px; padding:14px;
          grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); }
  figure { margin:0; background:#23252b; border:1px solid #33363d; border-radius:8px;
           padding:8px; display:flex; flex-direction:column; gap:6px; align-items:center; }
  figure img { image-rendering:pixelated; max-width:100%; max-height:220px;
               background:
                 conic-gradient(#3a3d45 0 25%, #2c2f35 0 50%, #3a3d45 0 75%, #2c2f35 0)
                 0 0/16px 16px; border-radius:4px; }
  figcaption { font-size:11px; color:var(--dim); text-align:center; word-break:break-all; }
  #tip { color:var(--dim); }
  #count { color:var(--dim); font-variant-numeric:tabular-nums; }
  #zoom { position:fixed; inset:0; background:#0e0f12ee; display:none;
          align-items:center; justify-content:center; z-index:50; cursor:zoom-out; }
  #zoom img { image-rendering:pixelated; max-width:92vw; max-height:92vh;
              background:
                conic-gradient(#3a3d45 0 25%, #2c2f35 0 50%, #3a3d45 0 75%, #2c2f35 0)
                0 0/24px 24px; }
</style></head><body>
<header>
  <h1>身体 + 头 合成</h1>
  <span id="count"></span>
  <input type="search" id="q" placeholder="按名字过滤，例如 head2151">
  <label class="chk"><input type="checkbox" id="nat"> 原始尺寸（不缩放）</label>
  <button id="big">放大图</button>
  <span id="tip">点头像看大图，Esc 关闭</span>
</header>
<div id="grid"></div>
<div id="zoom"><img id="zimg" alt=""></div>
<script>
const ITEMS = __ITEMS__;
let zoomed = 4;
const grid = document.getElementById('grid');
const q = document.getElementById('q');
const nat = document.getElementById('nat');
const count = document.getElementById('count');
const zoom = document.getElementById('zoom');
const zimg = document.getElementById('zimg');

function show(list) {
  grid.innerHTML = '';
  for (const it of list) {
    const f = document.createElement('figure');
    const im = document.createElement('img');
    im.loading = 'lazy';
    im.src = it.n;
    im.alt = it.n;
    im.title = it.n + '  ' + it.w + 'x' + it.h;
    im.addEventListener('click', () => {
      zimg.src = it.n;
      zimg.style.imageRendering = 'pixelated';
      zoom.style.display = 'flex';
      zoom.dataset.size = it.w + 'x' + it.h;
      applyZoom();
    });
    const cap = document.createElement('figcaption');
    cap.textContent = it.n.replace(/\.png$/, '') + '  ' + it.w + 'x' + it.h;
    f.appendChild(im);
    f.appendChild(cap);
    grid.appendChild(f);
  }
  count.textContent = list.length + ' / ' + ITEMS.length + ' 张';
}

function applyZoom() {
  const s = zoom.dataset.size.split('x');
  zimg.style.width = (s[0] * zoomed) + 'px';
  zimg.style.maxWidth = 'none';
  zimg.style.maxHeight = 'none';
}

function filtered() {
  const t = q.value.trim().toLowerCase();
  return t ? ITEMS.filter(i => i.n.toLowerCase().includes(t)) : ITEMS;
}

q.addEventListener('input', () => show(filtered()));
nat.addEventListener('change', () => {
  grid.querySelectorAll('img').forEach(im => {
    im.style.maxHeight = nat.checked ? 'none' : '220px';
    im.style.maxWidth = nat.checked ? 'none' : '100%';
  });
});
document.getElementById('big').addEventListener('click', () => {
  zoomed = zoomed === 4 ? 8 : 4;
});
zoom.addEventListener('click', () => { zoom.style.display = 'none'; });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') zoom.style.display = 'none';
  if (zoom.style.display === 'flex') {
    if (e.key === '+' || e.key === '=') { zoomed *= 2; applyZoom(); }
    if (e.key === '-') { zoomed = Math.max(1, zoomed / 2); applyZoom(); }
  }
});
show(ITEMS);
</script>
</body></html>
"""


def main():
    items = []
    if not os.path.isdir(DST):
        print('no', DST)
        return
    for f in sorted(os.listdir(DST)):
        if not f.lower().endswith('.png'):
            continue
        from PIL import Image
        with Image.open(os.path.join(DST, f)) as im:
            w, h = im.size
        items.append({'n': f, 'w': w, 'h': h})
    page = HTML.replace('__ITEMS__', json.dumps(items, ensure_ascii=False))
    with open(os.path.join(DST, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(page)
    print('gallery %s  %d images  %d bytes'
          % (os.path.join(DST, 'index.html'), len(items), len(page.encode('utf-8'))))


if __name__ == '__main__':
    main()
