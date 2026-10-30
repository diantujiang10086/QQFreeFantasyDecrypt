"""Reproduce the reference renders from .gsn layers and report the pixel-exact agreement.

  python repro.py --head head2151 [--sheet]

For each of the eight views the body frame and the head direction come from the user's map
(m02600).  Each sprite is placed by an exact-pixel search, then the whole composite is
compared to the render.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
REF = os.path.join(HERE, 'out', 'ref')
BODY = 'npc1000101'

MAP = [
    ('\u524d', 4, 5, False),
    ('\u540e', 3, 4, False),
    ('\u5de6', 1, 2, False),
    ('\u53f3', 1, 2, True),
    ('\u5de6\u4e0a', 2, 3, False),
    ('\u53f3\u4e0a', 2, 3, True),
    ('\u5de6\u4e0b', 0, 1, False),
    ('\u53f3\u4e0b', 0, 1, True),
]


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def search(ref, spr, thr=200):
    arr = np.asarray(spr).astype(np.int32)
    m = arr[:, :, 3] > thr
    rgb = arr[:, :, :3][m]
    th, tw = m.shape
    H, W = ref.shape[:2]
    best = (-1, -1, -1)
    for y in range(0, max(1, H - th + 1)):
        for x in range(0, max(1, W - tw + 1)):
            hits = int(np.all(ref[y:y + th, x:x + tw][m] == rgb, axis=1).sum())
            if hits > best[0]:
                best = (hits, x, y)
    return best[0], best[1], best[2], int(m.sum())


def main():
    a = sys.argv[1:]
    head = a[a.index('--head') + 1] if '--head' in a else 'head2151'
    sheet_wanted = '--sheet' in a
    clean_only = '--clean' in a
    views = [m for m in MAP if not (clean_only and m[3])]
    db = open(os.path.join(SRC, 'npc', BODY + '.gsn'), 'rb').read()
    rb = dimg.parse(db)
    dh = open(os.path.join(SRC, 'head', head + '.gsn'), 'rb').read()
    recs, extra, k = headtool.segment(dh)
    single = len(recs) <= 5
    tiles = []
    for name, bf, hd, mir in views:
        path = os.path.join(REF, name + '.png')
        if not os.path.exists(path):
            print('missing', esc(name))
            continue
        ref_im = Image.open(path).convert('RGB')
        ref = np.asarray(ref_im).astype(np.int32)
        pre, w, h, px, bpp = rb['frames'][bf]
        body = dimg.to_image(db, px, w, h, bpp).convert('RGBA')
        hi = (hd - 1) if single else 2 * (hd - 1)
        p, hw, hh, s, f = recs[hi]
        head_im = dimg.to_image(dh, p + 16, hw, hh, s // w).convert('RGBA')
        combos = []
        for bmir in ({True, False} if mir else {False}):
            for hmir in ({True, False} if mir else {False}):
                b2 = body.transpose(Image.FLIP_LEFT_RIGHT) if bmir else body
                h2 = head_im.transpose(Image.FLIP_LEFT_RIGHT) if hmir else head_im
                hb, bx, by, nb = search(ref, b2)
                hh2, hx, hy, nh = search(ref, h2)
                combos.append((hb / nb + hh2 / nh, bmir, hmir, b2, bx, by, h2, hx, hy, hb, nb, hh2, nh))
        combos.sort(reverse=True, key=lambda t: t[0])
        s0, bmir, hmir, b2, bx, by, h2, hx, hy, hb, nb, hh2, nh = combos[0]
        comp = Image.new('RGBA', ref_im.size, (0, 0, 0, 0))
        comp.alpha_composite(b2, (bx, by))
        comp.alpha_composite(h2, (hx, hy))
        ca = np.asarray(comp)
        m = ca[:, :, 3] > 200
        exact = float(np.all(ca[:, :, :3][m] == ref[m], axis=1).mean())
        print('%-6s body f%d%s (%d,%d) %5.1f%%  head d%d%s (%d,%d) %5.1f%%  -> exact %.1f%% of %d px'
              % (esc(name).replace('\\u', 'u'), bf, ' mirrored' if bmir else '', bx, by, 100.0 * hb / nb,
                 hd, ' mirrored' if hmir else '', hx, hy, 100.0 * hh2 / nh, 100 * exact, int(m.sum())))
        if sheet_wanted:
            tiles.append((name, ref_im, comp, exact, bx, by, hx, hy))
    if sheet_wanted and tiles:
        scale = 3
        W, H = tiles[0][1].size
        sheet = Image.new('RGB', (len(tiles) * (W * scale + 6), H * scale * 2 + 24), (30, 30, 34))
        for i, (name, r, c, ex, bx, by, hx, hy) in enumerate(tiles):
            x = i * (W * scale + 6)
            sheet.paste(r.resize((W * scale, H * scale), Image.NEAREST), (x, 0))
            bg = Image.new('RGB', r.size, (30, 30, 34))
            bg.paste(c.convert('RGB'), (0, 0), c)
            sheet.paste(bg.resize((W * scale, H * scale), Image.NEAREST), (x, H * scale + 20))
        dst = os.path.join(HERE, 'out', 'repro_sheet.png')
        sheet.save(dst)
        print('wrote', esc(dst))


if __name__ == '__main__':
    main()
