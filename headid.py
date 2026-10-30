"""Identify the head in the render: which .gsn layer reproduces the pixels the body does not cover?

  python headid.py [--ref 0] [--body npc1000101] [--frame 4] [--at 26,30] [--top 15]
"""
import os
import sys

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


def sprite_layers(path):
    """yield (index, w, h, rgba array) for every record (colour and mask)"""
    d = open(path, 'rb').read()
    recs, extra, k = headtool.segment(d)
    for i, (p, w, h, s, f) in enumerate(recs):
        im = dimg.to_image(d, p + 16, w, h, s // w).convert('RGBA')
        yield i, w, h, np.asarray(im).astype(np.int32)


def main():
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    idx = int(opt('--ref', 0))
    stem = opt('--body', 'npc1000101')
    bf = int(opt('--frame', 4))
    bx, by = (int(v) for v in opt('--at', '26,30').split(','))
    top = int(opt('--top', 15))

    im = Image.open(os.path.join(REF, ALL[idx]))
    a3 = np.asarray(im.convert('RGB')).astype(np.int32)
    mask = (a3 % 17 == 0).all(axis=2)
    d = open(os.path.join(SRC, 'npc', stem + '.gsn'), 'rb').read()
    r = dimg.parse(d)
    pre, w, h, px, bpp = r['frames'][bf]
    ba = np.asarray(dimg.to_image(d, px, w, h, bpp).convert('RGBA'))[:, :, 3] > 128
    claim = np.zeros_like(mask)
    claim[by:by + h, bx:bx + w] |= ba
    left = mask & ~claim
    ys, xs = np.nonzero(left)
    cols = a3[ys, xs]
    n = len(ys)
    print('leftover %d px  bbox x %d..%d y %d..%d' % (n, xs.min(), xs.max(), ys.min(), ys.max()))

    best = []
    files = sorted(os.listdir(os.path.join(SRC, 'head')))
    for fn in files:
        if not fn.endswith('.gsn'):
            continue
        try:
            for i, w2, h2, arr in sprite_layers(os.path.join(SRC, 'head', fn)):
                al = arr[:, :, 3] > 128
                rgb = arr[:, :, :3]
                x0lo = max(0, xs.max() - w2 + 1)
                x0hi = min(im.width - w2, xs.min())
                y0lo = max(0, ys.max() - h2 + 1)
                y0hi = min(im.height - h2, ys.min())
                for y0 in range(y0lo, y0hi + 1):
                    dy = ys - y0
                    if dy.min() < 0 or dy.max() >= h2:
                        continue
                    for x0 in range(x0lo, x0hi + 1):
                        dx = xs - x0
                        if dx.min() < 0 or dx.max() >= w2:
                            continue
                        if not al[dy, dx].all():
                            continue
                        hit = int(np.all(rgb[dy, dx] == cols, axis=1).sum())
                        best.append((hit, fn, i, x0, y0, w2, h2))
        except Exception as e:      # noqa: BLE001
            print('  skip', fn, e)
    best.sort(reverse=True)
    print('candidates whose silhouette fully covers the leftover: %d' % len(best))
    for hit, fn, i, x0, y0, w2, h2 in best[:top]:
        print('  %4d/%d  %5.1f%%  %-14s rec %2d %2dx%-2d at (%d,%d)'
              % (hit, n, 100.0 * hit / n, fn, i, w2, h2, x0, y0))
    if best:
        hit, fn, i, x0, y0, w2, h2 = best[0]
        d2 = open(os.path.join(SRC, 'head', fn), 'rb').read()
        recs, extra, k = headtool.segment(d2)
        p, ww, hh, s, f = recs[i]
        spr = dimg.to_image(d2, p + 16, ww, hh, s // ww).convert('RGBA')
        ref_im = Image.open(os.path.join(REF, ALL[idx])).convert('RGB')
        comp = Image.new('RGBA', ref_im.size, (0, 0, 0, 0))
        comp.alpha_composite(spr, (x0, y0))
        comp.alpha_composite(dimg.to_image(d, px, w, h, bpp).convert('RGBA'), (bx, by))
        out = Image.new('RGB', (ref_im.width * 3 + 16, ref_im.height), (40, 40, 46))
        out.paste(ref_im, (0, 0))
        out.paste(comp.convert('RGB'), (ref_im.width + 8, 0), comp)
        diff = np.abs(np.asarray(ref_im).astype(np.int32) - np.asarray(comp.convert('RGB')).astype(np.int32)).sum(axis=2)
        out.paste(Image.fromarray((255 - np.clip(diff * 3, 0, 255)).astype(np.uint8)).convert('RGB'),
                  (ref_im.width * 2 + 16, 0))
        dst = os.path.join(HERE, 'out', 'headid_%s_%s_r%d.png'
                           % (esc(ALL[idx]).replace('.png', '').replace('\\u', 'u'), fn.replace('.gsn', ''), i))
        out.resize((out.width * 4, out.height * 4), Image.NEAREST).save(dst)
        print('wrote', esc(dst))


if __name__ == '__main__':
    main()
