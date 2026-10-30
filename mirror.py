"""Are the 'mirrored' views literally the mirrored composites of the opposite view?"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'out', 'ref')
PAIRS = [('左', '右'), ('左上', '右上'), ('左下', '右下')]


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def grid(im):
    a = np.asarray(im.convert('RGB')).astype(np.int32)
    return (a % 17 == 0).all(axis=2), a


def main():
    for a, b in PAIRS:
        pa = os.path.join(REF, a + '.png')
        pb = os.path.join(REF, b + '.png')
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print('missing', esc(a), esc(b))
            continue
        ma, ca = grid(Image.open(pa))
        mb, cb = grid(Image.open(pb))
        ma_flip = ma[:, ::-1]
        inter = int((ma_flip & mb).sum())
        union = int((ma_flip | mb).sum())
        print('%s vs mirror(%s): mask IoU %.3f   px %d vs %d'
              % (esc(b), esc(a), inter / max(1, union), int(mb.sum()), int(ma.sum())))
        # best shift between flipped mask and b
        best = (0, 0, 0)
        H, W = mb.shape
        for dy in range(-4, 5):
            for dx in range(-6, 7):
                sh = np.zeros_like(ma_flip)
                ys0, ys1 = max(0, dy), min(H, H + dy)
                xs0, xs1 = max(0, dx), min(W, W + dx)
                sh[ys0:ys1, xs0:xs1] = ma_flip[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
                i2 = int((sh & mb).sum())
                if i2 > best[0]:
                    best = (i2, dx, dy)
        print('   best shifted overlap %d (dx %d, dy %d) -> IoU %.3f'
              % (best[0], best[1], best[2], best[0] / max(1, int((mb | ma).sum()))))


if __name__ == '__main__':
    main()
