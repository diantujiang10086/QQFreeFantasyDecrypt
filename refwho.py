"""Which sprite in the library is actually drawn in the reference renders?

  python refwho.py --ref 0 --kind npc [--top 20] [--limit N] [--shard i/N]

For every .gsn the frame-0 sprite alpha is correlated (FFT) with the reference
foreground mask; the best placements are scored by IoU.  A true match sits well above
0.5, a wrong sprite lands near 0.1.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import paths

REF = os.path.join(HERE, 'out', 'ref')
SRC = paths.sub('data/official/avatar')
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def fg_mask(im, tol=60, grid=True):
    if grid:
        return (np.asarray(im.convert('RGB')).astype(np.int16) % 17 == 0).all(axis=2)
    """border flood fill on the beige background texture"""
    from collections import deque
    a = np.asarray(im.convert('RGB')).astype(np.int16)
    h, w = a.shape[:2]
    seed = a[0, 0]
    seen = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        q.append((0, x))
        q.append((h - 1, x))
    for y in range(h):
        q.append((y, 0))
        q.append((y, w - 1))
    while q:
        y, x = q.popleft()
        if y < 0 or x < 0 or y >= h or x >= w or seen[y, x]:
            continue
        if np.abs(a[y, x] - seed).sum() > tol * 3:
            continue
        seen[y, x] = True
        q.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    return ~seen


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


def sprite_alpha(path, frame=0, scale=1.0):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    if not r.get('ok'):
        return None
    pre, w, h, px, bpp = r['frames'][frame]
    if not px:
        return None
    im = dimg.to_image(d, px, w, h, bpp)
    if scale != 1.0:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.NEAREST)
    return (np.asarray(im)[:, :, 3] > 40).astype(float)


def main():
    a = sys.argv[1:]
    idx = int(a[a.index('--ref') + 1]) if '--ref' in a else 0
    kind = a[a.index('--kind') + 1] if '--kind' in a else 'npc'
    top = int(a[a.index('--top') + 1]) if '--top' in a else 20
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 0
    scale = float(a[a.index('--scale') + 1]) if '--scale' in a else 1.0
    name = ALL[idx]
    mask = fg_mask(Image.open(os.path.join(REF, name))).astype(float)
    dirp = os.path.join(SRC, kind)
    files = sorted(n for n in os.listdir(dirp) if n.lower().endswith('.gsn'))
    if limit:
        files = files[:limit]
    print('ref %-10s fg=%d  kind=%s files=%d scale=%.2f'
          % (esc(name), int(mask.sum()), kind, len(files), scale))
    rows = []
    for i, n in enumerate(files):
        try:
            A = sprite_alpha(os.path.join(dirp, n), 0, scale)
        except Exception:
            A = None
        if A is None:
            continue
        iou, x, y = best_iou(mask, A)
        rows.append((iou, n, x, y, A.shape[1], A.shape[0]))
        if (i + 1) % 2000 == 0:
            print('  ... %d/%d' % (i + 1, len(files)))
    rows.sort(reverse=True)
    print('--- top %d' % top)
    for iou, n, x, y, w, h in rows[:top]:
        print('  %.3f  %-14s at (%2d,%2d)  %dx%d' % (iou, esc(n), x, y, w, h))


if __name__ == '__main__':
    main()
