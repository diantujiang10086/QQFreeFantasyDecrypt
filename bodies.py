"""Find headless bodies: sprites whose very top is a narrow stub (the neck).

A body that can take a head has a narrow protrusion at the top of its sprite;
a monster or a prop (a sword, a tree, a chest) starts wide or has no neck at
all.  We sample the npc folder and report the distribution of the top-row width
so we can pick a sensible cut-off.
"""
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mix   # noqa: E402


def topw(img):
    a = np.asarray(img)[:, :, 3] > 128
    ys = np.nonzero(a.any(axis=1))[0]
    if not len(ys):
        return None
    xs = np.nonzero(a[ys[0]])[0]
    return int(xs.max()) - int(xs.min()) + 1, int(xs.size), img.width, img.height


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    d = os.path.join(mix.SRC, 'npc')
    names = sorted(f[:-4] for f in os.listdir(d) if f.endswith('.gsn'))
    random.seed(7)
    pick = random.sample(names, min(n, len(names)))
    buckets = {}
    ok = 0
    rows = []
    for nm in pick:
        try:
            b = mix.body_frame(os.path.join(d, nm + '.gsn'), 0)
        except Exception:                      # noqa: BLE001
            continue
        if not b:
            continue
        t = topw(b['img'])
        if not t:
            continue
        w_top, npx, w, h = t
        ok += 1
        key = ('1-6' if w_top <= 6 else '7-10' if w_top <= 10 else
               '11-16' if w_top <= 16 else '17-24' if w_top <= 24 else '25+')
        buckets[key] = buckets.get(key, 0) + 1
        if w_top <= 10 and len(rows) < 25:
            rows.append((nm, w, h, w_top, npx))
    print('sampled %d, parsed %d' % (len(pick), ok))
    for k in ('1-6', '7-10', '11-16', '17-24', '25+'):
        print('  top width %-6s %4d' % (k, buckets.get(k, 0)))
    print('\nexamples with a narrow neck stub (top width <= 10):')
    for r in rows:
        print('  %-16s sprite %3dx%-3d  top run %2d px  (%d px in top row)'
              % (r[0], r[1], r[2], r[3], r[4]))


if __name__ == '__main__':
    main()
