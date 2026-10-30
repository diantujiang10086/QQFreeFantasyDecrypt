"""Locate known sprites inside the reference renders by masked template matching.

  python refmatch2.py                 # front view, several candidate bodies + heads
  python refmatch2.py --scale 1,1.5,2

Prints the best position + score for each template, so the body -> head offset that
the real render uses can be read off the reference instead of guessed.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg  # noqa: E402
import paths

SRC = paths.sub('data/official/avatar')
REF = os.path.join(HERE, 'out', 'ref')


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def sprite(path, frame=0):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    pre, w, h, px, bpp = r['frames'][frame]
    return dimg.to_image(d, px, w, h, bpp)


def head_sprite(path, k=0):
    d, recs, r = None, None, None
    import combo
    d, recs, r = combo.recursive_records(path)
    w, h, bpp, px = recs[k]
    return dimg.to_image(d, px, w, h, bpp)


def to_arrays(im, scale=1.0):
    if scale != 1.0:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    a = np.asarray(im.convert('RGBA'), dtype=np.float32)
    return a[:, :, :3], a[:, :, 3]


def match(img_rgb, tpl_rgb, tpl_a, stride=1):
    """Exhaustive masked mean-abs-diff. Returns (score, x, y) sorted best-first."""
    H, W = img_rgb.shape[:2]
    th, tw = tpl_rgb.shape[:2]
    m = tpl_a > 16
    n = int(m.sum())
    if n == 0 or th > H or tw > W:
        return []
    t = tpl_rgb[m]                       # (n,3)
    out = []
    for y in range(0, H - th + 1, stride):
        for x in range(0, W - tw + 1, stride):
            win = img_rgb[y:y + th, x:x + tw][m]
            out.append((float(np.abs(win - t).mean()), x, y))
    out.sort()
    return out


def main():
    a = sys.argv[1:]
    scales = [float(v) for v in (a[a.index('--scale') + 1] if '--scale' in a else '1').split(',')]
    ref = Image.open(os.path.join(REF, '\u524d.png')).convert('RGBA')       # 前
    print('ref size', ref.size)
    bodies = ['npc1000101', 'npc1000201', 'npc1000301']
    heads = ['head0101', 'head0251']
    for sc in scales:
        rgb, _ = to_arrays(ref, 1.0)     # reference is matched at its own scale
        print('== scale %.2f' % sc)
        best = {}
        for nm in bodies:
            im = sprite(os.path.join(SRC, 'npc', nm + '.gsn'))
            tr, ta = to_arrays(im, sc)
            res = match(rgb, tr, ta)
            if res:
                print('  body %-12s best score %.2f at (%d,%d)  (tpl %dx%d)'
                      % (nm, res[0][0], res[0][1], res[0][2], tr.shape[1], tr.shape[0]))
                best[nm] = res[0]
        for nm in heads:
            im = head_sprite(os.path.join(SRC, 'head', nm + '.gsn'))
            tr, ta = to_arrays(im, sc)
            res = match(rgb, tr, ta)
            if res:
                print('  head %-12s best score %.2f at (%d,%d)  (tpl %dx%d)'
                      % (nm, res[0][0], res[0][1], res[0][2], tr.shape[1], tr.shape[0]))
                best[nm] = res[0]
        if 'npc1000101' in best:
            bx, by = best['npc1000101'][1], best['npc1000101'][2]
            for nm in heads:
                if nm in best:
                    hx, hy = best[nm][1], best[nm][2]
                    print('  --> offset head-body (top-left) = (%d,%d)' % (hx - bx, hy - by))


if __name__ == '__main__':
    main()
