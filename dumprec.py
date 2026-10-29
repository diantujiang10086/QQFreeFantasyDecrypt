# -*- coding: utf-8 -*-
"""Dump record boundaries of one file to inspect a frame-walk failure.

    python dumprec.py <file> [--first-px N] [--oh N] [--max-frames N]
"""
import argparse
import binascii
import mmap
import struct

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--first-px', type=int, default=None)
    ap.add_argument('--oh', type=int, default=None)
    ap.add_argument('--frames', type=int, default=4)
    a = ap.parse_args()
    fh = open(a.path, 'rb')
    d = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
    u16 = lambda o: struct.unpack_from('<H', d, o)[0]
    u32 = lambda o: struct.unpack_from('<I', d, o)[0]
    n, nd = u16(16), u16(20)
    print(f'{a.path.split(chr(92))[-1]}  size={len(d):,}  nFrames={n}  nDirs={nd}  '
          f'ver={u16(8)}.{u16(10)}.{u16(12)}  oh={u16(14)}')
    first_px = a.first_px or 100
    oh = a.oh or 40
    print(f'first_px={first_px}  oh={oh}')
    p = first_px - 16
    for i in range(min(n, a.frames)):
        w, h, s, f = u32(p), u32(p + 4), u32(p + 8), u32(p + 12)
        ok = (w == 0 and h == 0 and s == 0 and f == 0) or (1 <= w <= 8192 and 1 <= h <= 8192 and f in (1, 2) and s == 2 * f * w)
        print(f'  frame {i}: sig@{p} (w={w}, h={h}, stride={s}, flag={f}) {"ok" if ok else "BAD"}')
        if i < a.frames - 1 and not ok:
            print('    --- context (sig-32 .. sig+32) ---')
            o0 = max(0, p - 32)
            for o in range(o0, p + 32, 16):
                print(f'    {o:>12,}  {binascii.hexlify(d[o:o+16]).decode()}   {[u32(o+4*j) for j in range(4)]}')
            print('    --- plausible signatures within +-256 ---')
            for off in range(max(84, p - 256), p + 256, 4):
                ww, hh, ss, ff = u32(off), u32(off + 4), u32(off + 8), u32(off + 12)
                if 1 <= ww <= 8192 and 1 <= hh <= 8192 and ff in (1, 2) and ss == 2 * ff * ww:
                    print(f'      hit @{off:,} (w={ww}, h={hh}, stride={ss}, flag={ff}) delta={off-p:+,}')
            break
        if w == 0:
            p += oh
        else:
            p += 16 + 2 * f * w * h + (oh - 16)
    d.close()
    fh.close()

if __name__ == '__main__':
    main()
