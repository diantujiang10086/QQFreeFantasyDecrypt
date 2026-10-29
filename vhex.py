# -*- coding: utf-8 -*-
"""Head/tail hex dump for comparing file layouts.

    python vhex.py <file> [--head N] [--tail N]
"""
import sys

def dump(d, off, n, label):
    print(f'   {label} @{off:,}:')
    b = d[off:off + n]
    for i in range(0, len(b), 16):
        row = b[i:i + 16]
        hx = ' '.join(f'{x:02X}' for x in row)
        asc = ''.join(chr(x) if 32 <= x < 127 else '.' for x in row)
        print(f'     {off + i:>10,}  {hx:<47}  {asc}')

def show(path, headn=112, tailn=96, words=True):
    import struct
    d = open(path, 'rb').read()
    name = path.split('\\')[-1]
    nf = struct.unpack_from('<H', d, 16)[0]
    nd = struct.unpack_from('<H', d, 20)[0]
    print(f'== {name} size={len(d):,} frames={nf} dirs={nd}')
    w = [struct.unpack_from('<I', d, o)[0] for o in range(24, 24 + 4 * 19, 4)]
    print('   words @24: ' + ' '.join(str(x) for x in w))
    dump(d, 0, headn, 'head')
    dump(d, len(d) - tailn, tailn, 'tail')

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.isdigit()]
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()]
    for p in args:
        show(p, *(nums or []))
