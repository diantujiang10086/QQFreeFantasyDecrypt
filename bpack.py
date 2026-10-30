"""Parse and export avatar/backpack sprites (same container as head/npc)."""
import collections
import json
import os
import struct
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402
import paths

SRC = paths.sub('data/official/avatar/backpack')
OUT = os.path.join(HERE, 'out')
DST = os.path.join(OUT, 'backpack')


def hdr(b):
    major, u10, minor = struct.unpack_from('<3H', b, 8)
    n1, n2, n3 = struct.unpack_from('<3H', b, 16)
    return major, u10, minor, n1, n2, n3


def info(path):
    d = open(path, 'rb').read()
    major, u10, minor, n1, n2, n3 = hdr(d)
    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    n_dirs = struct.unpack_from('<H', d, 16)[0]
    recs, extra, k = headtool.segment(d) if hasattr(headtool, 'segment') else (None, None, None)
    return dict(size=len(d), ver='%d.%d' % (major, minor), u10=u10,
                n1=n1, n2=n2, n3=n3, pw=pw, W=pw[3], H=pw[4], cx=pw[5], cy=pw[6],
                n_dirs=n_dirs, recs=recs, extra=extra, k=k, data=d)


def rec_pixels(path, idx):
    d = open(path, 'rb').read()
    recs, extra, k = headtool.segment(d)
    p, w, h, stride, flag = recs[idx]
    bpp = stride // w
    return dimg.to_image(d, p + 16, w, h, bpp), (w, h, bpp, p)


def main():
    a = sys.argv[1:]
    names = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.gsn'))
    if '--png' in a:
        os.makedirs(DST, exist_ok=True)
        made = 0
        for nm in names:
            stem = nm[:-4]
            d = open(os.path.join(SRC, nm), 'rb').read()
            recs, extra, k = headtool.segment(d)
            if not recs:
                print('%-22s no chain' % stem)
                continue
            n = len(recs)
            f = n // 5 if n % 5 == 0 else 1   # frames per direction
            sub = os.path.join(DST, stem)
            os.makedirs(sub, exist_ok=True)
            for i, (p, w, h, stride, flag) in enumerate(recs):
                bpp = stride // w
                im = dimg.to_image(d, p + 16, w, h, bpp)
                im.save(os.path.join(sub, 'd%d_%02d.png' % (i // f + 1, i % f)))
                made += 1
        print('png %d -> %s' % (made, DST))
        return
    rows = []
    for nm in names:
        r = info(os.path.join(SRC, nm))
        if not r['recs']:
            print('%-22s %8d  no chain' % (nm[:-4], r['size']))
            continue
        sizes = ' '.join('%dx%d' % (w, h) for _p, w, h, _s, _f in r['recs'])
        rows.append((nm[:-4], r['size'], r['ver'], r['n_dirs'], r['k'], r['extra'],
                     r['W'], r['H'], r['cx'], r['cy'], sizes))
        print('%-16s %8d v%-7s ndirs=%-3d recs=%-3d extra=%-4d canvas=%dx%d pivot=(%d,%d)  %s'
              % (nm[:-4], r['size'], r['ver'], r['n_dirs'], r['k'], r['extra'],
                 r['W'], r['H'], r['cx'], r['cy'], sizes))
    c = collections.Counter(r[4] for r in rows)
    print('\nrecords per file:', dict(c))
    c2 = collections.Counter(r[3] for r in rows)
    print('header n_dirs:', dict(c2))
    print('canvas WxH: most common', collections.Counter((r[6], r[7]) for r in rows).most_common(10))
    with open(os.path.join(OUT, 'backpack.csv'), 'w', encoding='utf-8') as fh:
        fh.write('file,size,ver,n_dirs,records,tail_extra,W,H,cx,cy,sizes\n')
        for r in rows:
            fh.write(','.join(str(x) for x in r) + '\n')


if __name__ == '__main__':
    main()
