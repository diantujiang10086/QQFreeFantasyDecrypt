"""Exhaustively template-match a sprite (masked SSD) and rank candidates.

  python refbest.py --dir head [--ref 0] [--top 10]
  python refbest.py --dir npc --only npc1000101,npc1000201 ...

Ranking heads by the best masked match inside the reference identifies the head the
render actually wears (head0101 does not match, so the reference uses another one).
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


def first_record(path):
    d = open(path, 'rb').read()
    try:
        r = dimg.parse(d)
        if r.get('ok'):
            for pre, w, h, px, bpp in r['frames']:
                if px:
                    return d, w, h, bpp, px
    except Exception:
        pass
    import headtool
    recs, extra, k = headtool.segment(d)
    p, w, h, s, f = recs[0]
    return d, w, h, s // w, p + 16


def arrays(ref, path):
    d, w, h, bpp, px = first_record(path)
    tpl = np.asarray(dimg.to_image(d, px, w, h, bpp), dtype=np.float32)
    return tpl[:, :, :3], tpl[:, :, 3]


def best_match(ref, tpl_rgb, tpl_a):
    H, W = ref.shape[:2]
    th, tw = tpl_rgb.shape[:2]
    if th > H or tw > W:
        return 1e9, -1, -1
    m = tpl_a > 40
    n = int(m.sum())
    if n == 0:
        return 1e9, -1, -1
    best = (1e18, -1, -1)
    flat = tpl_rgb[m]
    for y in range(H - th + 1):
        for x in range(W - tw + 1):
            d = float(np.abs(ref[y:y + th, x:x + tw][m] - flat).mean())
            if d < best[0]:
                best = (d, x, y)
    return best


def main():
    args = sys.argv[1:]
    idx = int(args[args.index('--ref') + 1]) if '--ref' in args else 0
    top = int(args[args.index('--top') + 1]) if '--top' in args else 10
    sub = args[args.index('--dir') + 1] if '--dir' in args else 'head'
    only = args[args.index('--only') + 1].split(',') if '--only' in args else None
    name = ALL[idx]
    ref = np.asarray(Image.open(os.path.join(REF, name)).convert('RGB'), dtype=np.float32)
    dirp = os.path.join(SRC, sub)
    files = sorted(n for n in os.listdir(dirp) if n.lower().endswith('.gsn'))
    if only:
        files = [n for n in files if any(o in n for o in only)]
    scored = []
    for n in files:
        try:
            tr, ta = arrays(ref, os.path.join(dirp, n))
        except Exception as e:
            print('  skip', esc(n), e)
            continue
        s, x, y = best_match(ref, tr, ta)
        scored.append((s, n, x, y, tr.shape[1], tr.shape[0]))
    scored.sort()
    print('ref %s  %s files=%d' % (esc(name), sub, len(files)))
    for s, n, x, y, w, h in scored[:top]:
        print('   %-14s score=%6.2f at (%2d,%2d) tpl %dx%d' % (esc(n), s, x, y, w, h))


if __name__ == '__main__':
    main()
