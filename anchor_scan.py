"""Summarise every anchor-only table (35 files): record prefix words."""
import csv
import os

import dimg

HERE = os.path.dirname(os.path.abspath(__file__))


def signed(x):
    return x - (1 << 32) if x >= (1 << 31) else x


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, 'out', 'plan.csv'),
                                   newline='', encoding='utf-8')))
    names = [r['file'] for r in rows
             if r['status'] == 'ok' and int(r['skipped']) == int(r['frames']) and int(r['frames'])]
    print('anchor-only files:', len(names))
    w5 = {}
    for f in names:
        with open(os.path.join(dimg.SRC, f), 'rb') as fh:
            d = fh.read()
        r = dimg.parse(d)
        n = max(1, (r['oh'] - 16) // 4)
        pre = r['frames'][0][0]
        w0 = [signed(x) for x in dimg.prefix_words(d, pre, n)]
        pre1 = r['frames'][1][0] if len(r['frames']) > 1 else pre
        w1 = [signed(x) for x in dimg.prefix_words(d, pre1, n)]
        key = w0[-1]
        w5[key] = w5.get(key, 0) + 1
        print('%-14s %4d rec  oh=%d w0=%s' % (f[:-4], len(r['frames']), r['oh'], w0))
        if w1 != w0:
            print('%-14s           2nd=%s' % ('', w1))
    print('last-word histogram:', w5)


if __name__ == '__main__':
    main()
