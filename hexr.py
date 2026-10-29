# -*- coding: utf-8 -*-
"""Show int32 view + hex rows for byte ranges of a .gsn file.

usage: python hexr.py <file> <off>:<len> [<off>:<len> ...]
       off may be negative (from EOF), e.g. -80:80
"""
import os
import struct
import sys

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'


def main():
    name = sys.argv[1]
    d = open(os.path.join(SRC, name), 'rb').read()
    size = len(d)
    print(f'### {name} size={size}')
    for spec in sys.argv[2:]:
        a, b = spec.split(':')
        off = int(a)
        ln = int(b)
        if off < 0:
            off = size + off
        end = min(off + ln, size)
        print(f'--- [{off}..{end}) len={end-off} ---')
        base = off - (off % 4)
        i = base
        while i < end:
            vals = []
            for k in range(i, min(i + 32, size), 4):
                vals.append(struct.unpack_from('<i', d, k)[0])
            mark = '<' if i <= off < i + 32 else ' '
            print(f'{mark}{i:>9} ' + ' '.join(f'{v:>11}' for v in vals))
            i += 32
        i = off - (off % 16)
        while i < end:
            row = d[i:min(i + 16, size)]
            print(f' {i:>9} ' + ' '.join(f'{x:02X}' for x in row))
            i += 16


if __name__ == '__main__':
    main()
