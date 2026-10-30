"""Compare a stacked composite with a reference render pixel by pixel.

  python cmpix.py [--ref 0] [--body npc1000101] [--head head0101] [--at 34,12] [--dx 9] [--dy 4]

Reports, over the pixels where the composite is opaque:
  exact  = share of pixels whose RGB equals the sprite RGB exactly
  mad    = mean absolute RGB difference
  mad_nb = same, skipping pixels whose reference colour is close to the background beige
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402
import paths

SRC = paths.sub('data/official/avatar')
REF = os.path.join(HERE, 'out', 'ref')


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def load(path):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    if r.get('ok'):
        pre, w, h, px, bpp = r['frames'][0]
        im = dimg.to_image(d, px, w, h, bpp)
    else:
        recs, extra, k = headtool.segment(d)
        p, w, h, s, f = recs[0]
        im = dimg.to_image(d, p + 16, w, h, s // w)
    return im.convert('RGBA')


def main():
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    idx = int(opt('--ref', 0))
    body, head = opt('--body', 'npc1000101'), opt('--head', 'head0101')
    at = tuple(int(v) for v in opt('--at', '34,12').split(','))
    dx, dy = int(opt('--dx', 9)), int(opt('--dy', 4))
    refs = sorted(n for n in os.listdir(REF) if n.endswith('.png'))
    ref = np.asarray(Image.open(os.path.join(REF, refs[idx])).convert('RGB')).astype(int)
    H, W = ref.shape[:2]
    beige = np.abs(ref - ref[0, 0]).sum(axis=2) < 40

    b = load(os.path.join(SRC, 'npc', body + '.gsn'))
    h = load(os.path.join(SRC, 'head', head + '.gsn'))
    comp = np.zeros((H, W, 4), np.int32)
    for im, pos in ((b, at), (h, (at[0] + dx, at[1] + dy))):
        arr = np.asarray(im)
        y0, x0 = pos[1], pos[0]
        hh, ww = arr.shape[:2]
        ys, ye = max(0, y0), min(H, y0 + hh)
        xs, xe = max(0, x0), min(W, x0 + ww)
        if ys >= ye or xs >= xe:
            continue
        sub = arr[ys - y0:ye - y0, xs - x0:xe - x0]
        m = sub[:, :, 3] > 40
        region = comp[ys:ye, xs:xe]
        region[m] = sub[m].astype(np.int32)

    m = comp[:, :, 3] > 40
    rgb = comp[:, :, :3]
    exact = float((np.all(rgb[m] == ref[m], axis=1)).mean()) if m.any() else 0.0
    mad = float(np.abs(rgb[m] - ref[m]).mean()) if m.any() else 0.0
    keep = m & ~beige
    mad_nb = float(np.abs(rgb[keep] - ref[keep]).mean()) if keep.any() else 0.0
    exact_nb = float((np.all(rgb[keep] == ref[keep], axis=1)).mean()) if keep.any() else 0.0
    print('ref %-8s %dx%d  composite px=%d (body at %s, head at %+d,%+d)'
          % (esc(refs[idx]), W, H, int(m.sum()), at, dx, dy))
    print('  exact=%.1f%%  mad=%.1f   | not-background: exact=%.1f%% mad=%.1f'
          % (exact * 100, mad, exact_nb * 100, mad_nb))
    # where the biggest differences are
    d = np.abs(rgb - ref).sum(axis=2)
    d[~m] = 0
    ys, xs = np.where(d > 60)
    if len(ys):
        print('  %d composite px differ by >60 (sum RGB); bbox y %d..%d x %d..%d'
              % (len(ys), ys.min(), ys.max(), xs.min(), xs.max()))
    for dy2 in (-2, 0, 2):
        for dx2 in (-2, 0, 2):
            pass


if __name__ == '__main__':
    main()
