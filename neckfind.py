"""Show the opaque x-runs of the first rows of each body frame.

Goal: find out what the head anchor is really attached to.  The five
calibrated frames of npc1000101 imply these head-pivot positions in
sprite-local coordinates (head2151 pivot = 20,28):

    f0 -> x 31   f1 -> x 24   f2 -> x 36   f3 -> x 29   f4 -> x 23

If one of the protrusions below sits at those x values, that protrusion is
the anchor (and the rule can use it instead of "topmost row centre").
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mix   # noqa: E402

WANT = {0: 31, 1: 24, 2: 36, 3: 29, 4: 23}


def runs(row):
    xs = np.nonzero(row)[0]
    if len(xs) == 0:
        return []
    out = []
    s = p = int(xs[0])
    for x in xs[1:]:
        x = int(x)
        if x != p + 1:
            out.append((s, p))
            s = x
        p = x
    out.append((s, p))
    return out


def main():
    bp = os.path.join(mix.SRC, 'npc', 'npc1000101.gsn')
    for fr in range(5):
        b = mix.body_frame(bp, fr)
        a = np.asarray(b['img'])[:, :, 3] > 128
        print('\n--- frame %d  sprite %dx%d   want head-pivot x = %d'
              % (fr, b['img'].width, b['img'].height, WANT[fr]))
        ys = np.nonzero(a.any(axis=1))[0]
        for y in range(int(ys[0]), min(int(ys[0]) + 14, a.shape[0])):
            rr = runs(a[y])
            tag = ''.join(' [%d..%d]' % r for r in rr)
            print('  y=%-3d %s' % (y, tag))


if __name__ == '__main__':
    main()
