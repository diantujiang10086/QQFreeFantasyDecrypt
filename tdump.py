# -*- coding: utf-8 -*-
"""带绝对偏移的尾部 hexdump：python tdump.py <file> [nbytes]"""
import sys, os
import dimg

p = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
if not os.path.isabs(p):
    p = os.path.join(dimg.SRC, p)
d = open(p, 'rb').read()
start = max(0, len(d) - n)
start -= start % 16
for o in range(start, len(d), 16):
    chunk = d[o:o + 16]
    hexs = ' '.join(f'{b:02x}' for b in chunk)
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print(f'{o:9d} (+{o - (len(d) - n):5d})  {hexs:<47}  {asc}')
print(f'size={len(d)}')
