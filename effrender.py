"""Render a static preview of an .eff effect (all layers at a chosen time).

    python effrender.py --out out\\eff [--step 4] [--time 0] [--sheet out\\eff_sheet.png]

Each layer is `(id, (name, 0, rate[, mode]), (blend,), (0,)[, mode, (dx,dy)))` and
its keyframe track gives `((x,y,z), (sx,sy), rot_deg, (r,g,b), alpha)` at times in ms.
We take the sprite frame that corresponds to `--time`, apply scale/rotation/tint and
alpha, and composite the layers in file order around the actor origin.
"""
import os
import sys

from PIL import Image, ImageChops

import dimg
import eff
import gso

MAGIC = eff.MAGIC
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = {}


def sprite(name, frame=0):
    """(PIL image, canvas_w, canvas_h, pivot_x, pivot_y) of one sprite frame."""
    key = (name, frame)
    if key in CACHE:
        return CACHE[key]
    stem = name
    if stem.startswith('magic'):
        digits = ''.join(ch for ch in stem if ch.isdigit())
        stem = 'magic%04d' % int(digits or 0)
    path = os.path.join(MAGIC, stem + '.gso')
    if not os.path.exists(path):
        CACHE[key] = None
        return None
    with open(path, 'rb') as fh:
        d = fh.read()
    r = dimg.parse(d, brute=True)
    if not r['ok']:
        CACHE[key] = None
        return None
    h = dimg.head(d)
    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    canvas = (pw[3], pw[4])
    pivot = (pw[5], pw[6])
    frames = [f for f in r['frames'] if f[3] is not None]
    if not frames:
        CACHE[key] = None
        return None
    f = frames[min(frame, len(frames) - 1)]
    im = dimg.to_image(d, f[3], f[1], f[2], f[4])
    out = (im, canvas[0], canvas[1], pivot[0], pivot[1])
    CACHE[key] = out
    return out


def lerp_keyframes(kfs, t):
    """Interpolate the keyframe track at time t (linear, clamped)."""
    if not kfs:
        return None
    pts = [(k[0], k[1]) for k in kfs if isinstance(k, list) and len(k) >= 2]
    if not pts:
        return None
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            a = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            out = []
            for j in range(min(len(v0), len(v1))):
                x, y = v0[j], v1[j]
                if isinstance(x, list) and isinstance(y, list):
                    out.append([round(px + (py - px) * a, 4) for px, py in zip(x, y)])
                else:
                    out.append(round(x + (y - x) * a, 4))
            return out
    return pts[-1][1]


def render(path, t=0, max_layers=24, pct=None):
    tree = eff.load(path)
    if tree is None:
        return None, 0
    layers = eff.layers(tree)
    if pct is not None:
        times = [k[0] for _, _, kfs in layers for k in kfs
                 if isinstance(k, list) and k and isinstance(k[0], (int, float))]
        t = (max(times) if times else 0) * pct
    items = []
    for head, name, kfs in layers[:max_layers]:
        sp = sprite(name, 0)
        if sp is None:
            continue
        body = lerp_keyframes(kfs, t) or [[0, 0, 0], [1, 1], 0, [255, 255, 255], 1]
        pos = body[0] if isinstance(body[0], list) else [0, 0, 0]
        scl = body[1] if isinstance(body[1], list) else [1, 1]
        rot = float(body[2]) if len(body) > 2 else 0.0
        col = body[3] if len(body) > 3 and isinstance(body[3], list) else [255, 255, 255]
        alpha = float(body[4]) if len(body) > 4 else 1.0
        im = sp[0]
        sx = max(0.02, float(scl[0]))
        sy = max(0.02, float(scl[1]))
        w = max(1, int(round(im.width * sx)))
        h = max(1, int(round(im.height * sy)))
        im2 = im.resize((w, h), Image.NEAREST)
        if abs(rot) > 0.01:
            im2 = im2.rotate(-rot, resample=Image.NEAREST, expand=True)
        r, g, b = [int(c) for c in (list(col) + [255, 255, 255])[:3]]
        a = im2.getchannel('A').point(lambda v: int(v * max(0.0, min(1.0, alpha))))
        rgb = ImageChops.multiply(im2.convert('RGB'), Image.new('RGB', im2.size, (r, g, b)))
        im2 = rgb.convert('RGBA')
        im2.putalpha(a)
        items.append((im2, float(pos[0]), float(pos[1]), float(pos[2])))
    if not items:
        return None, 0
    x0 = min(-i[0].width / 2 + i[1] for i in items)
    x1 = max(i[0].width / 2 + i[1] for i in items)
    y0 = min(-i[0].height / 2 + i[2] for i in items)
    y1 = max(i[0].height / 2 + i[2] for i in items)
    pad = 4
    W = max(16, int(round(x1 - x0)) + pad * 2)
    Hh = max(16, int(round(y1 - y0)) + pad * 2)
    if W > 2000 or Hh > 2000:
        return None, 0
    out = Image.new('RGBA', (W, Hh), (0, 0, 0, 0))
    for im, px, py, pz in items:
        ox = int(round(px - x0 - im.width / 2)) + pad
        oy = int(round(py - y0 - im.height / 2)) + pad
        out.alpha_composite(im, (ox, oy))
    return out, len(items)


def main():
    args = sys.argv[1:]
    outdir = os.path.join(HERE, 'out', 'eff')
    step = 4
    t = 0.0
    pct = 0.4
    sheet_path = None
    for i, a in enumerate(args):
        nxt = args[i + 1] if i + 1 < len(args) else ''
        if a == '--out':
            outdir = nxt
        elif a == '--step':
            step = int(nxt)
        elif a == '--time':
            t = float(nxt)
            pct = None
        elif a == '--pct':
            pct = float(nxt)
        elif a == '--sheet':
            sheet_path = nxt
    files = sorted(f for f in os.listdir(eff.EFF) if f.lower().endswith(('.eff', '.eff_')))
    files = files[::max(1, step)]
    os.makedirs(outdir, exist_ok=True)
    ok = 0
    tiles = []
    for k, name in enumerate(files):
        im, n = render(os.path.join(eff.EFF, name), t, pct=pct)
        if im is None:
            continue
        im.save(os.path.join(outdir, os.path.splitext(name)[0] + '.png'))
        ok += 1
        tiles.append((os.path.splitext(name)[0], im))
        if (k + 1) % 50 == 0:
            print('  ...%d/%d  ok %d' % (k + 1, len(files), ok), flush=True)
    print('%d files, %d rendered -> %s' % (len(files), ok, outdir))
    if sheet_path and tiles:
        from PIL import ImageDraw
        cols, cw, ch = 10, 150, 170
        per = 80
        for page in range(0, len(tiles), per):
            chunk = tiles[page:page + per]
            rows = (len(chunk) + cols - 1) // cols
            sh = Image.new('RGB', (cols * cw, rows * ch), (40, 42, 49))
            dr = ImageDraw.Draw(sh)
            for j, (nm, im) in enumerate(chunk):
                cx = (j % cols) * cw
                cy = (j // cols) * ch
                sc = min((cw - 10) / im.width, (ch - 26) / im.height, 3.0)
                w = max(1, int(im.width * sc))
                h = max(1, int(im.height * sc))
                small = im.resize((w, h), Image.NEAREST)
                sh.paste(small, (cx + (cw - w) // 2, cy + (ch - 20 - h) // 2), small)
                dr.text((cx + 3, cy + ch - 16), nm[:22], fill=(220, 220, 225))
            p = sheet_path if page == 0 else '%s-%d%s' % (os.path.splitext(sheet_path)[0],
                                                          page // per + 1,
                                                          os.path.splitext(sheet_path)[1])
            sh.save(p)
            print('sheet', p, sh.size, len(chunk), 'cells')


if __name__ == '__main__':
    main()
