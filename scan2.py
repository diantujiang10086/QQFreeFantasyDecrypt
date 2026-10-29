# -*- coding: utf-8 -*-
"""Scan signatures (w, h, 2*w, flag) for flag in 1..4.

usage: python scan2.py [file ...]
"""
import os
import sys

import validate as V

FILES = ['npc64401.gsn', 'npc64403.gsn', 'npc64501.gsn', 'npc108905.gsn',
         'npc174501.gsn', 'npc57101.gsn', 'npc64404.gsn']


def main():
    for name in (sys.argv[1:] or FILES):
        p = os.path.join(V.SRC, name)
        if not os.path.isfile(p):
            print(f'{name}: MISSING')
            continue
        d = open(p, 'rb').read()
        f12 = V.u32(d, 12) & 0xffff
        print('=' * 92)
        print(f'{name} size={len(d)} f12={f12} frames={V.u32(d,16)&0xffff} '
              f'dir={V.u32(d,20)&0xffff}')
        hits = []
        o = 0
        while o + 16 <= len(d):
            w, h = V.u32(d, o), V.u32(d, o + 4)
            f = V.u32(d, o + 12)
            if 1 <= w <= 4096 and 1 <= h <= 4096 and V.u32(d, o + 8) == 2 * w \
                    and 1 <= f <= 4:
                hits.append((o, w, h, f))
                o += 4
            else:
                o += 1
        print(f'  {len(hits)} hits (flag 1..4)')
        for o, w, h, f in hits[:30]:
            print(f'   @{o:>9} ({w:>4}x{h:<4}) 2w={2*w:<5} flag={f} '
                  f'bytes_after_px={len(d)-o-16-2*w*h}')
        if len(hits) > 30:
            print(f'   ... {len(hits)-30} more')


if __name__ == '__main__':
    main()
