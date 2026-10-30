"""Contact sheets for out/backpack: one representative sprite per file."""
import math
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(HERE, 'out', 'backpack')
OUT = os.path.join(HERE, 'out')

COLS, ROWS = 12, 8
CW, CH = 132, 176


def reps():
    out = []
    for stem in sorted(os.listdir(DST)):
        p = os.path.join(DST, stem)
        if not os.path.isdir(p):
            continue
        pngs = sorted(f for f in os.listdir(p) if f.endswith('.png'))
        if not pngs:
            continue
        out.append((stem, os.path.join(p, pngs[0])))
    return out


def main():
    items = reps()
    per = COLS * ROWS
    pages = int(math.ceil(len(items) / per))
    for pg in range(pages):
        chunk = items[pg * per:(pg + 1) * per]
        sheet = Image.new('RGBA', (COLS * CW, ROWS * CH), (40, 42, 49, 255))
        dr = ImageDraw.Draw(sheet)
        for k, (stem, path) in enumerate(chunk):
            im = Image.open(path).convert('RGBA')
            w, h = im.size
            sc = min((CW - 8) / w, (CH - 26) / h, 4.0)
            nw, nh = max(1, int(w * sc)), max(1, int(h * sc))
            im = im.resize((nw, nh), Image.NEAREST)
            cx = (k % COLS) * CW
            cy = (k // COLS) * CH
            # checkerboard
            for yy in range(0, CH, 8):
                for xx in range(0, CW, 8):
                    if ((xx // 8) + (yy // 8)) % 2 == 0:
                        dr.rectangle([cx + xx, cy + yy, cx + xx + 7, cy + yy + 7], fill=(72, 74, 82, 255))
            sheet.alpha_composite(im, (cx + (CW - nw) // 2, cy + (CH - 22 - nh) // 2))
            dr.text((cx + 4, cy + CH - 18), stem, fill=(230, 230, 230, 255))
        out = os.path.join(OUT, 'backpack_sheet-%d.png' % (pg + 1))
        sheet.convert('RGB').save(out)
        print('sheet', out, sheet.size)
    print('files %d, pages %d' % (len(items), pages))


if __name__ == '__main__':
    main()
