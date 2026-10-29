# -*- coding: utf-8 -*-
"""Numerical sprite-coherence metrics to pick the correct pixel start (D)
and the correct channel order, without a vision model.

For each frame decode we report:
  transp  fraction of pixels with alpha == 0
  comp    number of 4-connected opaque components
  slope   least-squares slope (px/row) of the left and right silhouette edges;
          a wrong pixel start shears the image by (delta/2w) px per row and
          shows up as a large |slope|
  jump    mean |alpha(y,x) - alpha(y+1,x)| / mean alpha  (row-to-row jumpiness)
"""
import os
import sys

import validate as V


def decode(d, off, w, h, alpha_from_byte1):
    a = [[0] * w for _ in range(h)]
    rgb = [[(0, 0, 0)] * w for _ in range(h)]
    stride = 2 * w
    for y in range(h):
        for x in range(w):
            i = off + y * stride + 2 * x
            if i + 1 >= len(d):
                continue
            b0, b1 = d[i], d[i + 1]
            if alpha_from_byte1:
                g, bl, al, r = V.h4(b0), V.l4(b0), V.h4(b1), V.l4(b1)
            else:
                al, r, g, bl = V.h4(b0), V.l4(b0), V.h4(b1), V.l4(b1)
            a[y][x] = al
            rgb[y][x] = (r, g, bl)
    return a, rgb


def slope(rows):
    """rows: list of (y, x).  least squares slope of x vs y."""
    n = len(rows)
    if n < 3:
        return 0.0
    my = sum(y for y, _ in rows) / n
    mx = sum(x for _, x in rows) / n
    num = sum((y - my) * (x - mx) for y, x in rows)
    den = sum((y - my) ** 2 for y, _ in rows)
    return num / den if den else 0.0


def components(a, w, h):
    seen = [[False] * w for _ in range(h)]
    n = 0
    for y0 in range(h):
        for x0 in range(w):
            if a[y0][x0] == 0 or seen[y0][x0]:
                continue
            n += 1
            st = [(y0, x0)]
            seen[y0][x0] = True
            while st:
                y, x = st.pop()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and not seen[yy][xx] \
                            and a[yy][xx] != 0:
                        seen[yy][xx] = True
                        st.append((yy, xx))
    return n


def metrics(a, w, h):
    tot = w * h
    op = [(y, x) for y in range(h) for x in range(w) if a[y][x] != 0]
    transp = 1 - len(op) / tot
    left, right = [], []
    for y in range(h):
        xs = [x for x in range(w) if a[y][x] != 0]
        if xs:
            left.append((y, xs[0]))
            right.append((y, xs[-1]))
    comp = components(a, w, h)
    jn = jd = 0
    for y in range(h - 1):
        for x in range(w):
            jn += abs(a[y][x] - a[y + 1][x])
            jd += max(1, a[y][x])
    jump = jn / jd
    return dict(transp=transp, comp=comp,
                sl=abs(slope(left)), sr=abs(slope(right)), jump=jump,
                opx=len(op))


CASES = [
    ('npc59503.gsn', 84, [40, 16]),
    ('npc64402.gsn', 64, [28, 16]),
    ('npc57301.gsn', 84, [40, 16]),
    ('npc57101.gsn', 84, [40, 16]),
    ('npc64404.gsn', 64, [28, 16]),
]


def main():
    for name, H, Ds in CASES:
        d = open(os.path.join(V.SRC, name), 'rb').read()
        print('=' * 88)
        print(f'{name} size={len(d)} f12={V.u32(d,12)}')
        for D in Ds:
            p = V.pat_at(d, H)
            w, h = p
            for ab in (True, False):
                a, _ = decode(d, H + D, w, h, ab)
                m = metrics(a, w, h)
                tag = 'alpha=hi(byte1)' if ab else 'alpha=hi(byte0)'
                print(f'  D={D:>3} {tag:17s} {w}x{h} transp={m["transp"]:.3f} '
                      f'comp={m["comp"]:>4} slopeL={m["sl"]:7.2f} '
                      f'slopeR={m["sr"]:7.2f} jump={m["jump"]:6.3f} opx={m["opx"]}')


if __name__ == '__main__':
    main()
