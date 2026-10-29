# -*- coding: utf-8 -*-
"""Correlate preamble word 0/1 with the record overhead `oh`.

Reads only the first 60 bytes of every .gsn, so it is cheap.

    python ohrule.py [--csv out/plan.csv]
"""
import argparse
import csv
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='out/plan.csv')
    a = ap.parse_args()
    known = {}
    with open(a.csv, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['status'] == 'ok' and row['oh']:
                known[row['file']] = (row['version'], int(row['oh']),
                                      row['first_px'])
    names = sorted(f for f in os.listdir(dimg.SRC) if f.endswith('.gsn'))
    print(f'{len(names)} files, {len(known)} with a known (version, oh)')
    tab = {}
    for name in names:
        p = os.path.join(dimg.SRC, name)
        with open(p, 'rb') as f:
            d = f.read(60)
        if len(d) < 60:
            continue
        w0, w1, w2 = (struct.unpack_from('<I', d, 24 + 4 * i)[0] for i in range(3))
        ver, oh, fp = known.get(name, ('?', 0, ''))
        tab.setdefault((w0, w1, ver, oh), 0)
        tab[(w0, w1, ver, oh)] += 1
    print(f'{"w0":>4} {"w1":>4} {"version":>12} {"oh":>4}  count')
    for (w0, w1, ver, oh), c in sorted(tab.items(), key=lambda kv: (-kv[1],)):
        print(f'{w0:>4} {w1:>4} {ver:>12} {oh:>4}  {c}')


if __name__ == '__main__':
    main()
