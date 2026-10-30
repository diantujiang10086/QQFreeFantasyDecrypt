"""Build a character mask for a reference render by flood-filling the background from the border.

  python refmask.py [tol] [--ascii] [name]

Tests several tolerances and reports how much is background, then prints the remaining
silhouette as ASCII so it can be judged without viewing the image.
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'out', 'ref')
SYM = '@#*+=-:. '


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def bg_mask(arr, tol):
    h, w = arr.shape[:2]
    refs = [arr[0, 0], arr[0, w - 1], arr[h - 1, 0], arr[h - 1, w - 1]]
    # background tolerance grows with distance from the border seeds: use nearest corner colour
    seen = np.zeros((h, w), dtype=bool)
    bg = np.zeros((h, w), dtype=bool)
    q = deque()
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if not seen[y, x]:
            seen[y, x] = True
            q.append((x, y))
    while q:
        x, y = q.popleft()
        c = arr[y, x].astype(np.int16)
        if not any(int(np.abs(c - r).max()) <= tol for r in refs):
            continue
        bg[y, x] = True
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((nx, ny))
    return bg


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    tol = int(args[0]) if args else 40
    want_ascii = '--ascii' in sys.argv
    names = [n for n in sorted(os.listdir(REF)) if n.endswith('.png')]
    for n in names[:1]:
        arr = np.asarray(Image.open(os.path.join(REF, n)).convert('RGB'))
        for t in (20, 30, 40, 50, 60, 80):
            bg = bg_mask(arr, t)
            fg = ~bg
            ys, xs = np.nonzero(fg)
            print('%-10s tol=%2d bg=%5.1f%% fg bbox=(%d,%d)-(%d,%d) fg=%d'
                  % (esc(n), t, 100.0 * bg.sum() / bg.size, xs.min(), ys.min(), xs.max(), ys.max(), fg.sum()))
        bg = bg_mask(arr, tol)
        fg = ~bg
        if want_ascii:
            print('ascii tol=%d' % tol)
            step = 1
            for y in range(0, arr.shape[0], step):
                row = ''.join('#' if fg[y, x] else '.' for x in range(0, arr.shape[1], step))
                print('%3d %s' % (y, row))


if __name__ == '__main__':
    main()
