"""What is left in the render after the body is placed? (colour histogram + ascii of the leftover)"""
import collections
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
REF = os.path.join(HERE, 'out', 'ref')
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))
RAMP = ' .:-=+*#%@'


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def main():
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    idx = int(opt('--ref', 0))
    stem = opt('--body', 'npc1000101')
    bf = int(opt('--frame', 4))
    bx, by = (int(v) for v in opt('--at', '26,30').split(','))
    im = Image.open(os.path.join(REF, ALL[idx]))
    a3 = np.asarray(im.convert('RGB')).astype(np.int32)
    mask = (a3 % 17 == 0).all(axis=2)
    d = open(os.path.join(SRC, 'npc', stem + '.gsn'), 'rb').read()
    r = dimg.parse(d)
    pre, w, h, px, bpp = r['frames'][bf]
    body = dimg.to_image(d, px, w, h, bpp).convert('RGBA')
    ba = np.asarray(body)[:, :, 3] > 128
    claim = np.zeros_like(mask)
    claim[by:by + h, bx:bx + w] |= ba
    left = mask & ~claim
    print('ref %-8s  sprite px %d  body px %d  leftover %d'
          % (esc(ALL[idx]), int(mask.sum()), int(claim.sum()), int(left.sum())))
    ys, xs = np.nonzero(left)
    print('leftover bbox x %d..%d y %d..%d' % (xs.min(), xs.max(), ys.min(), ys.max()))
    c = collections.Counter(tuple(int(v) for v in a3[y, x]) for y, x in zip(ys, xs))
    print('leftover colours:', len(c))
    for col, n in c.most_common(12):
        print('   %-18s %d' % (str(col), n))

    # ascii of the leftover, rows 0..60
    sub = left[0:60]
    print('\nleftover ascii (rows 0..59, 1 char = 1 px, x 20..75):')
    for y in range(sub.shape[0]):
        row = ''.join('#' if sub[y, x] else '.' for x in range(20, min(76, sub.shape[1])))
        print('%3d %s' % (y, row))

    # the same histogram for the candidate head colour record
    hd = opt('--head', 'head0251')
    hi = int(opt('--hidx', 8))
    dh = open(os.path.join(SRC, 'head', hd + '.gsn'), 'rb').read()
    recs, extra, k = headtool.segment(dh)
    p, hw, hh, s, f = recs[hi]
    spr = np.asarray(dimg.to_image(dh, p + 16, hw, hh, s // w).convert('RGB')).astype(np.int32)
    al = np.asarray(dimg.to_image(dh, p + 16, hw, hh, s // w).convert('RGBA'))[:, :, 3] > 128
    c2 = collections.Counter(tuple(int(v) for v in spr[y, x]) for y in range(hh) for x in range(hw) if al[y, x])
    print('\n%s rec %d colours %d:' % (hd, hi, len(c2)))
    for col, n in c2.most_common(12):
        print('   %-18s %d' % (str(col), n))
    inter = set(c) & set(c2)
    print('shared colours: %d  (leftover px in shared: %d)'
          % (len(inter), sum(n for col, n in c.items() if col in inter)))


if __name__ == '__main__':
    main()
