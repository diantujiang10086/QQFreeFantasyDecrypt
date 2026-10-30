"""ASCII preview of a composite: body / head / merged, one char per 2 px."""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mix   # noqa: E402

RAMP = ' .:-=+*#%@'


def show(im, w=40):
    a = np.asarray(im)
    h, ww = a.shape[:2]
    sc = max(1, int(np.ceil(max(h, ww) / float(w))))
    hr, wr = h // sc, ww // sc
    al = a[:, :, 3].astype(np.float64)
    lum = (0.3 * a[:, :, 0] + 0.59 * a[:, :, 1] + 0.11 * a[:, :, 2]).astype(np.float64)
    out = []
    for y in range(hr):
        row = []
        for x in range(wr):
            blk = al[y * sc:(y + 1) * sc, x * sc:(x + 1) * sc]
            lb = lum[y * sc:(y + 1) * sc, x * sc:(x + 1) * sc]
            if blk.mean() < 40:
                row.append(' ')
                continue
            v = min(len(RAMP) - 1, int(lb.mean() / 25.6))
            row.append(RAMP[v])
        out.append(''.join(row))
    return '\n'.join(out)


def main():
    names = sys.argv[1:] or ['npc1000101_head2151_d1.png']
    for n in names:
        p = os.path.join(mix.OUT, 'mix', n)
        im = Image.open(p)
        print('== %s  %dx%d' % (n, im.width, im.height))
        print(show(im))
        print()


if __name__ == '__main__':
    main()
