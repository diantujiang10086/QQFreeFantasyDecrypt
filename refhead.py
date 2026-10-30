"""Identify which head sprite the reference render uses, by exact-colour footprint.

  python refhead.py [--ref 0] [--dir head|face|cap] [--top 10]

The body was confirmed as npc1000101, but head0101's hair colours are absent from the
reference, so some other head is worn. Ranking all heads by how many of their palette
colours land in the reference's head region finds the one actually used.
"""
import os
import sys
from collections import Counter

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402

REF = os.path.join(HERE, 'out', 'ref')
SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def flatten(path, nrec=10):
    """Return the first nrec pixel records of any DIMG variant (fixed grid or chain)."""
    d = open(path, 'rb').read()
    try:
        r = dimg.parse(d)
        if r.get('ok'):
            return [(w, h, bpp, px) for pre, w, h, px, bpp in r['frames'] if px]
    except Exception:
        pass
    try:
        import headtool
        recs, extra, k = headtool.segment(d)
        out = []
        for p, w, h, s, f in recs[:nrec]:
            out.append((w, h, s // w, p + 16))
        return out
    except Exception:
        return []


def main():
    args = sys.argv[1:]
    idx = int(args[args.index('--ref') + 1]) if '--ref' in args else 0
    top = int(args[args.index('--top') + 1]) if '--top' in args else 10
    sub = args[args.index('--dir') + 1] if '--dir' in args else 'head'
    name = ALL[idx]
    ref = np.asarray(Image.open(os.path.join(REF, name)).convert('RGB')).astype(np.int32)
    H = ref.shape[0]
    band = ref[:40]                     # head region only
    dirp = os.path.join(SRC, sub)
    files = sorted(n for n in os.listdir(dirp) if n.lower().endswith('.gsn'))
    scored = []
    for n in files:
        recs = flatten(os.path.join(dirp, n))
        if not recs:
            continue
        w, h, bpp, px = recs[0]
        d = open(os.path.join(dirp, n), 'rb').read()
        arr = np.asarray(dimg.to_image(d, px, w, h, bpp))
        a = arr.reshape(-1, 4)
        a = a[a[:, 3] > 40]
        pc = Counter(map(tuple, a[:, :3].tolist()))
        tot = sum(pc.values())
        hit = 0
        for rgb, cnt in pc.most_common(10):
            if cnt / tot < 0.02:
                continue
            n2 = int(np.all(band == np.array(rgb), axis=2).sum())
            hit += min(n2, cnt * 4)
        scored.append((hit, n, tot, len(pc)))
    scored.sort(reverse=True)
    print('ref %s (%dx%d), %s files=%d' % (esc(name), ref.shape[1], H, sub, len(files)))
    for hit, n, tot, nd in scored[:top]:
        print('   %-14s hit=%5d opaque=%4d distinct=%3d' % (esc(n), hit, tot, nd))


if __name__ == '__main__':
    main()
