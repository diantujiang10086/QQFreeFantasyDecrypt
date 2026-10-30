"""Placement sweep: put the head on the body over a small dx/dy grid and write one
sheet so the exact offset can be picked by eye; ASCII dump for the leading guesses.

Usage: python sweep.py [--dx 6,7,8,9,10] [--dy -29,-28,...,-22] [--ascii 9x-27 7x-25]
"""
import os
import sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import combo  # noqa: E402

RAMP = ' .:-=+*#%@'


def checker(w, h, s=8):
    img = Image.new('RGBA', (w, h), (52, 56, 62, 255))
    dr = ImageDraw.Draw(img)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if ((x // s) + (y // s)) % 2:
                dr.rectangle([x, y, x + s - 1, y + s - 1], fill=(74, 80, 88, 255))
    return img


def ascii_img(img, width=36):
    step = max(1, img.width // width)
    sy = step * 2
    px = img.load()
    out = []
    for y in range(0, img.height, sy):
        line = []
        for x in range(0, img.width, step):
            hit = n = 0
            for yy in range(y, min(y + sy, img.height)):
                for xx in range(x, min(x + step, img.width)):
                    if px[xx, yy][3] > 8:
                        hit += 1
                    n += 1
            line.append(RAMP[min(9, hit * 10 // max(1, n))] if hit else ' ')
        out.append('%3d|%s' % (y, ''.join(line)))
    return '\n'.join(out)


def main():
    a = sys.argv[1:]
    dxs = [int(v) for v in (a[a.index('--dx') + 1] if '--dx' in a else '6,7,8,9,10').split(',')]
    dys = [int(v) for v in (a[a.index('--dy') + 1] if '--dy' in a
                            else '-30,-29,-28,-27,-26,-25,-24,-23,-22').split(',')]
    zoom = 4
    b = combo.sprite(combo.BODY, 0)
    h = combo.sprite(combo.HEAD, 0)
    tw, th = b['img'].width * zoom, b['img'].height * zoom
    gx, gy = 4, 22
    sheet = Image.new('RGBA', (6 + len(dys) * (tw + gx), 26 + len(dxs) * (th + gy)), (28, 30, 34, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((8, 8), 'dx=%s (rows)  dy=%s (cols)   (%s + %s)'
            % (dxs, dys, os.path.basename(combo.BODY), os.path.basename(combo.HEAD)),
            fill=(240, 244, 248))
    for ri, dx in enumerate(dxs):
        for ci, dy in enumerate(dys):
            img, _ = combo.compose(b['img'], h['img'], 1.0, (dx, dy))
            x = 6 + ci * (tw + gx)
            y = 26 + ri * (th + gy)
            bg = checker(img.width * zoom, img.height * zoom)
            sheet.paste(bg, (x, y))
            big = img.resize((img.width * zoom, img.height * zoom), Image.NEAREST)
            sheet.paste(big, (x, y), big)
            dr.text((x, y + th + 2), 'dy%+d' % dy, fill=(230, 235, 242))
        dr.text((6, 26 + ri * (th + gy) + 8), 'dx=%d' % dx, fill=(255, 210, 120))
    p = os.path.join(HERE, 'out', 'sweep_sheet.png')
    sheet.save(p)
    print('wrote', p, sheet.size)

    for spec in (a[a.index('--ascii') + 1].split() if '--ascii' in a else []):
        dx, dy = spec.split('x')
        img, _ = combo.compose(b['img'], h['img'], 1.0, (int(dx), int(dy)))
        print('\n=== dx=%s dy=%s  %dx%d ===' % (dx, dy, img.width, img.height))
        print(ascii_img(img))


if __name__ == '__main__':
    main()
