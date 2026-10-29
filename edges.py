# -*- coding: utf-8 -*-
"""Tight-crop / edge analysis: which pixel start makes the opaque content
exactly fill the declared (w,h) frame?

A sprite atlas frame is normally tightly cropped: its opaque bounding box
equals the frame.  A wrong pixel start shifts content horizontally by
D/2 pixels and grafts the previous row's tail onto the left edge, so the
bbox stops touching one of the horizontal edges.
"""
import os

import validate as V
import metrics as M

CASES = [
    ('npc59503.gsn', 84, [40, 36, 32, 28, 24, 20, 16, 12, 8, 4]),
    ('npc64402.gsn', 64, [28, 24, 20, 16, 12, 8, 4]),
    ('npc64404.gsn', 64, [28, 24, 20, 16, 12, 8, 4]),
    ('npc57301.gsn', 84, [40, 36, 32, 28, 24, 20, 16, 12, 8, 4]),
    ('npc57101.gsn', 84, [40, 36, 32, 28, 24, 20, 16, 12, 8, 4]),
]


def profile(a, w, h):
    cols = [sum(1 for y in range(h) if a[y][x] != 0) for x in range(w)]
    rows = [sum(1 for x in range(w) if a[y][x] != 0) for y in range(h)]
    return cols, rows


def main():
    for name, H, Ds in CASES:
        d = open(os.path.join(V.SRC, name), 'rb').read()
        p = V.pat_at(d, H)
        w, h = p
        print('=' * 96)
        print(f'{name} size={len(d)} f12={V.u32(d,12)} first frame {w}x{h} '
              f'pattern@{H}')
        print(f'{"D":>4} {"opx":>6} {"bbox":>16} {"col0":>5} {"colW":>5} '
              f'{"row0":>5} {"rowH":>5} {"comp":>5} {"edges":>12}')
        for D in Ds:
            a, _ = M.decode(d, H + D, w, h, True)
            cols, rows = profile(a, w, h)
            xs = [x for x in range(w) if cols[x]]
            ys = [y for y in range(h) if rows[y]]
            bbox = (min(xs), min(ys), max(xs), max(ys)) if xs else None
            touch = ''.join(['L' if cols[0] else '-', 'R' if cols[w - 1] else '-',
                             'T' if rows[0] else '-', 'B' if rows[h - 1] else '-'])
            ncomp = M.components(a, w, h)
            print(f'{D:>4} {sum(cols):>6} {str(bbox):>16} {cols[0]:>5} '
                  f'{cols[w-1]:>5} {rows[0]:>5} {rows[h-1]:>5} {ncomp:>5} {touch:>12}')
            if D in (40, 28, 16):
                print('     colprof ' + ' '.join(f'{c:>3}' for c in cols))


if __name__ == '__main__':
    main()
