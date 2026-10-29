# -*- coding: utf-8 -*-
"""Dump record prefixes and file tails under the "pattern last in record" model.

usage: python rec.py [file ...]
"""
import os
import sys

import validate as V

DEFAULT = ['npc59503.gsn', 'npc64402.gsn', 'npc64404.gsn', 'npc20406.gsn',
           'npc57101.gsn', 'npc57301.gsn']


def hexrow(d, o, n=16):
    return ' '.join(f'{b:02X}' for b in d[o:o + n])


def i32(d, o, k):
    return [V.u32(d, o + 4 * i) for i in range(k)]


def show(name):
    d = open(os.path.join(V.SRC, name), 'rb').read()
    f12 = V.u32(d, 12) & 0xffff
    pre = f12 - 12
    sigs = []
    o = 0
    while o + 16 <= len(d):
        w, h = V.u32(d, o), V.u32(d, o + 4)
        if 1 <= w <= 4096 and 1 <= h <= 4096 and V.u32(d, o + 8) == 2 * w \
                and V.u32(d, o + 12) == 1:
            sigs.append((o, w, h))
            o += 4
        else:
            o += 1
    # drop signatures whose pixel block cannot fit before the next signature
    keep = []
    for i, (p, w, h) in enumerate(sigs):
        nxt = sigs[i + 1][0] if i + 1 < len(sigs) else len(d)
        if p + 16 + 2 * w * h <= nxt + pre:
            keep.append((p, w, h))
    print('=' * 92)
    print(f'{name} size={len(d)} f12={f12} prefix={pre}B frames={V.u32(d,16)&0xffff} '
          f'dir={V.u32(d,20)&0xffff} patterns={len(sigs)} kept={len(keep)}')
    for i, (p, w, h) in enumerate(keep):
        st = p - pre
        tag = 'FIRST' if i == 0 else '     '
        print(f'  {tag} rec{i} prefix@{st}..{p-1} = {i32(d, st, pre // 4)}   '
              f'pat@{p}=({w}x{h}) px@{p+16}..{p+16+2*w*h-1}')
    last = keep[-1]
    end = last[0] + 16 + 2 * last[2] * last[1] if False else last[0] + 16 + 2 * last[1] * last[2]
    print(f'  --- H1 (pixel right after pattern) ends at {end}, file ends at {len(d)} '
          f'-> {len(d)-end} bytes after last pixel block')
    tail = max(0, len(d) - 96)
    print(f'  tail int32 @{tail}: {i32(d, tail, (len(d)-tail)//4)}')
    print(f'  tail hex   @{tail}: {hexrow(d, tail, 96)}')
    print(f'  preamble ext @24..{keep[0][0]-1}: {i32(d, 24, (keep[0][0]-24)//4)}')


if __name__ == '__main__':
    for n in (sys.argv[1:] or DEFAULT):
        if os.path.isfile(os.path.join(V.SRC, n)):
            show(n)
        else:
            print(f'{n}: MISSING')
