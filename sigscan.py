# -*- coding: utf-8 -*-
"""Scan a .gsn for plausible frame signatures and show the record layout.

    python sigscan.py <file> [--max N] [--from N] [--to N]
"""
import argparse
import mmap
import struct

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--max', type=int, default=25)
    ap.add_argument('--min-w', type=int, default=1)
    a = ap.parse_args()
    fh = open(a.path, 'rb')
    d = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
    u16 = lambda o: struct.unpack_from('<H', d, o)[0]
    u32 = lambda o: struct.unpack_from('<I', d, o)[0]
    n, nd = u16(16), u16(20)
    # canvas dims from the preamble (words 3..6 of the 9-word preamble at 24)
    W, H = u32(24 + 12), u32(24 + 16)
    print(f'{a.path.split(chr(92))[-1]} size={len(d):,} n={n} nd={nd} canvas={W}x{H}')
    hits = []
    end = len(d) - 16
    p = 84
    while p < end and len(hits) < a.max:
        w, h, s, f = u32(p), u32(p + 4), u32(p + 8), u32(p + 12)
        if (a.min_w <= w <= W + 64 and 1 <= h <= H + 64 and f in (1, 2) and s == 2 * f * w
                and p + 16 + 2 * f * w * h <= len(d)):
            hits.append((p, w, h, f))
            p += 16 + 2 * f * w * h + 24
        else:
            p += 4
    prev = None
    for (off, w, h, f) in hits:
        gap = '' if prev is None else f'  gap_from_px_end={off - (prev + 16 + 2 * prevf * prevw * prevh):,}'
        print(f'  sig@{off:>12,}  w={w:>4} h={h:>4} flag={f} pxbytes={2*f*w*h:>10,}{gap}')
        prev, prevw, prevh, prevf = off, w, h, f
    d.close()
    fh.close()

if __name__ == '__main__':
    main()
