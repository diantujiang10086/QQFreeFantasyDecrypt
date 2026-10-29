# -*- coding: utf-8 -*-
"""Show the last N bytes of a file as 12-byte groups (hex + int32).

usage: python tailview.py file [nbytes]
"""
import os
import struct
import sys

import validate as V


def main():
    name = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    d = open(os.path.join(V.SRC, name), 'rb').read()
    start = max(0, len(d) - n)
    print(f'{name} size={len(d)}  showing {start}..{len(d)}')
    o = start
    while o < len(d):
        chunk = d[o:o + 12]
        ints = []
        for k in range(0, len(chunk) - 3, 4):
            ints.append(struct.unpack_from('<i', chunk, k)[0])
        print(f'  @{o:>10} (mod12={o % 12:>2}) '
              f'{" ".join(f"{b:02X}" for b in chunk):<35} {ints}')
        o += 12


if __name__ == '__main__':
    main()
