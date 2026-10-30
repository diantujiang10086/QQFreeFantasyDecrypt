"""Segment a `head/*.gsn` file and characterise every image it contains.

Head files do not follow the npc record grid: n_frames/n_dirs look like 5/5 but
each direction stores TWO image records, and the byte gap between a pixel block
and the next signature is 12 or 20 (never the npc `oh`).  So this tool segments
greedily -- after a pixel block, look for the next valid signature within the
first 32 bytes -- and then reports, per image, whether it looks like a colour
layer or a grayscale mask.

    python head_probe.py <file> [--png DIR]
"""
import os
import struct
import sys

import dimg

HERE = os.path.dirname(os.path.abspath(__file__))


def sig_at(d, p):
    """(w,h,stride,flag) if a strict signature sits at p, else None."""
    if p < 0 or p + 16 > len(d):
        return None
    w, h, s, f = struct.unpack_from('<4I', d, p)
    if not (1 <= w <= 1024 and 1 <= h <= 1024):
        return None
    if f not in (1, 2) or s != 2 * f * w:
        return None
    return w, h, s, f


def segment(d, start=60):
    recs = []
    p = start
    while p + 16 <= len(d):
        hit = None
        for off in range(0, 33, 4):          # prefix lengths seen: 12, 16, 20
            s = sig_at(d, p + off)
            if s:
                hit = (p + off, s)
                break
        if not hit:
            break
        sp, (w, h, stride, flag) = hit
        px = sp + 16
        bpp = stride // w
        end = px + stride * h
        if end > len(d):
            break
        recs.append({'pre': p, 'sig': sp, 'w': w, 'h': h, 'bpp': bpp,
                     'px': px, 'end': end, 'gap': sp - p})
        p = end
    return recs, p


def stats(d, r):
    bpp, w, h, px = r['bpp'], r['w'], r['h'], r['px']
    n = w * h
    if bpp == 2:
        raw = d[px:px + 2 * n]
        b0, b1 = raw[0::2], raw[1::2]
        a = [x >> 4 for x in b1]
        r_ = [(x & 15) for x in b1]
        g_ = [(x >> 4) for x in b0]
        b_ = [(x & 15) for x in b0]
    else:
        raw = d[px:px + 4 * n]
        r_, g_, b_, a = raw[0::4], raw[1::4], raw[2::4], raw[3::4]
        a = [x >> 4 for x in a]
        r_ = [x >> 4 for x in r_]
        g_ = [x >> 4 for x in g_]
        b_ = [x >> 4 for x in b_]
    opaque = [i for i in range(n) if a[i] > 0]
    if not opaque:
        return {'opaque': 0, 'gray': 0.0, 'mean': (0, 0, 0)}
    gm = sum(abs(r_[i] - g_[i]) + abs(g_[i] - b_[i]) for i in opaque) / len(opaque)
    mr = sum(r_[i] for i in opaque) / len(opaque)
    mg = sum(g_[i] for i in opaque) / len(opaque)
    mb = sum(b_[i] for i in opaque) / len(opaque)
    return {'opaque': len(opaque), 'gray': round(gm, 2),
            'mean': (round(mr, 1), round(mg, 1), round(mb, 1))}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    name = args[0]
    path = name if os.path.exists(name) else os.path.join(
        r'<dir>',
        name if name.endswith('.gsn') else name + '.gsn')
    d = open(path, 'rb').read()
    h = dimg.head(d)
    pre = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    print('=== %s  %d B  ver %d.%d.%d  n_frames=%d n_dirs=%d' % (
        os.path.basename(path), len(d), h['major'], h['minor'], h['n_dirs'],
        h['n_frames'], h['n_dirs']))
    print('  preamble:', pre)
    recs, end = segment(d)
    print('  records: %d  last_end=%d  tail=%d (=%d dirs*12 + %d)'
          % (len(recs), end, len(d) - end, (len(d) - end) // 12,
             (len(d) - end) - 12 * ((len(d) - end) // 12)))
    print('  %-3s %-6s %-6s %-6s %-4s %-6s %-9s %-22s %s' % (
        '#', 'prefix', 'sig', 'size', 'bpp', 'px', 'opaque', 'mean RGB', 'gray'))
    for i, r in enumerate(recs):
        st = stats(d, r)
        print('  %-3d %-6d %-6d %3dx%-3d %-4d %-6d %4d/%-5d (%5.1f,%5.1f,%5.1f) %s'
              % (i, r['gap'], r['sig'], r['w'], r['h'], r['bpp'], r['px'],
                 st['opaque'], r['w'] * r['h'], st['mean'][0], st['mean'][1],
                 st['mean'][2], st['gray']))


if __name__ == '__main__':
    main()
