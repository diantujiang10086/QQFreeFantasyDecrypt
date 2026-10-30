# -*- coding: utf-8 -*-
"""
Self-validating parse + visual decode for DIMG (.gsn).

Model (canonical form):
   file = [preamble H bytes][frame record R bytes][pixel block 2*w*h][...][trailer T]
   each frame record STARTS with the 4 int32 pattern (w, h, 2*w, 1)
   H = byte offset of the first pattern (= first record start)

  layout A: rec, px, rec, px, ...
  layout B: rec0..recN-1, px0..pxN-1

Walk is validated by byte conservation: the walk must reach EOF with a small
trailer (0..64, 4-aligned).  Nothing about the preamble is assumed.
"""
import os
import struct
import sys

from PIL import Image, ImageDraw
import paths

SRC = paths.sub('data/official/avatar/npc')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')

FILES = [
    'npc64402.gsn', 'npc64403.gsn', 'npc64404.gsn', 'npc64405.gsn',
    'npc64401.gsn', 'npc64501.gsn', 'npc59503.gsn', 'npc57101.gsn',
    'npc57301.gsn', 'npc20406.gsn', 'npc108905.gsn', 'npc174501.gsn',
    'npc61401.gsn', 'npc57102.gsn', 'npc58501.gsn',
]


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def pat_at(d, o):
    """(w,h) if the 4-int32 pattern is exactly at o, else None."""
    if o + 16 > len(d):
        return None
    w = u32(d, o)
    h = u32(d, o + 4)
    if not (1 <= w <= 4096 and 1 <= h <= 4096):
        return None
    if u32(d, o + 8) != 2 * w or u32(d, o + 12) != 1:
        return None
    return (w, h)


def first_pattern(d):
    for o in range(0, min(len(d), 4096)):
        if o % 4:
            continue
        p = pat_at(d, o)
        if p:
            return o
    return None


def parse_layout_a(d, H, R):
    """Walk records until EOF.  Returns (frames, trailer) or None."""
    size = len(d)
    pos = H
    frames = []
    while True:
        p = pat_at(d, pos)
        if not p:
            return None
        w, h = p
        frames.append((pos, w, h))
        pos += R + 2 * w * h
        if pos == size:
            return frames, 0
        if size - 64 <= pos < size:
            # trailer region: nothing more may parse
            if pat_at(d, pos) is None:
                return frames, size - pos
            return None
        if pos > size:
            return None
        if len(frames) > 4096:
            return None


def parse_layout_b(d, H, R, N):
    size = len(d)
    pos = H
    frames = []
    for _ in range(N):
        p = pat_at(d, pos)
        if not p:
            return None
        w, h = p
        frames.append((pos, w, h))
        pos += R
    for pos0, w, h in frames:
        pos += 2 * w * h
    if 0 <= size - pos <= 64:
        return frames, size - pos
    return None


def h4(x):
    return ((x >> 4) & 0xF) * 17


def l4(x):
    return (x & 0xF) * 17


def unpack(d, off, w, h, alpha_high=True):
    """ARGB4444-ish: byte0 = G|B, byte1 = A|R."""
    px = bytearray(w * h * 4)
    stride = 2 * w
    for y in range(h):
        row = off + y * stride
        for x in range(w):
            i = row + 2 * x
            if i + 1 >= len(d):
                continue
            b0 = d[i]
            b1 = d[i + 1]
            if alpha_high:
                g, b, a, r = h4(b0), l4(b0), h4(b1), l4(b1)
            else:
                a, r, g, b = h4(b0), l4(b0), h4(b1), l4(b1)
            o = (y * w + x) * 4
            px[o] = r
            px[o + 1] = g
            px[o + 2] = b
            px[o + 3] = a
    return px


def checker(w, h, s=8):
    im = Image.new('RGB', (w, h), (200, 200, 200))
    dr = ImageDraw.Draw(im)
    for yy in range(0, h, s):
        for xx in range(0, w, s):
            if ((xx // s) + (yy // s)) % 2:
                dr.rectangle([xx, yy, xx + s - 1, yy + s - 1], fill=(150, 150, 150))
    return im


def sheet(d, frames, R, path, scale=3):
    """frames: list of (rec_off, w, h).  Row1 = alpha composite, row2 = opaque."""
    imgs = []
    for off, w, h in frames[:12]:
        px = unpack(d, off + R, w, h)
        im = Image.frombytes('RGBA', (w, h), bytes(px))
        imgs.append((im, w, h))
    if not imgs:
        return
    gap = 6
    W = sum(i[1] * scale + gap for i in imgs) + gap
    Hh = max(i[2] for i in imgs) * scale * 2 + gap * 3 + 14
    out = Image.new('RGB', (W, Hh), (255, 255, 255))
    dr = ImageDraw.Draw(out)
    xx = gap
    for im, w, h in imgs:
        big = im.resize((w * scale, h * scale), Image.NEAREST)
        bg = checker(w * scale, h * scale, 6)
        bg.paste(big, (0, 0), big)
        out.paste(bg, (xx, gap + 14))
        op = Image.new('RGB', (w, h), (255, 255, 255))
        op.paste(im.convert('RGB'), (0, 0), im)
        out.paste(op.resize((w * scale, h * scale), Image.NEAREST),
                  (xx, gap * 2 + 14 + max(i[2] for i in imgs) * scale))
        dr.text((xx, 2), f'{w}x{h}', fill=(0, 0, 0))
        xx += w * scale + gap
    out.save(path)
    return out.size


def main():
    names = sys.argv[1:] or FILES
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        path = os.path.join(SRC, name)
        if not os.path.isfile(path):
            print(f'{name}: MISSING')
            continue
        d = open(path, 'rb').read()
        size = len(d)
        n16 = u32(d, 16)
        n20 = u32(d, 20)
        H = first_pattern(d)
        print('=' * 78)
        print(f'{name} size={size} n@16={n16} n@20={n20} f12={u32(d,12)} '
              f'major={u32(d,8)&0xffff} first_pattern={H}')
        if H is None:
            print('   no pattern found')
            continue
        ok = False
        for R in range(8, 257, 4):
            r = parse_layout_a(d, H, R)
            if r:
                frames, trail = r
                ok = True
                print(f'   [A] R={R} frames={len(frames)} trail={trail} '
                      f'sizes={[(f[1], f[2]) for f in frames[:8]]}')
                if R in (24, 28, 32, 36, 40, 44, 48, 52):
                    p = os.path.join(OUT, f'{name}_A_R{R}.png')
                    print('       sheet', sheet(d, frames, R, p))
        for R in range(8, 129, 4):
            for N in {n16, n20}:
                r = parse_layout_b(d, H, R, N)
                if r:
                    frames, trail = r
                    print(f'   [B] R={R} N={N} trail={trail} '
                          f'sizes={[(f[1], f[2]) for f in frames[:8]]}')
        if not ok:
            print('   (no layout-A solution)')


if __name__ == '__main__':
    main()
