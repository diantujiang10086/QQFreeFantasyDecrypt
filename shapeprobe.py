"""Shape-only probe: how much of a head sprite's silhouette lands on the render's sprite pixels."""
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
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def grid_mask(im):
    a = np.asarray(im.convert('RGB')).astype(np.int32)
    return (a % 17 == 0).all(axis=2)


def best_shape(mask, alpha, thr=128):
    th, tw = alpha.shape
    H, W = mask.shape
    best = (-1, -1, -1, 0)
    for y in range(0, max(1, H - th + 1)):
        for x in range(0, max(1, W - tw + 1)):
            inside = int((mask[y:y + th, x:x + tw] & alpha).sum())
            if inside > best[0]:
                best = (inside, x, y, int(alpha.sum()))
    return best


def main():
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    idx = int(opt('--ref', 0))
    stem = opt('--head', 'head0251')
    y0, y1 = int(opt('--y0', 0)), int(opt('--y1', 55))
    im = Image.open(os.path.join(REF, ALL[idx]))
    mask = grid_mask(im)[y0:y1]
    print('ref %-8s rows %d..%d  mask px %d' % (esc(ALL[idx]), y0, y1, int(mask.sum())))
    d = open(os.path.join(SRC, 'head', stem + '.gsn'), 'rb').read()
    recs, extra, k = headtool.segment(d)
    rows = []
    for i in range(len(recs)):
        p, w, h, s, f = recs[i]
        spr = dimg.to_image(d, p + 16, w, h, s // w).convert('RGBA')
        al = np.asarray(spr)[:, :, 3] > 128
        inside, x, y, n = best_shape(mask, al)
        rows.append((inside / max(1, n), inside, n, i, w, h, x, y + y0))
    rows.sort(reverse=True)
    for pct, inside, n, i, w, h, x, y in rows:
        print('  rec %2d  %2dx%-2d  cover %5.1f%%  (%4d/%-4d) at (%2d,%3d)%s'
              % (i, w, h, 100 * pct, inside, n, x, y, '' if i % 2 == 0 else '   (mask rec)'))


if __name__ == '__main__':
    main()
