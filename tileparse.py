"""Validate the two tile containers' header/count model over every file.

    python tileparse.py            # summary
    python tileparse.py --list     # per-file table (ascii only)

.til      : magic "ELIT", u32@12 = entry count, each entry 128x128 RGBA = 65,536 B
tileimgNN : magic "QQ  TILE", u32@28 = entry count, each entry 64x64 RGBA = 16,384 B
"""
import glob
import os
import struct
import sys
from collections import Counter

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\tile'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tile_model.txt')

TIL_ENTRY = 128 * 128 * 4
IMG_ENTRY = 64 * 64 * 4


def main():
    lines = []
    rows = []
    # ---- .til
    hdrs = Counter()
    bad = []
    for p in sorted(glob.glob(os.path.join(ROOT, '*.til'))):
        d = open(p, 'rb').read(16)
        n = struct.unpack_from('<I', d, 12)[0]
        size = os.path.getsize(p)
        h = size - n * TIL_ENTRY
        hdrs[h] += 1
        if not (8 <= h <= 4096):
            bad.append((os.path.basename(p), size, n, h))
        rows.append(('til', os.path.basename(p), size, n, h))
    lines.append('### .til   files=%d' % len(rows))
    lines.append('header sizes: %s' % dict(hdrs))
    lines.append('out of range: %s' % (bad or 'none'))
    lines.append('')
    # ---- tileimgNN.dat
    hdrs2 = Counter()
    bad2 = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'tileimg*.dat'))):
        d = open(p, 'rb').read(32)
        n = struct.unpack_from('<I', d, 28)[0]
        size = os.path.getsize(p)
        h = size - n * IMG_ENTRY
        hdrs2[h] += 1
        if h != 64:
            bad2.append((os.path.basename(p), size, n, h))
        rows.append(('img', os.path.basename(p), size, n, h))
    lines.append('### tileimg*.dat   files=%d' % len([r for r in rows if r[0] == 'img']))
    lines.append('header sizes: %s' % dict(hdrs2))
    lines.append('not 64: %s' % (bad2 or 'none'))
    lines.append('')
    tot = sum(r[3] for r in rows)
    lines.append('total entries: %d  (til %d + img %d)'
                 % (tot, sum(r[3] for r in rows if r[0] == 'til'), sum(r[3] for r in rows if r[0] == 'img')))
    if '--list' in sys.argv:
        lines.append('')
        lines.append('%s %10s %8s %6s' % ('kind', 'size', 'entries', 'hdr'))
        for k, name, size, n, h in rows:
            lines.append('%s %10d %8d %6d  %s' % (k, size, n, h, name.encode('unicode_escape').decode('ascii')))
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    print('\n'.join(lines[:12]))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
