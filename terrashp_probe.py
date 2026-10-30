"""terrashp*.dat probe: RA YSTRSP header + 544 fixed 1044-byte records.

Record layout (verified on all 14 files):
    u32 x, u32 y, u32 kind, u32 n, u32 zero   followed by n groups of
    '4 identical u32' (a 2x2 cells of one tile block, presumably a shape index).

Usage:
    python terrashp_probe.py                 # summary + first records
    python terrashp_probe.py --rec 300       # dump one record
    python terrashp_probe.py --csv out/terrashp.csv
"""
import argparse
import collections
import glob
import os

import numpy as np
import paths

ROOT = paths.sub('data/official/tile')
HDR = 48
REC = 261          # u32 per record == 1044 bytes


def load(path=None):
    path = path or os.path.join(ROOT, 'terrashp.dat')
    d = open(path, 'rb').read()
    a = np.frombuffer(d[HDR:], dtype='<u4')
    return path, a.reshape(-1, REC)


def record(rec):
    x, y, kind, n = (int(v) for v in rec[:4])
    body = rec[5:]
    q = body[:(len(body) // 4) * 4].reshape(-1, 4)
    keep = [i for i in range(len(q)) if q[i].any()]
    q = q[:keep[-1] + 1] if keep else q[:0]
    flat = [int(v) for v in q[:, 0]]
    return {'x': x, 'y': y, 'kind': kind, 'n': n, 'groups': flat,
            'lanes_equal': bool(len(q) == 0 or ((q[:, 0] == q[:, 1]) & (q[:, 0] == q[:, 2]) & (q[:, 0] == q[:, 3])).all())}


def summary(a):
    print('records', len(a), 'x', REC, 'u32 each')
    kinds = collections.Counter()
    lens = collections.Counter()
    nlanes = 0
    vals = []
    for rec in a:
        r = record(rec)
        kinds[r['kind']] += 1
        lens[len(r['groups'])] += 1
        nlanes += r['lanes_equal']
        vals.extend(r['groups'])
    print('kind histogram', sorted(kinds.items()))
    print('payload group count histogram', sorted(lens.items()))
    print('records whose 4 lanes are identical', nlanes, '/', len(a))
    print('payload value range', min(vals), '..', max(vals), 'sample', sorted(set(vals))[:16])
    for i in (0, 1, 100, 300, 543):
        if i < len(a):
            r = record(a[i])
            print('rec %3d  x=%-10d y=%-10d kind=%-3d n=%-2d groups=%s'
                  % (i, r['x'], r['y'], r['kind'], r['n'], r['groups'][:10]))


def dump(a, i):
    r = record(a[i])
    print('rec', i, 'x', r['x'], 'y', r['y'], 'kind', r['kind'], 'n', r['n'],
          'lanes_equal', r['lanes_equal'])
    print('groups', r['groups'])


def csv_out(a, path):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('rec,x,y,kind,n,groups\n')
        for i, rec in enumerate(a):
            r = record(rec)
            fh.write('%d,%d,%d,%d,%d,%s\n'
                     % (i, r['x'], r['y'], r['kind'], r['n'],
                        ' '.join(str(v) for v in r['groups'])))
    print('csv ->', path)


def files():
    return sorted(glob.glob(os.path.join(ROOT, 'terrashp*.dat')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rec', type=int)
    ap.add_argument('--csv')
    ap.add_argument('--all', action='store_true', help='every terrashpNN.dat')
    a = ap.parse_args()
    paths = files() if a.all else [os.path.join(ROOT, 'terrashp.dat')]
    for p in paths:
        print('===', os.path.basename(p))
        _, arr = load(p)
        if a.rec is not None:
            dump(arr, a.rec)
        else:
            summary(arr)
        if a.csv:
            csv_out(arr, a.csv if len(paths) == 1 else a.csv.replace('.csv', '_%s.csv' % os.path.basename(p)[:-4]))


if __name__ == '__main__':
    main()
