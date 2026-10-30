"""Fast library-wide identification of the sprites drawn in a reference render.

  python refwho2.py --ref 0 [--kind npc|head|cap|face] [--top 20] [--frame 0]

Only the first record is touched (no full walk): header -> preamble -> first signature ->
pixels, so a 20k-file scan stays in the minutes range.  The reference mask is the set of
pixels whose three channels are all multiples of 17 (the sprite palette grid); the beige
UI background is not on that grid.
"""
import mmap
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402

REF = os.path.join(HERE, 'out', 'ref')
SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def sprite0(path):
    """(alpha bool 2-D, sprite w, sprite h) from the first record only"""
    with open(path, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as d:
            h = dimg.head(d)
            hs = dimg.hints(h)
            if not hs:
                return None
            fp, oh, _tag = hs[0]
            sig = fp - 16
            if sig < 0 or sig + 16 > len(d):
                return None
            w, hh, stride, flag = [dimg.u32(d, sig + 4 * i) for i in range(4)]
            if not (1 <= w <= 8192 and 1 <= hh <= 8192 and flag in (1, 2) and stride == 2 * flag * w):
                return None
            nb = stride * hh
            px = sig + 16
            if px + nb > len(d):
                return None
            raw = d[px:px + nb]
            bw = 2 * flag                      # bytes per pixel
            alpha = np.frombuffer(raw, dtype=np.uint8).reshape(hh, stride)[:, bw - 1::bw]
            return alpha > 40, w, hh


def best_iou(mask, tpl):
    H, W = mask.shape
    th, tw = tpl.shape
    if th > H or tw > W:
        return 0.0, -1, -1
    fh, fw = H + th - 1, W + tw - 1
    F = np.fft.rfft2(mask, (fh, fw)) * np.conj(np.fft.rfft2(tpl[::-1, ::-1], (fh, fw)))
    cc = np.rint(np.fft.irfft2(F, (fh, fw))[th - 1:th - 1 + H - th + 1,
                                           tw - 1:tw - 1 + W - tw + 1])
    inter = np.maximum(cc, 0)
    union = float(tpl.sum()) + float(mask.sum()) - inter
    iou = inter / np.maximum(union, 1)
    y, x = np.unravel_index(int(np.argmax(iou)), iou.shape)
    return float(iou[y, x]), int(x), int(y)


def main():
    a = sys.argv[1:]
    idx = int(a[a.index('--ref') + 1]) if '--ref' in a else 0
    kind = a[a.index('--kind') + 1] if '--kind' in a else 'npc'
    top = int(a[a.index('--top') + 1]) if '--top' in a else 20
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 0
    size = a[a.index('--size') + 1] if '--size' in a else ''
    tol = int(a[a.index('--tol') + 1]) if '--tol' in a else 0
    want = (int(size.split('x')[0]), int(size.split('x')[1])) if size else None
    mask = (np.asarray(Image.open(os.path.join(REF, ALL[idx])).convert('RGB')).astype(np.int16)
            % 17 == 0).all(axis=2).astype(float)
    dirp = os.path.join(SRC, kind)
    files = sorted(n for n in os.listdir(dirp) if n.lower().endswith('.gsn'))
    if limit:
        files = files[:limit]
    print('ref %-10s mask=%d  kind=%s files=%d%s' % (esc(ALL[idx]), int(mask.sum()), kind, len(files),
                                                    '' if want is None else ' want %dx%d±%d' % (want[0], want[1], tol)), flush=True)
    rows = []
    bad = 0
    kept = 0
    for i, n in enumerate(files):
        try:
            r = sprite0(os.path.join(dirp, n))
        except Exception:
            r = None
        if r is None:
            bad += 1
            continue
        alpha, w, h = r
        if want and (abs(w - want[0]) > tol or abs(h - want[1]) > tol):
            continue
        kept += 1
        iou, x, y = best_iou(mask, alpha.astype(float))
        rows.append((iou, n, x, y, w, h, int(alpha.sum())))
        if (i + 1) % 2000 == 0:
            print('  ... %d/%d  (skip %d, kept %d)' % (i + 1, len(files), bad, kept), flush=True)
    rows.sort(reverse=True)
    print('--- top %d  (unparsed %d, size-filtered %d)' % (top, bad, kept), flush=True)
    for iou, n, x, y, w, h, npx in rows[:top]:
        print('  %.3f  %-16s at (%2d,%2d)  %dx%d  alpha=%d' % (iou, esc(n), x, y, w, h, npx), flush=True)


if __name__ == '__main__':
    main()
