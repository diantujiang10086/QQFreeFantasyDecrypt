"""Calibrate the head offset from the real renders, using the known frame/direction map.

  python calib.py [--ref 0] [--body npc1000101] [--bodyframe 4] [--head head0251] [--headdir 5]

The user's map (m02600) says 前.png = npc1000101 frame 4 + head0251 direction 5 colour.
Both layers come straight out of .gsn, so a correct placement makes the sprite pixels
match the render *exactly*; we search placement by counting exact RGB matches.
"""
import os
import sys

from types import SimpleNamespace

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402
import paths

SRC = paths.sub('data/official/avatar')
REF = os.path.join(HERE, 'out', 'ref')
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def load_body(path, frame):
    d = open(path, 'rb').read()
    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    r = dimg.parse(d)
    pre, w, h, px, bpp = r['frames'][frame]
    b0 = [dimg.u32(d, pre + 4 * i) for i in range(4)]
    im = dimg.to_image(d, px, w, h, bpp).convert('RGBA')
    return SimpleNamespace(img=im, W=pw[3], H=pw[4], cx=pw[5], cy=pw[6],
                           at=(b0[1], b0[2]), nframes=len(r['frames']))


def load_head(path, idx):
    d = open(path, 'rb').read()
    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    recs, extra, k = headtool.segment(d)
    p, w, h, s, f = recs[min(idx, len(recs) - 1)]
    im = dimg.to_image(d, p + 16, w, h, s // w).convert('RGBA')
    return SimpleNamespace(img=im, W=pw[3], H=pw[4], cx=pw[5], cy=pw[6], nrec=len(recs))


def search(ref, spr, coarse_only=False):
    """maximise count of exact RGB matches; returns (hits, x, y, npix)"""
    arr = np.asarray(spr).astype(np.int32)
    m = arr[:, :, 3] > 200
    rgb = arr[:, :, :3][m]
    th, tw = m.shape
    H, W = ref.shape[:2]
    best = (-1, -1, -1)
    for y in range(0, H - th + 1):
        for x in range(0, W - tw + 1):
            sub = ref[y:y + th, x:x + tw][m]
            hits = int(np.all(sub == rgb, axis=1).sum())
            if hits > best[0]:
                best = (hits, x, y)
    return best[0], best[1], best[2], int(m.sum())


def main():
    a = sys.argv[1:]
    def opt(k, dflt):
        return a[a.index(k) + 1] if k in a else dflt
    idx = int(opt('--ref', 0))
    body = opt('--body', 'npc1000101')
    bf = int(opt('--bodyframe', 4))
    head = opt('--head', 'head0251')
    hd = int(opt('--headdir', 5))
    ref = np.asarray(Image.open(os.path.join(REF, ALL[idx])).convert('RGB')).astype(np.int32)
    print('ref %-8s %dx%d' % (esc(ALL[idx]), ref.shape[1], ref.shape[0]))

    b = load_body(os.path.join(SRC, 'npc', body + '.gsn'), bf)
    print('body %s frame %d: %dx%d canvas %dx%d pivot (%d,%d) at %s'
          % (body, bf, b.img.width, b.img.height, b.W, b.H, b.cx, b.cy, b.at))
    hits_b, bx, by, nb = search(ref, b.img)
    print('  body best: %d/%d exact px (%.1f%%) at (%d,%d)'
          % (hits_b, nb, 100.0 * hits_b / nb, bx, by))

    h = load_head(os.path.join(SRC, 'head', head + '.gsn'), 2 * (hd - 1))
    print('head %s dir %d: sprite %dx%d canvas %dx%d pivot (%d,%d) recs=%d'
          % (head, hd, h.img.width, h.img.height, h.W, h.H, h.cx, h.cy, h.nrec))
    hits_h, hx, hy, nh = search(ref, h.img)
    print('  head best: %d/%d exact px (%.1f%%) at (%d,%d)'
          % (hits_h, nh, 100.0 * hits_h / nh, hx, hy))
    print('=> head sprite offset relative to body sprite: (%+d, %+d)' % (hx - bx, hy - by))
    # in body canvas coordinates: where the head pivot lands
    jx = (hx - bx) + b.at[0] + h.cx
    jy = (hy - by) + b.at[1] + h.cy
    print('   head pivot lands at body canvas (%d,%d);  body pivot (%d,%d) -> (%+d,%+d)'
          % (jx, jy, b.cx, b.cy, jx - b.cx, jy - b.cy))

    # composite and compare
    comp = Image.new('RGBA', (ref.shape[1], ref.shape[0]), (0, 0, 0, 0))
    comp.alpha_composite(b.img, (bx, by))
    comp.alpha_composite(h.img, (hx, hy))
    rgb = np.asarray(comp)[:, :, :3].astype(np.int32)
    m = np.asarray(comp)[:, :, 3] > 200
    exact = float(np.all(rgb[m] == ref[m], axis=1).mean())
    print('   composite: %d px, exact match %.1f%%' % (int(m.sum()), 100 * exact))
    sheet = Image.new('RGB', (ref.shape[1] * 3 + 16, ref.shape[0]), (40, 40, 46))
    sheet.paste(Image.fromarray(ref.astype(np.uint8)), (0, 0))
    sheet.paste(comp.convert('RGB'), (ref.shape[1] + 8, 0), comp)
    ov = Image.fromarray(ref.astype(np.uint8)).copy()
    ov.paste(comp.convert('RGB'), (0, 0), comp)
    sheet.paste(ov, (ref.shape[1] * 2 + 16, 0))
    dst = os.path.join(HERE, 'out', 'calib_%s_f%d_%s_d%d.png' % (esc(ALL[idx]).replace('.png', '').replace('\\u', 'u'), bf, head, hd))
    sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(dst)
    print('wrote', esc(dst))


if __name__ == '__main__':
    main()
