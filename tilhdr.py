"""Dump .til headers (first 640 bytes) as u32 rows for header-size analysis."""
import glob
import os
import struct

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\tile'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tile_hdr.txt')


def main():
    files = sorted(glob.glob(os.path.join(ROOT, '*.til')))
    seen = {}
    lines = []
    for p in files:
        d = open(p, 'rb').read(640)
        n = struct.unpack_from('<I', d, 12)[0]
        h = os.path.getsize(p) - n * 65536
        if h in seen:
            continue
        seen[h] = p
        lines.append('=' * 72)
        lines.append('hdr=%d  n=%d  file=#%d' % (h, n, files.index(p)))
        for i in range(0, min(640, h + 32), 32):
            u = struct.unpack_from('<8I', d, i)
            lines.append('  @%4d  %s' % (i, ' '.join('%9d' % v for v in u)))
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    print('wrote', OUT, 'header variants', sorted(seen))


if __name__ == '__main__':
    main()
