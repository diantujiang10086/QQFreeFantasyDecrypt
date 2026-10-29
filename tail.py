# -*- coding: utf-8 -*-
"""Decisive test for the pixel-start question (D=16 vs D=f12+4).

For every frame we know the signature (w,h,2w,1).  Under H1 the pixel block
starts right after the signature; under H2 it starts (f12-12) bytes later.
Both models place every signature identically, so the only difference is the
size of the region left over at the end of the file:

    tail_H1 = size - (p_last + 16 + 2*w*h)
    tail_H2 = tail_H1 - (f12 - 12)

Hypothesis being tested: tail_H1 == u16@20 * (f12 - 12)  ->  H1
                        tail_H2 == u16@20 * (f12 - 12)  ->  H2

usage: python tail.py [file ...]
"""
import os
import sys

import validate as V

FILES = [
    'npc59503.gsn', 'npc64402.gsn', 'npc64404.gsn', 'npc20406.gsn',
    'npc57101.gsn', 'npc57301.gsn', 'npc64401.gsn', 'npc64403.gsn',
    'npc64405.gsn', 'npc64501.gsn', 'npc61401.gsn', 'npc57102.gsn',
    'npc58501.gsn', 'npc108905.gsn', 'npc174501.gsn', 'npc1955501.gsn',
    'npc540201.gsn', 'npc559201.gsn', 'npc559201t.gsn', 'npc511901t.gsn',
    'npc305001.gsn', 'npc15311.gsn', 'npc20101.gsn', 'npc20301.gsn',
    'npc260701.gsn', 'npc499203.gsn', 'npc280702.gsn', 'npc528901.gsn',
    'npc29408.gsn', 'npc31809.gsn', 'npc98203.gsn',
]


def patterns(d):
    out = []
    o = 0
    while o + 16 <= len(d):
        w, h = V.u32(d, o), V.u32(d, o + 4)
        if 1 <= w <= 4096 and 1 <= h <= 4096 and V.u32(d, o + 8) == 2 * w \
                and V.u32(d, o + 12) == 1:
            out.append((o, w, h))
            o += 4
        else:
            o += 1
    return out


def walk_from(d, f12, sigmap, start):
    frames = []
    p = start
    while True:
        m = sigmap.get(p)
        if m is None:
            break
        w, h = m[1], m[2]
        frames.append((p, w, h))
        p = p + (f12 + 4) + 2 * w * h
        if p + 16 > len(d):
            break
    return frames


def walk(d, f12, nframes=0):
    """Greedy walk, spacing (f12+4)+2wh; pick the start that matches nframes."""
    sigs = patterns(d)
    if not sigs:
        return []
    sigmap = {o: (o, w, h) for o, w, h in sigs}
    cands = [walk_from(d, f12, sigmap, o) for o, _, _ in sigs[:4]]
    if nframes:
        for c in cands:
            if len(c) == nframes:
                return c
    return max(cands, key=len)


def main():
    bad = 0
    for name in (sys.argv[1:] or FILES):
        p = os.path.join(V.SRC, name)
        if not os.path.isfile(p):
            print(f'{name:20s} MISSING')
            continue
        d = open(p, 'rb').read()
        f12 = V.u32(d, 12) & 0xffff
        nframes, ndir = V.u32(d, 16) & 0xffff, V.u32(d, 20) & 0xffff
        pre = f12 - 12
        fr = walk(d, f12, nframes)
        if not fr:
            print(f'{name:20s} size={len(d):>9} f12={f12:>3} n={nframes:>3} '
                  f'dir={ndir:>2} NO WALK')
            bad += 1
            continue
        lastp, lw, lh = fr[-1]
        h1 = len(d) - (lastp + 16 + 2 * lw * lh)
        h2 = h1 - pre
        want = ndir * pre
        verdict = 'H1' if h1 == want else ('H2' if h2 == want else '???')
        if verdict == '???':
            bad += 1
        tail0 = [V.u32(d, len(d) - want + 4 * i) for i in range(max(0, want // 4))]
        print(f'{name:20s} size={len(d):>9} f12={f12:>3} n={nframes:>3}/{len(fr):<3} '
              f'dir={ndir:>2} pre={pre:>2} tail_H1={h1:>6} tail_H2={h2:>6} '
              f'dir*pre={want:>4} -> {verdict}  tail0={tail0[:8]}')
    print(f'\nunexplained: {bad}')


if __name__ == '__main__':
    main()
