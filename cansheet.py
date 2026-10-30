"""Canvas-space compositing sheet.

Every part file carries its own canvas (W,H) and pivot (cx,cy).  The body sprite is
pasted at its stored canvas position (first record prefix: cy, x, y, 0), and the head
is pasted so that its own pivot lands at (body_cx, body_cy - d) for a few d values.

  python cansheet.py --bodies npc1000101,npc1000201,npc1000301 --head head0101 --ds 34,40,46
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import combo  # noqa: E402
import dimg  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

SRC = combo.SRC
ZOOM = 3


def w32(d, off, n):
    return [struct.unpack_from('<i', d, off + 4 * j)[0] for j in range(n)]


def part(path, frame=0):
    d = open(path, 'rb').read()
    h = dimg.head(d)
    pre = w32(d, 24, 9)
    pref = w32(d, 60, 4)
    r = dimg.parse(d)
    if r['ok'] and frame < len(r['frames']):
        _, w, hh, px, bpp = r['frames'][frame]
        img = dimg.to_image(d, px, w, hh, bpp)
        return {'img': img, 'W': pre[3], 'H': pre[4], 'cx': pre[5], 'cy': pre[6],
                'x': pref[1], 'y': pref[2]}
    d2, recs, _ = combo.recursive_records(path)
    k = frame
    w, hh, bpp, px = recs[k]
    return {'img': dimg.to_image(d2, px, w, hh, bpp), 'W': pre[3], 'H': pre[4],
            'cx': pre[5], 'cy': pre[6], 'x': pref[1], 'y': pref[2]}


def canvas(w, h):
    im = Image.new('RGBA', (w, h), (56, 60, 66, 255))
    dr = ImageDraw.Draw(im)
    for y in range(0, h, 10):
        for x in range(0, w, 10):
            if ((x // 10) + (y // 10)) % 2:
                dr.rectangle([x, y, x + 9, y + 9], fill=(76, 82, 90, 255))
    return im


def main():
    a = sys.argv[1:]
    bodies = (a[a.index('--bodies') + 1] if '--bodies' in a
              else 'npc1000101,npc1000201,npc1000301').split(',')
    head = a[a.index('--head') + 1] if '--head' in a else 'head0101'
    ds = [int(v) for v in (a[a.index('--ds') + 1] if '--ds' in a else '34,40,46').split(',')]
    hp = part(os.path.join(SRC, 'head', head + '.gsn'))
    print('head %s canvas %dx%d pivot (%d,%d) sprite %dx%d at (%d,%d)'
          % (head, hp['W'], hp['H'], hp['cx'], hp['cy'], hp['img'].width, hp['img'].height, hp['x'], hp['y']))

    rows = []
    for nm in bodies:
        p = part(os.path.join(SRC, 'npc', nm + '.gsn'))
        print('body %-12s canvas %dx%d pivot (%d,%d) sprite %dx%d at (%d,%d)'
              % (nm, p['W'], p['H'], p['cx'], p['cy'], p['img'].width, p['img'].height, p['x'], p['y']))
        rows.append((nm, p))
    cw = max(r[1]['W'] for r in rows) * ZOOM
    ch = max(r[1]['H'] for r in rows) * ZOOM
    gx, gy = 8, 12
    cols = len(ds) + 1
    sheet = Image.new('RGBA', (6 + cols * (cw + gx), 26 + len(rows) * (ch + gy + 14)),
                      (26, 28, 32, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((6, 7), '%s pivot at (body_cx, body_cy - d); col0 = body only' % head, fill=(240, 244, 248))
    for ri, (nm, b) in enumerate(rows):
        y = 26 + ri * (ch + gy + 14)
        base = canvas(b['W'], b['H'])
        base.paste(b['img'], (b['x'], b['y']), b['img'])
        tiles = [(base, nm)]
        for dv in ds:
            im = base.copy()
            hx = b['cx'] - hp['cx'] + hp['x']
            hy = b['cy'] - dv - hp['cy'] + hp['y']
            im.paste(hp['img'], (hx, hy), hp['img'])
            tiles.append((im, 'd=%d -> (%d,%d)' % (dv, hx, hy)))
        for ci, (im, lab) in enumerate(tiles):
            x = 6 + ci * (cw + gx)
            sheet.paste(im.resize((im.width * ZOOM, im.height * ZOOM), Image.NEAREST), (x, y))
            dr.text((x, y + ch + 1), lab, fill=(220, 226, 236))
    out = os.path.join(HERE, 'out', 'can_%s.png' % head)
    sheet.save(out)
    print('wrote', out, sheet.size)


if __name__ == '__main__':
    main()
