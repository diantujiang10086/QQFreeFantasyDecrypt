"""Probe colour families in the reference renders to guess which pixels are the character."""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'out', 'ref')


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def main():
    for n in sorted(os.listdir(REF)):
        if not n.endswith('.png'):
            continue
        a = np.asarray(Image.open(os.path.join(REF, n)).convert('RGB'), dtype=np.int16)
        R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        fams = {
            'blue': (B > R + 10),
            'warm': (R > B + 30) & (R > 120),
            'dark': (R + G + B < 300),
            'grey': (abs(R - G) < 12) & (abs(G - B) < 12) & (R > 150),
        }
        print(esc(n), a.shape)
        for nm, m in fams.items():
            ys, xs = np.nonzero(m)
            if len(xs):
                print('   %-5s n=%5d (%4.1f%%) bbox=(%d,%d)-(%d,%d)'
                      % (nm, len(xs), 100.0 * len(xs) / m.size, xs.min(), ys.min(), xs.max(), ys.max()))
            else:
                print('   %-5s none' % nm)


if __name__ == '__main__':
    main()
