"""Which record of a head file reproduces the reference render? Exact-pixel match probe."""
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


def search(ref, spr, thr=200):
    arr = np.asarray(spr).astype(np.int32)
    m = arr[:, :, 3] > thr
    rgb = arr[:, :, :3][m]
    th, tw = m.shape
    H, W = ref.shape[:2]
    best = (-1, -1, -1)
    for y in range(0, max(1, H - th + 1)):
        for x in range(0, max(1, W - tw + 1)):
            sub = ref[y:y + th, x:x + tw][m]
            hits = int(np.all(sub == rgb, axis=1).sum())
            if hits > best[0]:
                best = (hits, x, y)
    return best[0], best[1], best[2], int(m.sum())


def main():
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    idx = int(opt('--ref', 0))
    stem = opt('--head', 'head0251')
    y0, y1 = int(opt('--y0', 0)), int(opt('--y1', 60))
    ref = np.asarray(Image.open(os.path.join(REF, ALL[idx])).convert('RGB')).astype(np.int32)
    ref = ref[y0:y1]
    print('ref %-8s rows %d..%d' % (esc(ALL[idx]), y0, y1))
    d = open(os.path.join(SRC, 'head', stem + '.gsn'), 'rb').read()
    recs, extra, k = headtool.segment(d)
    print('%s: %d records' % (stem, len(recs)))
    rows = []
    for i in range(len(recs)):
        p, w, h, s, f = recs[i]
        im = dimg.to_image(d, p + 16, w, h, s // w).convert('RGBA')
        hits, x, y, n = search(ref, im)
        rows.append((hits / max(1, n), hits, n, i, w, h, x, y + y0))
    rows.sort(reverse=True)
    for pct, hits, n, i, w, h, x, y in rows:
        print('  rec %2d  %2dx%-2d  %4d/%-4d exact %5.1f%%  at (%2d,%3d)%s'
              % (i, w, h, hits, n, 100 * pct, x, y, '   <== colour' if i % 2 == 0 else ''))


if __name__ == '__main__':
    main()
