"""Relaxed signature scan: find every (w,h,stride,flag) window where the record
layout is self-consistent (stride = bpp*w with bpp 1..4, flag == bpp).

    python probe_head.py <file> [--max 40]

Prints every hit plus the gap from the previous hit's pixel end, so the record
boundary of a new file family can be read off directly.
"""
import struct
import sys


def hits(d, wmax=1024):
    """(w,h,stride,flag) windows that are *plausible*: stride is a whole number
    of bytes per pixel (2..4) and flag is 1..2 -- the strict rule stride == 2*flag*w
    is deliberately NOT enforced, so padded/odd variants still show up."""
    out = []
    n = len(d)
    for p in range(0, n - 16, 4):
        w, h, s, f = struct.unpack_from('<4I', d, p)
        if not (2 <= w <= wmax and 2 <= h <= wmax):
            continue
        if s % w:
            continue
        q = s // w
        if q not in (1, 2, 3, 4):
            continue
        if f not in (1, 2):
            continue
        px = p + 16
        if px + s * h > n:
            continue
        out.append((p, w, h, s, f))
    return out


def main():
    args = sys.argv[1:]
    maxn = 40
    if '--max' in args:
        j = args.index('--max')
        maxn = int(args[j + 1])
        del args[j:j + 2]
    for path in args:
        d = open(path, 'rb').read()
        hs = hits(d)
        print('=== %s  %d B  hits=%d' % (path.split('\\')[-1], len(d), len(hs)))
        prev_end = None
        for i, (p, w, h, s, f) in enumerate(hs[:maxn]):
            px = p + 16
            end = px + s * h
            gap = '' if prev_end is None else '  gap=%d' % (p - prev_end)
            print('  #%d sig@%-8d (%3dx%-3d stride=%-5d bpp=%d) px=%d..%d%s'
                  % (i, p, w, h, s, f, px, end, gap))
            prev_end = end
        if len(hs) > maxn:
            print('  ... %d more' % (len(hs) - maxn))
        if hs:
            print('  tail after last px: %d' % (len(d) - prev_end))


if __name__ == '__main__':
    main()
