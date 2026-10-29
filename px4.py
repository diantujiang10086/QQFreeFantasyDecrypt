# -*- coding: utf-8 -*-
"""Probe the 4-bytes-per-pixel (flag=2) layout.

    python px4.py <file> [frame_index]
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg  # noqa: E402

# candidate byte orders: name -> (r, g, b, a) offsets into the 4 bytes
ORDERS = {
    'RGBA': (0, 1, 2, 3),
    'BGRA': (2, 1, 0, 3),
    'ARGB': (1, 2, 3, 0),
    'ABGR': (3, 2, 1, 0),
    'GBAR': (3, 0, 1, 2),
    '0RGB': (1, 2, 3, 0),
}


def main():
    path = sys.argv[1]
    want = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    print(f'{os.path.basename(path)} ok={r.get("ok")} oh={r.get("oh")} '
          f'first_px={r.get("first_px")} method={r.get("method")}')
    if not r.get('ok'):
        print('  tried:', r.get('tried'))
        return
    frame = r['frames'][want]
    pre, w, h, px, bpp = frame
    print(f'frame {want}: {w}x{h} bpp={bpp} px@{px}')
    if px is None:
        return
    assert bpp == 4, f'expected 4 bpp, got {bpp}'
    n = w * h
    raw = d[px:px + 4 * n]
    for pos in range(4):
        col = raw[pos::4]
        nz = sum(1 for v in col if v == 0)
        n255 = sum(1 for v in col if v == 255)
        print(f'  byte{pos}: zero={nz/n:6.2%} full={n255/n:6.2%} '
              f'distinct={len(set(col)):4d} mean={sum(col)/n:6.1f}')
    cnt = collections.Counter(raw[4 * i:4 * i + 4] for i in range(n))
    print('  most common pixel words:')
    for word, c in cnt.most_common(6):
        print(f'    {word.hex(" ")}  {c/n:6.2%}  '
              + ' '.join(f'{k}=({word[v[0]]},{word[v[1]]},{word[v[2]]},{word[v[3]]})'
                         for k, v in ORDERS.items() if k in ('RGBA', 'BGRA', 'ARGB')))
    corner = raw[0:4]
    print(f'  pixel(0,0) = {corner.hex(" ")}   pixel(1,0) = {raw[4:8].hex(" ")}')
    ctr = 4 * ((h // 2) * w + w // 2)
    print(f'  pixel(center) = {raw[ctr:ctr+4].hex(" ")}')
    # how "alpha-like" is each position: a background of mostly-zero then jumps
    from PIL import Image
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'px4')
    os.makedirs(out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    for name, (ro, go, bo, ao) in ORDERS.items():
        img = Image.new('RGBA', (w, h))
        img.putdata([(raw[4 * i + ro], raw[4 * i + go], raw[4 * i + bo],
                      raw[4 * i + ao]) for i in range(n)])
        img.save(os.path.join(out, f'{stem}_f{want}_{name}.png'))
    print(f'  wrote {len(ORDERS)} candidate PNGs to {out}')


if __name__ == '__main__':
    main()
