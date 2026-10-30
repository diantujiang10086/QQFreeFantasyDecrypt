"""List head/*.gsn sprites by size, to find one matching a target silhouette."""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import headtool  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\head'


def sprites(path):
    d = open(path, 'rb').read()
    recs, extra, k = headtool.segment(d)
    out = []
    for p, w, h, s, f in recs:
        out.append((w, h, d[p + 16:p + 16 + s * h], s // w))
    return out


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else '27x40'
    W, H = (int(v) for v in want.split('x'))
    files = sorted(n for n in os.listdir(SRC) if n.endswith('.gsn'))
    rows = []
    for n in files:
        try:
            sp = sprites(os.path.join(SRC, n))
        except Exception as e:
            print('skip', n, e)
            continue
        w, h = sp[0][0], sp[0][1]
        rows.append((abs(w - W) + abs(h - H), n, [(a, b) for a, b, _, _ in sp]))
    rows.sort()
    for score, n, sizes in rows[:15]:
        print('%3d  %-12s %s' % (score, n, sizes))


if __name__ == '__main__':
    main()
