# -*- coding: utf-8 -*-
"""Cheap library-wide census of the frame signature flag (= bpp/2).

The first frame's 16-byte signature always sits at `first_px - 16`, and
`first_px` is predicted by the version table, so one small read per file
tells us `(w, h, stride, flag)` for frame 0 of every .gsn.

    python flags.py [--csv out/plan.csv]
"""
import argparse
import csv
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='out/plan.csv')
    a = ap.parse_args()
    known = {}
    with open(a.csv, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['first_px']:
                known[row['file']] = (row['version'], int(row['first_px']))
    names = sorted(f for f in os.listdir(dimg.SRC) if f.endswith('.gsn'))
    cnt = Counter()
    odd = []
    four = []
    for name in names:
        p = os.path.join(dimg.SRC, name)
        with open(p, 'rb') as f:
            h = f.read(24)
        if len(h) < 24 or h[4:8] != b'DIMG':
            cnt['not DIMG'] += 1
            continue
        ver = f'{struct.unpack_from("<H", h, 8)[0]}.{struct.unpack_from("<H", h, 12)[0]}'
        fp = known.get(name, (ver, None))[1]
        if fp is None:
            fp = 24 + 4 * dimg.GET_START.get(ver, 0)
        with open(p, 'rb') as f:
            f.seek(fp - 16)
            raw = f.read(16)
        w, hh, s, fl = struct.unpack('<4I', raw)
        bpp = 2 * fl
        ok = (1 <= w <= 8192 and 1 <= hh <= 8192 and fl in (1, 2)
              and s == 2 * fl * w)
        cnt[(ver, fl, bpp, ok)] += 1
        if fl == 2:
            four.append((name, ver, w, hh, s, fl, ok))
        elif not ok:
            odd.append((name, ver, w, hh, s, fl))
    print(f'{len(names)} files')
    print(f'{"version":>10} {"flag":>4} {"bpp":>3} {"valid":>5}  count')
    for (ver, fl, bpp, ok), c in sorted(cnt.items(), key=lambda kv: -kv[1]):
        print(f'{ver:>10} {fl:>4} {bpp:>3} {str(ok):>5}  {c}')
    print(f'\nflag=2 (4 bytes per pixel) files: {len(four)}')
    for row in four:
        print('   ', row)
    if odd:
        print(f'\nunexpected first signature: {len(odd)}')
        for row in odd[:20]:
            print('   ', row)


if __name__ == '__main__':
    main()
