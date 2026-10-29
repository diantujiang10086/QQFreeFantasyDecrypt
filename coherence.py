# -*- coding: utf-8 -*-
"""Independent evidence for the pixel start: frame-to-frame coherence.

A constant wrong pixel offset is a cyclic shift of the whole pixel stream,
so spatial smoothness cannot detect it -- but it *does* scramble which bytes
belong to which frame.  Consecutive animation frames of the same size are
usually very similar, so comparing (correct px) against (px shifted by +2
bytes, i.e. one pixel) is a real discriminator.

usage: python coherence.py [file ...]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg

SRC = dimg.SRC
DEFAULT = ['npc20301.gsn', 'npc61401.gsn', 'npc1955501.gsn', 'npc511901.gsn',
           'npc499203.gsn', 'npc64404.gsn', 'npc29408.gsn', 'npc57101.gsn']


def pair_stats(d, pa, pb, n):
    same = 0
    tot = 0
    for i in range(n):
        a = d[pa + 2 * i:pa + 2 * i + 2]
        b = d[pb + 2 * i:pb + 2 * i + 2]
        if a == b:
            same += 1
        tot += abs(a[0] - b[0]) + abs(a[1] - b[1])
    return same / n, tot / (2.0 * n)


def main():
    names = sys.argv[1:] or DEFAULT
    for name in names:
        d = open(os.path.join(SRC, name), 'rb').read()
        r = dimg.parse(d)
        if not r['ok']:
            print(f'{name}: FAIL')
            continue
        pairs = []
        for i in range(1, len(r['frames'])):
            _, w0, h0, p0, b0 = r['frames'][i - 1]
            _, w1, h1, p1, b1 = r['frames'][i]
            if p0 and p1 and (w0, h0) == (w1, h1) and b0 == b1 == 2:
                pairs.append((w0, h0, p0, p1))
        print(f'### {name} oh={r["oh"]} frames={len(r["frames"])} '
              f'same-size consecutive pairs={len(pairs)}')
        if not pairs:
            print('    (no same-size pair to compare)')
            continue
        agg = {'ok_same': 0.0, 'ok_mad': 0.0, 'sh_same': 0.0, 'sh_mad': 0.0}
        for w, h, p0, p1 in pairs:
            n = w * h
            s, m = pair_stats(d, p0, p1, n)
            agg['ok_same'] += s
            agg['ok_mad'] += m
            s2, m2 = pair_stats(d, p0 + 2, p1 + 2, n)
            agg['sh_same'] += s2
            agg['sh_mad'] += m2
        k = len(pairs)
        print(f'    correct px : identical={100*agg["ok_same"]/k:6.2f}%  '
              f'mean|d|={agg["ok_mad"]/k:7.3f}')
        print(f'    px+2 bytes : identical={100*agg["sh_same"]/k:6.2f}%  '
              f'mean|d|={agg["sh_mad"]/k:7.3f}')


if __name__ == '__main__':
    main()
