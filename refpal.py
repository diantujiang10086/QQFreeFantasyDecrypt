"""Check whether a reference render actually contains a given sprite, by exact colour footprint.

  python refpal.py [--ref 0]

Sprites use a small exact palette; if the reference was drawn from them, those exact RGB
values appear inside the character with the same relative layout. Prints each palette
colour's occurrence count and bbox in the reference.
"""
import os
import sys
from collections import Counter

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import combo     # noqa: E402
import paths

REF = os.path.join(HERE, 'out', 'ref')
SRC = paths.sub('data/official/avatar')
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def sprite(path, frame=0, head=False):
    if head:
        d, recs, r = combo.recursive_records(path)
        w, h, bpp, px = recs[frame]
    else:
        d = open(path, 'rb').read()
        r = dimg.parse(d)
        pre, w, h, px, bpp = r['frames'][frame]
    return np.asarray(dimg.to_image(d, px, w, h, bpp))


def palette(arr):
    a = arr.reshape(-1, 4)
    a = a[a[:, 3] > 40]
    return Counter(map(tuple, a[:, :3].tolist()))


def main():
    args = sys.argv[1:]
    idx = int(args[args.index('--ref') + 1]) if '--ref' in args else 0
    name = ALL[idx]
    ref = np.asarray(Image.open(os.path.join(REF, name)).convert('RGB')).astype(np.int32)
    print('ref', esc(name), ref.shape)
    for label, path, head in (
        ('body npc1000101', os.path.join(SRC, 'npc', 'npc1000101.gsn'), False),
        ('head head0101', os.path.join(SRC, 'head', 'head0101.gsn'), True),
    ):
        pc = palette(sprite(path, 0, head))
        total = sum(pc.values())
        print('== %s  distinct=%d opaque=%d' % (label, len(pc), total))
        hit_all = 0
        for rgb, cnt in pc.most_common(12):
            m = np.all(ref == np.array(rgb), axis=2)
            n = int(m.sum())
            hit_all += n
            ys, xs = np.nonzero(m)
            bb = '' if n == 0 else ' bbox=(%d,%d)-(%d,%d)' % (xs.min(), ys.min(), xs.max(), ys.max())
            print('   rgb=%-16s sprite=%4d (%.1f%%)  ref=%5d%s' % (str(rgb), cnt, 100.0 * cnt / total, n, bb))
        print('   top-12 colours found in ref: %d px' % hit_all)


if __name__ == '__main__':
    main()
