"""avat ar 子目录的解析普查：dimg.parse -> 失败再退 headtool.chain。

    python avacensus.py cap face weaponl weaponr
    python avacensus.py --csv out\\ava.csv cap
"""
import os
import sys
import csv
import collections

import dimg
import headtool
import paths

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRCROOT = paths.sub('data/official/avatar')


def one(folder, path):
    d = open(path, 'rb').read()
    size = len(d)
    r = dimg.parse(d, brute=False)
    method = 'dimg'
    if not r['ok']:
        r = dimg.parse(d, brute=True)
        method = 'dimg+brute'
    if r['ok']:
        return dict(file=os.path.basename(path), folder=folder, size=size, ok=1,
                    method=method, tag=r.get('tag'), oh=r.get('oh'),
                    first_px=r.get('first_px'), frames=len(r['frames']),
                    dirs='|'.join(str(x) for x in (r.get('dir_counts') or [])),
                    extra=r.get('extra'), bpp=r.get('bpp'), err='')
    # 退 headtool 搜链
    try:
        h = dimg.head(d)
        recs, tx, k = headtool.segment(d)
        return dict(file=os.path.basename(path), folder=folder, size=size, ok=2,
                    method='chain', tag='%d.%d' % (h['major'], h['minor']),
                    oh='', first_px='', frames=len(recs), dirs='tx=%d' % tx,
                    extra='', bpp=collections.Counter(
                        x[3] // x[1] for x in recs).most_common(1)[0][0], err='')
    except Exception as e:
        return dict(file=os.path.basename(path), folder=folder, size=size, ok=0,
                    method='-', tag='', oh='', first_px='', frames='',
                    dirs='', extra='', bpp='', err='%s: %s' % (type(e).__name__, e))


def main():
    args = sys.argv[1:]
    rows = []
    csv_path = None
    if '--csv' in args:
        i = args.index('--csv')
        csv_path = args[i + 1]
        del args[i:i + 2]
    for folder in args:
        d = os.path.join(SRCROOT, folder)
        names = sorted(f for f in os.listdir(d) if f.lower().endswith('.gsn'))
        print('=== %s: %d .gsn' % (folder, len(names)), flush=True)
        stat = collections.Counter()
        ohs = collections.Counter()
        pats = collections.Counter()
        for n, f in enumerate(names):
            r = one(folder, os.path.join(d, f))
            rows.append(r)
            stat[r['method']] += 1
            if r['ok'] == 1:
                ohs[r['oh']] += 1
                pats[r['dirs']] += 1
            if r['ok'] == 0:
                print('  FAIL %s %s' % (f, r['err']), flush=True)
            if (n + 1) % 1000 == 0:
                print('  ...%d/%d' % (n + 1, len(names)), flush=True)
        print('  methods:', dict(stat), flush=True)
        print('  oh:', dict(sorted(ohs.items())), flush=True)
        print('  dir patterns (%d):' % len(pats), flush=True)
        for k, v in pats.most_common(12):
            print('    %-28s %d' % (k, v), flush=True)

    if csv_path:
        os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print('csv ->', csv_path, len(rows), 'rows')


if __name__ == '__main__':
    main()
