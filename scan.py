# -*- coding: utf-8 -*-
"""List every occurrence of the frame record signature (w, h, 2*w, 1).

usage: python scan.py [file ...]
"""
import os
import sys

import validate as V

DEFAULT = ['npc59503.gsn', 'npc57101.gsn', 'npc57301.gsn', 'npc64402.gsn',
           'npc64404.gsn', 'npc20406.gsn', 'npc64501.gsn', 'npc61401.gsn',
           'npc559201.gsn', 'npc559201t.gsn']


def scan(d):
    n = len(d)
    out = []
    o = 0
    while o + 16 <= n:
        w = V.u32(d, o)
        h = V.u32(d, o + 4)
        if 1 <= w <= 4096 and 1 <= h <= 4096 and V.u32(d, o + 8) == 2 * w \
                and V.u32(d, o + 12) == 1:
            out.append((o, w, h))
            o += 4
        else:
            o += 1
    return out


def main():
    for name in (sys.argv[1:] or DEFAULT):
        p = os.path.join(V.SRC, name)
        if not os.path.isfile(p):
            print(f'{name}: MISSING')
            continue
        d = open(p, 'rb').read()
        sigs = scan(d)
        print('=' * 90)
        print(f'{name} size={len(d)} u16@12={V.u32(d,12)&0xffff} '
              f'u16@16={V.u32(d,16)&0xffff} u16@20={V.u32(d,20)&0xffff} '
              f'patterns={len(sigs)}')
        for o, w, h in sigs[:40]:
            print(f'   @{o:>9} ({w:>5}x{h:<5}) 2w={2*w:<6} align4={o % 4 == 0} '
                  f'bytes_left={len(d)-o-16-2*w*h}')
        if len(sigs) > 40:
            print(f'   ... {len(sigs)-40} more')


if __name__ == '__main__':
    main()
