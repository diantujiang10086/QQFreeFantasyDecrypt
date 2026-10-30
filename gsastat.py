"""Aggregate out/gsa.csv by top-level sub-directory of official\\res."""
import collections
import csv
import os

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'gsa.csv')


def main():
    rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
    agg = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        top = r['file'].replace('\\', '/').split('/')[0]
        a = agg[top]
        a[0] += 1
        a[1] += int(r['size'] or 0)
        a[2] += int(r['frames'] or 0)
        a[3] += int(r['tiles'] or 0)
    print('%-14s %6s %10s %8s %8s %8s' % ('subdir', 'files', 'MB', 'frames', 'tiles', 'avg f'))
    tot = [0, 0, 0, 0]
    for k in sorted(agg, key=lambda t: -agg[t][1]):
        v = agg[k]
        for i in range(4):
            tot[i] += v[i]
        print('%-14s %6d %10.2f %8d %8d %8.2f' % (k, v[0], v[1] / 1048576, v[2], v[3], v[2] / v[0]))
    print('%-14s %6d %10.2f %8d %8d %8.2f' % ('TOTAL', tot[0], tot[1] / 1048576, tot[2], tot[3], tot[2] / tot[0]))
    print()
    multi = [r for r in rows if int(r['frames'] or 0) > 1]
    print('files with >1 frame:', len(multi), ' max frames:', max(int(r['frames']) for r in rows))
    tiles = [r for r in rows if int(r['tiles'] or 0) > int(r['frames'] or 1)]
    print('files stored as multiple tiles per frame:', len(tiles))
    for r in sorted(tiles, key=lambda r: -int(r['tiles']))[:8]:
        print('   %-46s %-9s %4sx%-4s frames %-3s tiles %s'
              % (r['file'], r['size'], r['w'], r['h'], r['frames'], r['tiles']))


if __name__ == '__main__':
    main()
