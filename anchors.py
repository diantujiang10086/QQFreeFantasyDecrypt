"""Dump the per-record prefix words of a pixel-less (anchor table) .gsn file.

    python anchors.py npc573201t [npc559201t ...] [--rows 12]

Anchor tables have no pixel data at all; the per-frame values live in the
24-byte (oh-16) record prefix.  This prints them as signed 32-bit decimals
plus the raw parse numbers so the layout can be cross-checked by hand.
"""
import os
import sys

import dimg

HERE = os.path.dirname(os.path.abspath(__file__))


def signed(x):
    return x - (1 << 32) if x >= (1 << 31) else x


def dump(name, rows):
    stem = name[:-4] if name.lower().endswith('.gsn') else name
    path = os.path.join(dimg.SRC, stem + '.gsn')
    with open(path, 'rb') as f:
        d = f.read()
    r = dimg.parse(d)
    print('=== %s  %d B' % (stem, len(d)))
    if not r['ok']:
        print('  PARSE FAILED:', ' ; '.join(r['tried'][:3]))
        return
    print('  ver %d.%d.%d  oh=%d first_px=%d end=%d tail=%d extra=%d' % (
        r['header']['major'], r['header']['minor'], r['header']['n_dirs'],
        r['oh'], r['first_px'], r['end'], r['tail'], r['extra']))
    print('  frames=%d skipped=%d bpp=%s dirs=%s method=%s' % (
        len(r['frames']), r['skipped'], r['bpps'], r['dir_counts'], r['method']))
    print('  dir_note=%r' % r.get('dir_note'))
    n = max(1, (r['oh'] - 16) // 4)
    hp = ['pre%d' % i for i in range(n)]
    print('  %-4s %-5s %-5s %s' % ('k', 'dir', 'px', ' '.join('%8s' % h for h in hp)))
    for i, (pre, w, hh, px, bpp) in enumerate(r['frames']):
        if i >= rows:
            print('  ... %d more records' % (len(r['frames']) - rows))
            break
        words = [signed(x) for x in dimg.prefix_words(d, pre, n)]
        print('  %-4d %-5d %-5s %s' % (i, 1, '-' if px is None else px,
                                       ' '.join('%8d' % v for v in words)))


def main():
    argv = sys.argv[1:]
    rows = 12
    if '--rows' in argv:
        j = argv.index('--rows')
        rows = int(argv[j + 1])
        del argv[j:j + 2]
    if not argv:
        print(__doc__)
        return
    for a in argv:
        dump(a, rows)


if __name__ == '__main__':
    main()
