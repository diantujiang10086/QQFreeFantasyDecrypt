"""Build out/sheets/index.html: one page listing every contact sheet we produced.

    python mksheets.py

Reads out/*_sheet*.png (head/backpack/cap/face/weaponl/weaponr) and writes a
simple gallery page served by viewer_server.py at /sheets/index.html.
"""
import glob
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

GROUPS = [
    ('avatar\\head', 'head_sheet.png', '148 个头部（成对族取彩色层，单图族取唯一帧）'),
    ('avatar\\backpack', 'backpack_sheet-*.png', '282 个背包，方向 1 第 0 帧'),
    ('avatar\\cap', 'cap_sheet-*.png', '627 个帽子，方向 1 第 0 帧'),
    ('avatar\\face', 'face_sheet-*.png', '318 个表情，方向 1 第 0 帧'),
    ('avatar\\weaponl', 'weaponl_sheet-*.png', '1,997 个左手武器，方向 1 第 0 帧'),
    ('avatar\\weaponr', 'weaponr_sheet-*.png', '9,631 个右手武器（抽样 1/16 → 602 个）'),
]


def main():
    groups = []
    for name, pat, note in GROUPS:
        files = sorted(glob.glob(os.path.join(OUT, pat)))
        entries = []
        for f in files:
            im = Image.open(f)
            entries.append({'src': os.path.basename(f), 'w': im.width, 'h': im.height})
        groups.append({'name': name, 'note': note, 'pages': entries})
    data = {'groups': groups}
    os.makedirs(os.path.join(OUT, 'sheets'), exist_ok=True)
    html = HTML.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))
    path = os.path.join(OUT, 'sheets', 'index.html')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('wrote', path, sum(len(g['pages']) for g in groups), 'pages')


HTML = r"""<!doctype html>
<meta charset="utf-8">
<title>avatar 子目录总览图</title>
<style>
 :root{--bg:#15171c;--fg:#d8dae0;--dim:#8b90a0;--line:#2a2e37;--acc:#6ea8fe}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.5 system-ui,"Segoe UI",sans-serif}
 header{padding:10px 14px;border-bottom:1px solid var(--line);position:sticky;top:0;background:#15171cee;backdrop-filter:blur(6px);z-index:5}
 h1{font-size:15px;margin:0 0 4px}
 .sub{color:var(--dim);font-size:12px}
 section{padding:12px 14px;border-bottom:1px solid var(--line)}
 h2{font-size:14px;margin:0 0 2px}
 .note{color:var(--dim);font-size:12px;margin-bottom:8px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
 a.card{display:block;text-decoration:none;color:var(--fg);border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#1b1e25}
 a.card:hover{border-color:var(--acc)}
 .im{height:220px;background:
   linear-gradient(45deg,#23272f 25%,transparent 25%,transparent 75%,#23272f 75%),
   linear-gradient(45deg,#23272f 25%,#1b1e25 25%,#1b1e25 75%,#23272f 75%);
   background-size:16px 16px;background-position:0 0,8px 8px;display:flex;align-items:center;justify-content:center}
 .im img{max-width:100%;max-height:100%;image-rendering:pixelated}
 .cap{padding:5px 8px;font-size:12px;color:var(--dim);border-top:1px solid var(--line)}
 code{color:#cfe0ff}
</style>
<header>
 <h1>avatar 子目录 · 总览图</h1>
 <div class="sub">每个格子 = 一个 .gsn 的首帧（方向 1），点开看原图。文件由 <code>avaexport.py --sheet</code> / <code>bpsheet.py</code> / <code>headsheet.py</code> 生成。</div>
</header>
<main id="root"></main>
<script>
const DATA = /*DATA*/null;
const root = document.getElementById('root');
for (const g of DATA.groups) {
  const s = document.createElement('section');
  const h = document.createElement('h2'); h.textContent = g.name + `（${g.pages.length} 页）`; s.appendChild(h);
  const n = document.createElement('div'); n.className = 'note'; n.textContent = g.note; s.appendChild(n);
  const gr = document.createElement('div'); gr.className = 'grid';
  for (const p of g.pages) {
    const a = document.createElement('a'); a.className = 'card'; a.href = '../' + p.src; a.target = '_blank';
    const im = document.createElement('div'); im.className = 'im';
    const img = document.createElement('img'); img.loading = 'lazy'; img.src = '../' + p.src; img.alt = p.src;
    im.appendChild(img); a.appendChild(im);
    const c = document.createElement('div'); c.className = 'cap';
    c.textContent = p.src + ` · ${p.w}×${p.h}`; a.appendChild(c);
    gr.appendChild(a);
  }
  s.appendChild(gr); root.appendChild(s);
}
</script>
"""


if __name__ == '__main__':
    main()
