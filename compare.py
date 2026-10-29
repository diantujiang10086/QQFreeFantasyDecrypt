# -*- coding: utf-8 -*-
"""Render competing (H, D) parse candidates so the correct one can be judged
by eye.  D = number of bytes from the (w,h,2w,1) pattern to the pixel data.

usage: python compare.py
"""
import os
import sys

from PIL import Image, ImageDraw

import validate as V

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')

CASES = [
    ('npc59503.gsn', [('D=40 (f12+4)', 84, 40), ('D=16 (pattern only)', 84, 16)],
     (84, [38, 63]), 5),
    ('npc64402.gsn', [('D=28 (f12+4)', 64, 28), ('D=16 (pattern only)', 64, 16)],
     (64, [12, 14]), 8),
    ('npc57301.gsn', [('D=40', 84, 40), ('D=16', 84, 16)],
     (84, [55, 99]), 3),
    ('npc57101.gsn', [('D=40', 84, 40), ('D=16', 84, 16)],
     (84, [57, 69]), 3),
]


def walk(d, H, D, maxf=64):
    size = len(d)
    pos = H
    out = []
    while pos + 16 <= size and len(out) < maxf:
        p = V.pat_at(d, pos)
        if not p:
            break
        w, h = p
        out.append((pos, w, h))
        pos += D + 2 * w * h
        if pos > size:
            break
    return out


def compose(d, name, specs, maxf, scale):
    parsed = []
    for label, H, D in specs:
        fr = walk(d, H, D, maxf)
        parsed.append((label, D, fr))
    gap = 8
    cellw = max(sum(w * scale + gap for _, w, _ in fr[:maxf]) + gap
                for _, _, fr in parsed)
    cellh = max(h for _, _, fr in parsed for _, _, h in fr)
    W = cellw
    Hh = (cellh * scale + 22) * len(parsed) + gap
    out = Image.new('RGB', (W, Hh), (250, 250, 250))
    dr = ImageDraw.Draw(out)
    y = gap
    for label, D, fr in parsed:
        xx = gap
        for off, w, h in fr[:maxf]:
            px = V.unpack(d, off + D, w, h)
            im = Image.frombytes('RGBA', (w, h), bytes(px))
            big = im.resize((w * scale, h * scale), Image.NEAREST)
            bg = V.checker(w * scale, h * scale, 6)
            bg.paste(big, (0, 0), big)
            out.paste(bg, (xx, y + 18))
            dr.text((xx, y + 4), f'{w}x{h}@{off}+{D}', fill=(0, 0, 0))
            xx += w * scale + gap
        dr.text((gap, y + 4 + cellh * scale + 4),
                f'[{name}] {label}  frames={len(fr)}', fill=(0, 0, 200))
        y += cellh * scale + 22 + gap
    path = os.path.join(OUT, name.replace('.gsn', '') + '_cmp.png')
    out.save(path)
    print(f'{name}: {path} {out.size}')
    for label, D, fr in parsed:
        print(f'   {label:18s} frames={len(fr)} sizes={[(w, h) for _, w, h in fr[:8]]}')


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, specs, _, scale in CASES:
        d = open(os.path.join(V.SRC, name), 'rb').read()
        compose(d, name, specs, 8, scale)


if __name__ == '__main__':
    main()
