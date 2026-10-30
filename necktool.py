"""Neck editor: click on a body sprite to place the head's pivot (the "neck" point).

Serves a small local page on 127.0.0.1:8792:
  * pick a body (.gsn) and a head (.gsn), switch frame / direction, zoom
  * click on the body to set the neck point, arrow keys / typed numbers fine-tune
  * the head is drawn with its own pivot on that point, so what you see is the rule
  * "save" persists {stem: [x, y]} in canvas coordinates to out/neck.json

  python necktool.py --port 8792
  python necktool.py --show npc1000101        # print the stored neck point
"""
import io
import json
import os
import re
import struct
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg  # noqa: E402
from PIL import Image  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
NPC = os.path.join(SRC, 'npc')
HEADS = os.path.join(SRC, 'head')
NECKS = os.path.join(HERE, 'out', 'neck.json')
LOCK = threading.Lock()

_meta_cache = {}


def load_necks():
    try:
        with open(NECKS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_necks(d):
    os.makedirs(os.path.dirname(NECKS), exist_ok=True)
    with open(NECKS, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1, ensure_ascii=False, sort_keys=True)


def w32(d, off, n):
    return [struct.unpack_from('<i', d, off + 4 * j)[0] for j in range(n)]


def path_of(stem):
    for d0 in (NPC, HEADS):
        p = os.path.join(d0, stem + '.gsn')
        if os.path.exists(p):
            return p
    raise FileNotFoundError(stem)


def meta(stem):
    if stem in _meta_cache:
        return _meta_cache[stem]
    p = path_of(stem)
    d = open(p, 'rb').read()
    h = dimg.head(d)
    pre = w32(d, 24, 9)
    pref = w32(d, 60, 4)
    r = dimg.parse(d)
    out = {'stem': stem, 'size': len(d),
           'canvas': [pre[3], pre[4]], 'pivot': [pre[5], pre[6]],
           'sprite_at': [pref[1], pref[2]],
           'frames': [], 'head_family': not r['ok']}
    if r['ok']:
        for i, (p0, w, hh, px, bpp) in enumerate(r['frames']):
            out['frames'].append({'i': i, 'w': w, 'h': hh, 'px': px, 'bpp': bpp})
        out['ok'] = True
    else:
        out['ok'] = False
        try:
            import headtool
            recs, extra, k = headtool.segment(d)
            for i, (p0, w, hh, stride, flag) in enumerate(recs):
                out['frames'].append({'i': i, 'w': w, 'h': hh, 'px': p0 + 16, 'bpp': stride // w})
        except Exception as e:
            out['err'] = str(e)
    _meta_cache[stem] = out
    return out


def frame_png(stem, i=0, mask=None):
    """PNG of one frame. mask: 'alpha' -> white silhouette on transparent."""
    p = path_of(stem)
    d = open(p, 'rb').read()
    m = meta(stem)
    fr = m['frames'][i]
    img = dimg.to_image(d, fr['px'], fr['w'], fr['h'], fr['bpp'])
    if mask == 'alpha':
        a = img.split()[3].point(lambda v: 255 if v > 8 else 0)
        img = Image.merge('RGBA', (a, a, a, a))
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def bodies(limit=0):
    q = load_necks()
    out = []
    for nm in sorted(os.listdir(NPC)):
        if not nm.endswith('.gsn'):
            continue
        stem = nm[:-4]
        out.append({'stem': stem, 'neck': q.get(stem)})
        if limit and len(out) >= limit:
            break
    return out


def heads():
    return sorted(nm[:-4] for nm in os.listdir(HEADS) if nm.endswith('.gsn'))


def head_index(m, dirno):
    """Pair family (>=10 records) alternates colour/mask per direction."""
    n = len(m['frames'])
    d = max(1, min(9, dirno))
    k = 2 * (d - 1) if n >= 10 else (d - 1)
    return min(n - 1, k)


PAGE = r"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>脖子编辑器</title>
<style>
:root{--bg:#14161a;--panel:#1c2026;--line:#2c333c;--fg:#e6ebf2;--dim:#93a0b0;--accent:#4da3ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.5 "Segoe UI",system-ui,sans-serif;display:flex;height:100vh;overflow:hidden}
aside{width:280px;flex:0 0 280px;border-right:1px solid var(--line);display:flex;flex-direction:column;background:var(--panel)}
aside h1{font-size:13px;margin:0;padding:10px 12px;border-bottom:1px solid var(--line);color:var(--dim);font-weight:600}
#q{margin:8px 10px;padding:6px 8px;background:#12151a;border:1px solid var(--line);color:var(--fg);border-radius:4px}
#list{overflow:auto;flex:1}
#list div{padding:4px 12px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--dim)}
#list div:hover{background:#232a33;color:var(--fg)}
#list div.cur{background:#1b3a5c;color:#fff}
#list div.has b{color:#ffd479}
main{flex:1;display:flex;flex-direction:column;min-width:0}
#bar{display:flex;gap:8px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--line);flex-wrap:wrap}
#bar input,#bar select,#bar button{background:#12151a;color:var(--fg);border:1px solid var(--line);border-radius:4px;padding:4px 7px}
#bar button{cursor:pointer}
#bar button:hover{border-color:var(--accent)}
#stage{flex:1;overflow:auto;padding:16px;display:flex;align-items:flex-start;justify-content:flex-start}
#wrap{position:relative;image-rendering:pixelated}
#wrap img{position:absolute;left:0;top:0;image-rendering:pixelated}
#ck{position:absolute;inset:0}
#cross{position:absolute;width:0;height:0;pointer-events:none}
#cross:before,#cross:after{content:"";position:absolute;background:#ff3b7b}
#cross:before{left:-12px;top:-1px;width:24px;height:2px}
#cross:after{top:-12px;left:-1px;height:24px;width:2px}
#hud{position:fixed;right:14px;bottom:14px;background:#0d1014cc;border:1px solid var(--line);border-radius:6px;padding:8px 10px;font-family:Consolas,monospace;font-size:12px;line-height:1.6;pointer-events:none}
#hud b{color:var(--accent)}
</style></head><body>
<aside>
  <h1>身体 / NPC</h1>
  <input id="q" placeholder="搜索 npc1000…" autocomplete="off">
  <div id="list"></div>
</aside>
<main>
  <div id="bar">
    <span>头：</span><select id="head"></select>
    <span>方向</span><input id="hdir" type="number" value="1" min="1" max="9" style="width:52px">
    <span>身体帧</span><input id="bframe" type="number" value="0" min="0" style="width:56px">
    <span>缩放</span><input id="zoom" type="number" value="5" min="1" max="16" style="width:56px">
    <button id="showHead">头 显示/隐藏</button>
    <button id="clear">清除脖子</button>
    <button id="save">保存</button>
    <span id="msg" style="color:var(--dim)"></span>
  </div>
  <div id="stage"><div id="wrap">
    <canvas id="ck"></canvas>
    <img id="body" alt="">
    <img id="headimg" alt="">
    <div id="cross"></div>
  </div></div>
</main>
<div id="hud">empty</div>
<script>
const IMG = '/api/frame?stem=';
let state = {stem:null, bodyMeta:null, headMeta:null, neck:null, showHead:true, zoom:5};
const $ = s => document.querySelector(s);
const el = (t, c, txt) => { const e = document.createElement(t); if (c) e.className = c; if (txt != null) e.textContent = txt; return e; };

function checker(cv, w, h, s){
  const g = cv.getContext('2d'); cv.width = w; cv.height = h;
  for (let y = 0; y < h; y += s) for (let x = 0; x < w; x += s){
    g.fillStyle = ((x/s + y/s) % 2) ? '#3a4048' : '#4a515a';
    g.fillRect(x, y, s, s);
  }
}

function draw(){
  const z = state.zoom, bm = state.bodyMeta, hm = state.headMeta;
  if (!bm) return;
  const W = bm.canvas[0], H = bm.canvas[1];
  const wrap = $('#wrap');
  wrap.style.width = (W*z) + 'px'; wrap.style.height = (H*z) + 'px';
  const ck = $('#ck'); ck.style.width = (W*z)+'px'; ck.style.height = (H*z)+'px';
  checker(ck, W*z, H*z, 20);
  const b = $('#body');
  b.style.width = (bm.spriteW*z)+'px'; b.style.height = (bm.spriteH*z)+'px';
  b.style.left = (bm.sprite_at[0]*z)+'px'; b.style.top = (bm.sprite_at[1]*z)+'px';
  const hd = $('#headimg');
  if (state.neck && hm && state.showHead){
    const nx = bm.canvas[0], ny = bm.canvas[1];
    const hx = state.neck[0] - hm.pivot[0], hy = state.neck[1] - hm.pivot[1];
    hd.style.display = 'block';
    hd.style.width = (hm.spriteW*z)+'px'; hd.style.height = (hm.spriteH*z)+'px';
    hd.style.left = ((hx + hm.sprite_at[0])*z)+'px';
    hd.style.top  = ((hy + hm.sprite_at[1])*z)+'px';
  } else hd.style.display = 'none';
  const c = $('#cross');
  if (state.neck){
    c.style.display = 'block';
    c.style.left = (state.neck[0]*z)+'px'; c.style.top = (state.neck[1]*z)+'px';
  } else c.style.display = 'none';
  hud();
}

function hud(){
  const bm = state.bodyMeta;
  if (!bm){ $('#hud').textContent = 'empty'; return; }
  const n = state.neck;
  const lines = [];
  lines.push('body <b>' + bm.stem + '</b>  canvas ' + bm.canvas.join('x') + '  pivot ' + bm.pivot.join(','));
  lines.push('sprite at ' + bm.sprite_at.join(',') + '  size ' + bm.spriteW + 'x' + bm.spriteH + '  frame ' + $('#bframe').value);
  if (n){
    lines.push('neck(canvas) <b>' + n[0] + ',' + n[1] + '</b>');
    lines.push('neck(sprite) <b>' + (n[0]-bm.sprite_at[0]) + ',' + (n[1]-bm.sprite_at[1]) + '</b>');
    if (state.headMeta) lines.push('head pivot ' + state.headMeta.pivot.join(',') + '  → head canvas at ' + (n[0]-state.headMeta.pivot[0]) + ',' + (n[1]-state.headMeta.pivot[1]));
  } else lines.push('neck: 未设置（点图）');
  $('#hud').innerHTML = lines.join('<br>');
}

async function loadBody(stem){
  const r = await fetch('/api/meta?stem=' + encodeURIComponent(stem));
  if (!r.ok){ $('#msg').textContent = '读取失败'; return; }
  const m = await r.json();
  const fr = m.frames[0];
  m.spriteW = fr.w; m.spriteH = fr.h;
  state.bodyMeta = m; state.stem = stem;
  $('#body').src = IMG + encodeURIComponent(stem) + '&i=' + ($('#bframe').value||0) + '&t=' + Date.now();
  state.neck = m.neck ? [m.neck[0], m.neck[1]] : [m.pivot[0], m.pivot[1] - 40];
  draw();
}

async function loadHead(stem, dir){
  const r = await fetch('/api/head?stem=' + encodeURIComponent(stem) + '&dir=' + dir);
  if (!r.ok){ $('#msg').textContent = '头读取失败'; return; }
  const m = await r.json();
  state.headMeta = m;
  $('#headimg').src = '/api/headimg?stem=' + encodeURIComponent(stem) + '&dir=' + dir + '&t=' + Date.now();
  draw();
}

$('#wrap').addEventListener('click', ev => {
  const r = $('#wrap').getBoundingClientRect(), z = state.zoom;
  const x = Math.floor((ev.clientX - r.left) / z), y = Math.floor((ev.clientY - r.top) / z);
  state.neck = [x, y]; draw();
});

document.addEventListener('keydown', ev => {
  if (!state.neck) return;
  const k = ev.key, s = ev.shiftKey ? 5 : 1;
  let d = null;
  if (k === 'ArrowLeft') d = [-s, 0]; else if (k === 'ArrowRight') d = [s, 0];
  else if (k === 'ArrowUp') d = [0, -s]; else if (k === 'ArrowDown') d = [0, s];
  if (d){ ev.preventDefault(); state.neck = [state.neck[0]+d[0], state.neck[1]+d[1]]; draw(); }
});

$('#save').onclick = async () => {
  if (!state.stem || !state.neck) return;
  const r = await fetch('/api/neck', {method:'POST', headers:{'content-type':'application/json'},
    body: JSON.stringify({stem: state.stem, x: state.neck[0], y: state.neck[1]})});
  $('#msg').textContent = r.ok ? ('已保存 ' + state.stem + ' = ' + state.neck.join(',')) : '保存失败';
  const it = ALL.find(b => b.stem === state.stem);
  if (it) it.neck = [state.neck[0], state.neck[1]];
  renderList();
};
$('#clear').onclick = () => { state.neck = null; draw(); };
$('#showHead').onclick = () => { state.showHead = !state.showHead; draw(); };
$('#zoom').oninput = () => { state.zoom = Math.max(1, +$('#zoom').value || 5); draw(); };
$('#bframe').onchange = () => loadBody(state.stem);
$('#hdir').onchange = () => loadHead($('#head').value, +$('#hdir').value);
$('#head').onchange = () => loadHead($('#head').value, +$('#hdir').value);

let ALL = [];
async function refreshList(){
  const r = await fetch('/api/bodies');
  ALL = await r.json();
  renderList();
}
function renderList(){
  const q = ($('#q').value || '').trim().toLowerCase();
  const list = $('#list'); list.innerHTML = '';
  const items = ALL.filter(b => !q || b.stem.includes(q)).slice(0, 400);
  for (const b of items){
    const d = el('div', b.neck ? 'has' : '', b.stem + (b.neck ? '  ●' + b.neck.join(',') : ''));
    d.onclick = () => { [...list.children].forEach(c => c.classList.remove('cur')); d.classList.add('cur'); loadBody(b.stem); };
    list.appendChild(d);
  }
}

(async function init(){
  await refreshList();
  const r = await fetch('/api/heads'); const hs = await r.json();
  for (const h of hs){ const o = el('option', null, h); o.value = h; $('#head').appendChild(o); }
  $('#head').value = 'head0101';
  const first = $('#list').firstChild;
  if (first) first.click();
  await loadHead('head0101', 1);
})();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *a):
        pass

    def _send(self, code, body=b'', ctype='application/json; charset=utf-8', extra=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('content-type', ctype)
        self.send_header('content-length', str(len(body)))
        self.send_header('cache-control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path in ('/', '/index.html'):
                return self._send(200, PAGE, 'text/html; charset=utf-8')
            if u.path == '/api/bodies':
                return self._send(200, json.dumps(bodies()))
            if u.path == '/api/heads':
                return self._send(200, json.dumps(heads()))
            if u.path == '/api/meta':
                m = meta(q['stem'])
                m['neck'] = load_necks().get(q['stem'])
                return self._send(200, json.dumps(m))
            if u.path == '/api/frame':
                return self._send(200, frame_png(q['stem'], int(q.get('i', 0))), 'image/png')
            if u.path == '/api/headimg':
                d = open(path_of(q['stem']), 'rb').read()
                m = meta(q['stem'])
                k = head_index(m, int(q.get('dir', 1)))
                fr = m['frames'][k]
                img = dimg.to_image(d, fr['px'], fr['w'], fr['h'], fr['bpp'])
                buf = io.BytesIO()
                img.save(buf, 'PNG')
                return self._send(200, buf.getvalue(), 'image/png')
            if u.path == '/api/head':
                m = meta(q['stem'])
                k = head_index(m, int(q.get('dir', 1)))
                fr = m['frames'][k]
                return self._send(200, json.dumps({'stem': q['stem'], 'pivot': m['pivot'],
                                                   'sprite_at': m['sprite_at'], 'canvas': m['canvas'],
                                                   'spriteW': fr['w'], 'spriteH': fr['h'], 'idx': k}))
            return self._send(404, json.dumps({'err': 'not found'}))
        except FileNotFoundError as e:
            return self._send(404, json.dumps({'err': 'missing: %s' % e}))
        except Exception as e:
            return self._send(500, json.dumps({'err': repr(e)}))

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get('content-length') or 0)
        raw = self.rfile.read(n) if n else b'{}'
        if u.path == '/api/neck':
            try:
                j = json.loads(raw.decode('utf-8'))
            except Exception as e:
                return self._send(400, json.dumps({'err': repr(e)}))
            with LOCK:
                d = load_necks()
                d[j['stem']] = [int(j['x']), int(j['y'])]
                save_necks(d)
            return self._send(200, json.dumps({'ok': True, 'n': len(d)}))
        return self._send(404, json.dumps({'err': 'not found'}))


def main():
    a = sys.argv[1:]
    if '--show' in a:
        stem = a[a.index('--show') + 1]
        print(stem, load_necks().get(stem))
        return
    if '--set' in a:
        stem = a[a.index('--set') + 1]
        x, y = [int(v) for v in a[a.index('--set') + 2].split(',')]
        d = load_necks()
        d[stem] = [x, y]
        save_necks(d)
        print('set', stem, d[stem])
        return
    port = int(a[a.index('--port') + 1]) if '--port' in a else 8792
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print('neck editor on http://127.0.0.1:%d/' % port, flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
