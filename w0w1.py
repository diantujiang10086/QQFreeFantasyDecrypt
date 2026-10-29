# -*- coding: utf-8 -*-
"""Check whether preamble word 1 is a copy of nDirs (header u16@20).

For each (word0, word1) group found in the library, print a few samples
with the file header's own nDirs field next to it, plus the oh that the
parser actually used.

    python w0w1.py [--per-group 3]
"""
import argparse
import csv
import os
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='out/plan.csv')
    ap.add_argument('--per-group', type=int, default=3)
    a = ap.parse_args()
    known = {}
    with open(a.csv, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            known[row['file']] = row
    names = sorted(f for f in os.listdir(dimg.SRC) if f.endswith('.gsn'))
    seen = defaultdict(list)
    for name in names:
        p = os.path.join(dimg.SRC, name)
        with open(p, 'rb') as f:
            d = f.read(100)
        if len(d) < 100 or d[4:8] != b'DIMG':
            continue
        u16 = lambda o: struct.unpack_from('<H', d, o)[0]      # noqa: E731
        u32 = lambda o: struct.unpack_from('<I', d, o)[0]      # noqa: E731
        key = (u32(24), u32(28), u16(20))     # w0, w1, header nDirs
        row = known.get(name, {})
        seen[key].append((name, row.get('version', '?'), row.get('oh', '?'),
                          row.get('status', '?')))
    print(f'{"w0":>4} {"w1":>4} {"hdrNDirs":>8} {"files":>6}   samples')
    for key, rows in sorted(seen.items(), key=lambda kv: -len(kv[1])):
        w0, w1, nd = key
        ex = ', '.join(f'{r[0]}(v{r[1]},oh={r[2]},{r[3]})'
                       for r in rows[:a.per_group])
        print(f'{w0:>4} {w1:>4} {nd:>8} {len(rows):>6}   {ex}')


if __name__ == '__main__':
    main()
