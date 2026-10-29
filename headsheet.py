"""Contact sheet for the head family: first colour image of every file.

    python headsheet.py [--dir out\\head\\..] [--out out\\head_sheet.png] [--cols 12]
"""
import os
import sys

from PIL import Image, ImageDraw

import headtool

HERE = os.path.dirname(os.path.abspath(__file__))
CELL_W, CELL_H, PAD = 104, 128, 6


def checker(w, h, s=8):
    img = Image.new('RGB', (w, h), (54, 58, 64))
    d = ImageDraw.Draw(img)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if ((x // s) + (y // s)) % 2:
                d.rectangle([x, y, x + s - 1, y + s - 1], fill=(76, 82, 90))
    return img


def main():
    a = sys.argv[1:]
    cols = int(a[a.index('--cols') + 1]) if '--cols' in a else 12
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'out', 'head_sheet.png')
    png_root = a[a.index('--dir') + 1] if '--dir' in a else os.path.join(HERE, 'out', 'head')
    names = sorted(n for n in os.listdir(png_root) if os.path.isdir(os.path.join(png_root, n)))
    rows = (len(names) + cols - 1) // cols
    W, H = cols * CELL_W, rows * CELL_H
    sheet = checker(W, H, 12)
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        cx, cy = (i % cols) * CELL_W, (i // cols) * CELL_H
        cell = os.path.join(png_root, n)
        pngs = sorted(p for p in os.listdir(cell) if p.endswith('.png'))
        first = next((p for p in pngs if p.startswith('d1_c')), pngs[0] if pngs else None)
        d.rectangle([cx + 1, cy + 1, cx + CELL_W - 2, cy + CELL_H - 2], outline=(96, 104, 116))
        if first:
            im = Image.open(os.path.join(cell, first)).convert('RGBA')
            k = min(3, max(1, (CELL_W - 2 * PAD) // max(1, im.width)))
            im = im.resize((im.width * k, im.height * k), Image.NEAREST)
            sheet.paste(im, (cx + (CELL_W - im.width) // 2,
                             cy + PAD + (CELL_H - 26 - im.height) // 2), im)
        d.text((cx + PAD, cy + CELL_H - 20), n, fill=(228, 232, 238))
        d.text((cx + PAD, cy + CELL_H - 10), '%d img' % len(pngs), fill=(150, 156, 166))
    sheet.save(out)
    print('wrote %s  (%dx%d, %d files)' % (out, W, H, len(names)))


if __name__ == '__main__':
    main()
