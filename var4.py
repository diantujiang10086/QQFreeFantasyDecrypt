# -*- coding: utf-8 -*-
"""Verify the flag=2 hypothesis: record signature (w, h, 4*w, 2) == 4 bytes/px.

    python var4.py <file...>
"""
import mmap
import struct
import sys

def u32(d, o): return struct.unpack_from('<I', d, o)[0]
def u16(d, o): return struct.unpack_from('<H', d, o)[0]

def walk4(d, first_px=100, oh=40, n=40):
    frames = []
    p = first_px - 16
    for i in range(n):
        w, h, s, f = u32(d, p), u32(d, p+4), u32(d, p+8), u32(d, p+12)
        if w == 0 and h == 0 and s == 0 and f == 0:
            frames.append((w, h, 0)); p += oh; continue
        if not (1 <= w <= 8192 and 1 <= h <= 8192):
            return None, f'frame {i}: bad w/h {w}x{h} at {p}'
        # flag f == bytes per pixel / 2  =>  stride = 2*f*w
        if f not in (1, 2) or s != 2 * f * w:
            return None, f'frame {i}: flag {f} stride {s} (w={w}) at {p}'
        if p + 16 + 2 * f * w * h > len(d):
            return None, f'frame {i}: pixels past EOF'
        frames.append((w, h, f))
        p += 16 + 2 * f * w * h + (oh - 16)
    return (p, frames), ''

def main(paths):
    good = bad = 0
    for path in paths:
        with open(path, 'rb') as fh:
            d = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            n, nd = u16(d, 16), u16(d, 20)
            r, why = walk4(d, 100, 40, n)
            name = path.split('\\')[-1]
            if not r:
                print(f'FAIL {name}: {why}'); bad += 1; d.close(); continue
            end, frames = r
            px = sum(2 * f * w * h for w, h, f in frames)
            tail = len(d) - (end - 24)   # walk adds one extra record prefix
            flags = sorted({f for w, h, f in frames if f})
            o = len(d) - 12 * nd
            counts = [u32(d, o + 12 * i) for i in range(nd)]
            dtok = all(u32(d, o + 12 * i + 4) == 0 and u32(d, o + 12 * i + 8) == 0 for i in range(nd)) and sum(counts) == n
            ok = (tail == 12 * nd + 12) and dtok
            good += ok; bad += (not ok)
            print(f'{"OK  " if ok else "BAD "} {name} n={n} nd={nd} flags={flags} '
                  f'pxbytes={px:,} tail={tail} (want {12*nd+12}) dirs={counts} sum_wh={sum(w*h for w,h,f in frames):,}')
            d.close()
    print(f'\n{good} ok / {bad} not ok')

if __name__ == '__main__':
    main(sys.argv[1:])
