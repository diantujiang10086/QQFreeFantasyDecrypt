# -*- coding: utf-8 -*-
"""Diagnostic: show every frame signature and the implied record overhead.

For consecutive signatures p[i] -> p[i+1] the implied overhead is
    p[i+1] - p[i] - 2*w[i]*h[i]
which should equal the record overhead (oh).  Any change of value marks a
layout boundary.

usage: python diag.py file [max_hits]
"""
import os
import sys

import validate as V

SRC = V.SRC


def main():
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    d = open(os.path.join(SRC, name), 'rb').read()
    print(f'{name} size={len(d)} u16: ' + ' '.join(
        f'@{o}={V.u32(d,o)&0xffff}' for o in (8, 10, 12, 14, 16, 18, 20, 22)))
    sigs = []
    o = 0
    while o + 16 <= len(d):
        w, h = V.u32(d, o), V.u32(d, o + 4)
        if 1 <= w <= 8192 and 1 <= h <= 8192 and V.u32(d, o + 8) == 2 * w \
                and V.u32(d, o + 12) == 1:
            sigs.append((o, w, h))
            o += 4
        else:
            o += 1
    print(f'   {len(sigs)} signatures')
    prev = None
    for i, (p, w, h) in enumerate(sigs[:limit]):
        oh = '' if prev is None else f'{p - prev[0] - 2*prev[1]*prev[2]:>8}'
        print(f'  [{i:>3}] @{p:>10} {w:>4}x{h:<4} 2wh={2*w*h:>8} implied_oh={oh}')
        prev = (p, w, h)


if __name__ == '__main__':
    main()
