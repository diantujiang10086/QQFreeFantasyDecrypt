# -*- coding: utf-8 -*-
"""List frame records of a .gsn file with their prefixes.

usage: python frames.py file [first_px] [oh] [n] [start]
"""
import os
import sys

import dimg
from dimg import SRC, u32


def main():
    name = sys.argv[1]
    d = open(os.path.join(SRC, name), 'rb').read()
    h = dimg.head(d)
    first_px = int(sys.argv[2]) if len(sys.argv) > 2 else \
        dimg.hints(h)[0][0]
    oh = int(sys.argv[3]) if len(sys.argv) > 3 else dimg.hints(h)[0][1]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 24
    start = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    print(f'{name} size={len(d)} first_px={first_px} oh={oh} '
          f'frames={h["n_frames"]}')
    frames, ok, why = dimg.walk(d, first_px, oh, min(n, h['n_frames']))
    print(f'walk: {len(frames)} frames ok={ok} {why}')
    nw = (oh - 16) // 4
    for i, (pre, w, hh, px, bpp) in enumerate(frames):
        if i < start:
            continue
        if px is None:
            print(f'  f{i:>3}: sig@- {0:>5}x{0:<5} empty frame (no pixels)')
            continue
        end = px + bpp * w * hh
        pre_words = [u32(d, pre + 4 * k) for k in range(nw)]
        post = [u32(d, end + 4 * k) for k in range(6)] if end + 24 <= len(d) \
            else []
        print(f'  f{i:>3}: sig@{px-16:>10} {w:>5}x{hh:<5} '
              f'pxbytes={bpp*w*hh:>9} bpp={bpp} '
              f'px@{px:>10} end={end:>10}')
        print(f'        prefix@{pre} {pre_words}')
        print(f'        after-end {post}')


if __name__ == '__main__':
    main()
