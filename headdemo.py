"""Visual demo of the head family's two layers.

Writes one PNG with, per row: the colour layer, the grayscale second layer, and a
composite where the second layer is tinted (proving it behaves like a tintable
material mask -- i.e. hair that the engine recolours).

    python headdemo.py [--out out\\head_demo.png]
"""
import os
import sys

from PIL import Image, ImageDraw

import dimg
import headtool

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = [('head0101.gsn', 0), ('head0101.gsn', 2), ('head0251.gsn', 0),
        ('head1151.gsn', 0), ('head0301.gsn', 0)]
TINT = (236, 64, 122)          # hair tint used in the third panel


def layer(d, c):
    p, w, h, stride, _ = c
    return dimg.to_image(d, p + 16, w, h, stride // w)


def tinted(colour, mask, tint):
    """colour -> RGB, then multiply by mask luminance and tint."""
    out = Image.new('RGBA', colour.size)
    c, m = colour.load(), mask.load()
    for y in range(colour.height):
        for x in range(colour.width):
            r, g, b, a = c[x, y]
            if not a:
                out.putpixel((x, y), (0, 0, 0, 0))
                continue
            if x < mask.width and y < mask.height:
                mr, mg, mb, ma = m[x, y]
                if ma:
                    k = mg / 255.0
                    r = int(r * (1 - k) + tint[0] * k)
                    g = int(g * (1 - k) + tint[1] * k)
                    b = int(b * (1 - k) + tint[2] * k)
            out.putpixel((x, y), (r, g, b, a))
    return out


def checker(w, h, s=8):
    img = Image.new('RGB', (w, h), (54, 58, 64))
    dr = ImageDraw.Draw(img)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if ((x // s) + (y // s)) % 2:
                dr.rectangle([x, y, x + s - 1, y + s - 1], fill=(76, 82, 90))
    return img


def main():
    a = sys.argv[1:]
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'out', 'head_demo.png')
    zoom = 6
    rows = []
    for fn, pair in ROWS:
        path = os.path.join(headtool.SRC, fn)
        if not os.path.exists(path):
            continue
        d = open(path, 'rb').read()
        recs, extra, k = headtool.segment(d)
        paired = k == 2 * dimg.head(d)['n_frames']
        if pair * 2 >= len(recs):
            continue
        colour = layer(d, recs[pair * 2])
        mask = layer(d, recs[pair * 2 + 1]) if paired and pair * 2 + 1 < len(recs) else None
        panels = [('colour  %dx%d' % colour.size, colour)]
        if mask:
            panels.append(('2nd layer (gray)  %dx%d' % mask.size, mask))
            panels.append(('2nd layer tinted', tinted(colour, mask, TINT)))
        rows.append((fn + ' d%d' % (pair + 1), panels))
    cw = max(sum(p.width for _, p in ps) + 20 * (len(ps) - 1) for _, ps in rows) * zoom
    ch = max(max(p.height for _, p in ps) for _, ps in rows) * zoom + 34
    W = cw + 20
    H = ch * len(rows) + 10
    sheet = checker(W, H, 12)
    dr = ImageDraw.Draw(sheet)
    y0 = 6
    for title, ps in rows:
        dr.text((10, y0), title, fill=(230, 234, 240))
        x = 10
        for label, im in ps:
            big = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
            sheet.paste(big, (x, y0 + 14), big)
            dr.text((x, y0 + 16 + big.height), label, fill=(170, 176, 186))
            x += big.width + 20
        y0 += ch
    sheet.save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
