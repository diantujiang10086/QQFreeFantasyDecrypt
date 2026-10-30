"""Backpack geometry stats: pivot sanity, canvas vs sprite size, direction coverage."""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\backpack'


def main():
    rows = []
    for nm in sorted(f for f in os.listdir(SRC) if f.lower().endswith('.gsn')):
        d = open(os.path.join(SRC, nm), 'rb').read()
        pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
        recs, extra, k = headtool.segment(d)
        W, H, cx, cy = pw[3], pw[4], pw[5], pw[6]
        rows.append((nm[:-4], len(recs), W, H, cx, cy))
    neg = [(n, x, y) for n, r, W, H, x, y in rows if x > 2 ** 31 or y > 2 ** 31]
    print('pivot with sign bit set (interpreted as negative):', len(neg))
    for n, x, y in neg[:10]:
        print('   %-16s (%d, %d)' % (n, x - 2 ** 32, y - 2 ** 32))
    outside = [(n, W, H, x, y) for n, r, W, H, x, y in rows
               if x <= 2 ** 31 and y <= 2 ** 31 and (x > W or y > H)]
    print('pivot outside canvas (unsigned values):', len(outside))
    for t in outside[:10]:
        print('   %-16s canvas=%dx%d pivot=(%d,%d)' % t)
    ratio = [(n, y / H) for n, r, W, H, x, y in rows if y and y < 2 ** 31]
    print('cy/H: min %.2f  median %.2f  max %.2f'
          % (min(r for _n, r in ratio), sorted(r for _n, r in ratio)[len(ratio) // 2], max(r for _n, r in ratio)))
    cnt = collections.Counter(r for _n, r, _W, _H, _x, _y in rows)
    print('records histogram:', dict(sorted(cnt.items())))
    # direction-count consistency: is every file a multiple of 5?
    bad = [n for n, r, _W, _H, _x, _y in rows if r % 5]
    print('files whose record count is not a multiple of 5:', bad)


if __name__ == '__main__':
    main()
