# -*- coding: utf-8 -*-
"""Find the "v2 descriptor" (w,h,x,y,w,1,h) through a whole file.

Fast prefilter: the pattern always contains the flag word == 1, i.e. the
bytes 01 00 00 00 at descriptor offset +20.  For every such position we
check if words (p-20..p+8) look like (w, h, x, y, w, 1, h).

usage: python scansig3.py <file> [max_hits]
"""
import os
import struct
import sys
import paths

SRC = paths.sub('data/official/avatar/npc')
FLAG = b'\x01\x00\x00\x00'


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    d = open(os.path.join(SRC, name), 'rb').read()
    n = len(d)
    print(f'### {name} size={n} header={[u32(d, o) for o in range(0, 24, 4)]}')
    hits = []
    p = d.find(FLAG)
    while p >= 0 and len(hits) < 4000:
        b = p - 20
        if b >= 24:
            w, h, x, y, w2, f, h2 = (u32(d, b + 4 * i) for i in range(7))
            if (w2 == w and f == 1 and h2 == h and 1 <= w <= 8192
                    and 1 <= h <= 8192):
                hits.append((b, w, h, x, y))
        p = d.find(FLAG, p + 4)
    print(f'v2 descriptors: {len(hits)}')
    prev = None
    for i, (b, w, h, x, y) in enumerate(hits[:limit]):
        gap = '' if prev is None else f' gap={b - prev}'
        print(f'   [{i}] @{b} {w}x{h} x={x} y={y} 2wh={2 * w * h}{gap}')
        prev = b
    if len(hits) > limit:
        gaps = {}
        for i in range(1, len(hits)):
            g = hits[i][0] - hits[i - 1][0]
            gaps[g] = gaps.get(g, 0) + 1
        print('   gap histogram (top 8):',
              sorted(gaps.items(), key=lambda kv: -kv[1])[:8])
        print('   last @', hits[-1][0], 'bytes after =', n - hits[-1][0])


if __name__ == '__main__':
    main()
