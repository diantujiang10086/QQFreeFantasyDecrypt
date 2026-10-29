# -*- coding: utf-8 -*-
"""Brute-force (first_px, oh) that makes the whole frame walk validate.

usage: python solve.py file [file ...]
"""
import os
import sys

import dimg

SRC = dimg.SRC


def solve(d, n_frames, firsts=None, ohs=None):
    if firsts is None:
        firsts = range(24 + 4 * 8, 24 + 4 * 240, 4)
    if ohs is None:
        ohs = list(range(24, 260, 4))
    hits = []
    for first_px in firsts:
        if dimg.sig_at(d, first_px - 16) is None:
            continue
        for oh in ohs:
            frames, ok, why = dimg.walk(d, first_px, oh, n_frames)
            if ok:
                end = frames[-1][3] + 2 * frames[-1][1] * frames[-1][2]
                hits.append((first_px, oh, end, len(d) - end,
                             [(w, h) for _, w, h, _ in frames[:3]]))
    return hits


def main():
    for name in sys.argv[1:]:
        p = os.path.join(SRC, name)
        if not os.path.isfile(p):
            print(f'{name}: MISSING')
            continue
        d = open(p, 'rb').read()
        h = dimg.head(d)
        print('=' * 92)
        print(f'{name} size={len(d)} major={h["major"]} minor={h["minor"]} '
              f'patch/dirs={h["n_dirs"]} frames={h["n_frames"]}')
        hits = solve(d, h['n_frames'])
        if not hits:
            print('  no (first_px, oh) makes all frames parse')
            # report how far the best candidate got
            for first_px, oh, tag in dimg.candidates(h, h['n_dirs']):
                fr, ok, why = dimg.walk(d, first_px, oh, h['n_frames'])
                print(f'  cand {tag}: first_px={first_px} oh={oh} -> '
                      f'{len(fr)} frames, {why}')
            continue
        for first_px, oh, end, tail, sizes in hits[:6]:
            print(f'  first_px={first_px:>5} oh={oh:>4} end={end:>10} '
                  f'tail={tail:>7} first_sizes={sizes}')
        if len(hits) > 6:
            print(f'  ... {len(hits)-6} more')


if __name__ == '__main__':
    main()
