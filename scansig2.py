# -*- coding: utf-8 -*-
"""Probe the "v2 descriptor" family: files with no (w,h,2w,1) signature.

The failing 'e'/'t' files start with a descriptor that looks like

    (w, h, a, b, w, 1, h, flag)

instead of the normal (w, h, 2w, 1).  This tool finds every such descriptor
near the header, then walks from the first one and reports the distance to
the nearest following descriptor, so the record overhead can be measured.

usage: python scansig2.py <file> [n_records] [window_mb]
"""
import os
import struct
import sys

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def desc_at(d, p):
    """(w, h, a, b, flag) for a v2 descriptor, else None."""
    if p < 0 or p + 32 > len(d):
        return None
    w, h, a, b, w2, f, h2, fl = (u32(d, p + 4 * i) for i in range(8))
    if not (1 <= w <= 8192 and 1 <= h <= 8192):
        return None
    if w2 == w and f == 1 and h2 == h:
        return w, h, a, b, fl
    return None


def find_all(d, start, stop, limit=40):
    out = []
    p = start
    while p + 32 <= stop and len(out) < limit:
        r = desc_at(d, p)
        if r:
            out.append((p, r))
            p += 4
        else:
            p += 2
    return out


def main():
    name = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    win = int(sys.argv[3]) if len(sys.argv) > 3 else 8_000_000
    d = open(os.path.join(SRC, name), 'rb').read()
    print(f'### {name} size={len(d)}')
    head = [u32(d, o) for o in range(0, 24, 4)]
    print('header int32:', head[:6])
    near = find_all(d, 24, min(len(d), 24 + 4 * 400))
    print(f'descriptors in first 1.6KB: {len(near)}')
    for p, r in near[:6]:
        print(f'   @{p}: w={r[0]} h={r[1]} a={r[2]} b={r[3]} flag={r[4]} '
              f'2wh={2 * r[0] * r[1]}')
    if not near:
        return
    pos, r = near[0]
    for i in range(n):
        w, h = r[0], r[1]
        lo = pos + 32 + 2 * w * h
        if lo + 32 > len(d):
            print(f'  rec{i} @{pos} ({w}x{h}) -> past EOF')
            break
        nxt = None
        p = lo - 16 if lo > 16 else lo
        stop = min(len(d), lo + win)
        p = lo
        while p + 32 <= stop:
            q = desc_at(d, p)
            if q:
                nxt = (p, q)
                break
            p += 2
        if nxt is None:
            print(f'  rec{i} @{pos} ({w}x{h}) pixels end {lo} -> no next '
                  f'descriptor in {win} bytes')
            break
        gap = nxt[0] - lo
        print(f'  rec{i} @{pos} ({w}x{h}) px_end={lo} next@{nxt[0]} '
              f'gap={gap} (overhead={gap + 32 - 32}) '
              f'next=({nxt[1][0]}x{nxt[1][1]} a={nxt[1][2]} b={nxt[1][3]} '
              f'flag={nxt[1][4]})')
        pos, r = nxt


if __name__ == '__main__':
    main()
