# -*- coding: utf-8 -*-
"""Full-file signature map (fast): find every (w,h,2w,1) record signature.

usage: python scansig.py <file> [--all]
"""
import os
import struct
import sys

from dimg import SRC, sig_at

FLAG = b'\x01\x00\x00\x00'


def sigs(d):
    out = []
    idx = d.find(FLAG, 0)
    while idx != -1:
        p = idx - 12
        if p >= 0 and sig_at(d, p):
            out.append(p)
        idx = d.find(FLAG, idx + 1)
    return out


def main():
    name = sys.argv[1]
    show_all = '--all' in sys.argv
    d = open(os.path.join(SRC, name), 'rb').read()
    ss = sigs(d)
    print(f'{name} size={len(d)} signatures={len(ss)}')
    prev = None
    for p in ss:
        w, h = struct.unpack_from('<II', d, p)
        gap = '' if prev is None else f'gap={p - prev}'
        if prev is not None:
            pend = prev + 16 + 2 * prevw * prevh
            gap = f'gap={p - pend}'
        if show_all or prev is None or (p - (prev + 16 + 2 * prevw * prevh)) != 24:
            print(f'  sig@{p:>10} {w:>5}x{h:<5} 2wh={2*w*h:>9} {gap}')
        prev, prevw, prevh = p, w, h
    if ss:
        tot = 0
        for p in ss:
            w, h = struct.unpack_from('<II', d, p)
            tot += 2 * w * h
        last = ss[-1]
        lw, lh = struct.unpack_from('<II', d, last)
        last_end = last + 16 + 2 * lw * lh
        gaps = {}
        for i in range(1, len(ss)):
            pw, ph = struct.unpack_from('<II', d, ss[i - 1])
            g = ss[i] - (ss[i - 1] + 16 + 2 * pw * ph)
            gaps[g] = gaps.get(g, 0) + 1
        print(f'  SUMMARY sigs={len(ss)} sum_2wh={tot} first_sig={ss[0]} '
              f'last_end={last_end} bytes_after_last_end={len(d) - last_end} '
              f'gap_histogram={sorted(gaps.items())}')


if __name__ == '__main__':
    main()
