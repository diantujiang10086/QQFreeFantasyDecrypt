"""Scan tileimg*.dat entries: report solid-colour entries and texture entries.

Also cross-references tilebase*.ini colour ids (name + RGB).
"""
import glob
import os
import re
import struct
from collections import Counter

import numpy as np
import paths

ROOT = paths.sub('data/official/tile')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tileimg_scan.txt')
ENTRY = 64 * 64 * 4


def tilebase(ini, lines):
    p = os.path.join(ROOT, ini)
    if not os.path.exists(p):
        return []
    t = open(p, 'rb').read().decode('gbk', 'replace')
    out = []
    for line in t.splitlines():
        m = re.match(r'\s*(\d+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$', line)
        if m:
            out.append((int(m.group(1)), m.group(2), (int(m.group(3)), int(m.group(4)), int(m.group(5)))))
    lines.append('%s: %d colour ids' % (ini, len(out)))
    return out


def main():
    lines = []
    base = tilebase('tilebase.ini', lines)
    base_by_rgb = {v[2]: v for v in base}
    for p in sorted(glob.glob(os.path.join(ROOT, 'tileimg*.dat'))):
        d = open(p, 'rb').read()
        n = struct.unpack_from('<I', d, 28)[0]
        solid = []
        textured = 0
        for k in range(n):
            a = np.frombuffer(d, np.uint8, ENTRY, 64 + k * ENTRY).reshape(64, 64, 4)
            rgb = a[:, :, :3]
            if (rgb == rgb[0, 0]).all() and (a[:, :, 3] == 255).all():
                b, g, r = int(rgb[0, 0, 0]), int(rgb[0, 0, 1]), int(rgb[0, 0, 2])
                hit = base_by_rgb.get((r, g, b))
                solid.append((k, (r, g, b), hit[1].encode('unicode_escape').decode('ascii') if hit else ''))
            else:
                textured += 1
        lines.append('=' * 70)
        lines.append('%s  entries %d  solid %d  textured %d'
                     % (os.path.basename(p).encode('unicode_escape').decode('ascii'), n, len(solid), textured))
        for k, rgb, name in solid[:40]:
            lines.append('   #%-4d solid rgb=%-16s %s' % (k, rgb, name))
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    print('\n'.join(lines[:6]))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
