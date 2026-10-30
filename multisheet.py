"""Cross-sample head/body compositing sheet using a chin-anchor rule.

Rule under test: the head's bottom-centre (chin) is put at
    (body sprite centre x,  body sprite top + K)
so a taller head extends upwards instead of downwards.

  python multisheet.py --bodies npc1000101,npc1000102 --head head0101 --ks 27,31,35
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import combo  # noqa: E402
import dimg  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

SRC = combo.SRC
ZOOM = 3


def body_sprite(path, idx=0):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    if not r['ok'] or idx >= len(r['frames']):
        return None
    pre, w, hh, px, bpp = r['frames'][idx]
    if px is None:
        return None
    return dimg.to_image(d, px, w, hh, bpp)


def head_sprite(path, dirno=1):
    d, recs, r = combo.recursive_records(path)
    k = 2 * (dirno - 1) if len(recs) >= 10 else (dirno - 1)
    if k >= len(recs):
        return None
    w, h, bpp, px = recs[k]
    return dimg.to_image(d, px, w, h, bpp)


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
              else 'npc1000101,npc1000102,npc1000103,npc1000104').split(',')
    head = a[a.index('--head') + 1] if '--head' in a else 'head0101'
    ks = [int(v) for v in (a[a.index('--ks') + 1] if '--ks' in a else '27,31,35').split(',')]
    dirno = int(a[a.index('--dir') + 1]) if '--dir' in a else 1
    frame = int(a[a.index('--frame') + 1]) if '--frame' in a else 0

    hd = head_sprite(os.path.join(SRC, 'head', head + '.gsn'), dirno)
    hw, hh = hd.size
    rows = []
    for nm in bodies:
        im = body_sprite(os.path.join(SRC, 'npc', nm + '.gsn'), frame)
        if im is not None:
            rows.append((nm, im))
    print('rows:', len(rows), 'head', head, hd.size, 'ks', ks)
    if not rows:
        return

    cw = max(im.width for _, im in rows) * ZOOM
    ch = max(im.height for _, im in rows) * ZOOM
    gx, gy = 8, 12
    cols = len(ks) + 1
    sheet = Image.new('RGBA', (6 + cols * (cw + gx),
                               26 + len(rows) * (ch + gy + 14)), (26, 28, 32, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((6, 7), '%s dir%d (chin at body top + K, centred) on bodies; col0 = body' % (head, dirno),
            fill=(240, 244, 248))
    for ri, (nm, b) in enumerate(rows):
        y = 26 + ri * (ch + gy + 14)
        tiles = [(b, '%s %dx%d' % (nm, b.width, b.height))]
        for K in ks:
            im = canvas(b.width, b.height)
            im.paste(b, (0, 0), b)
            x = round(b.width / 2 - hw / 2)
            top = K - hh
            im.paste(hd, (x, top), hd)
            tiles.append((im, 'K=%d dx=%d dy=%d' % (K, x, top)))
        for ci, (im, lab) in enumerate(tiles):
            x = 6 + ci * (cw + gx)
            sheet.paste(im.resize((im.width * ZOOM, im.height * ZOOM), Image.NEAREST), (x, y))
            dr.text((x, y + ch + 1), lab, fill=(220, 226, 236))
    out = os.path.join(HERE, 'out', 'multi_%s.png' % head)
    sheet.save(out)
    print('wrote', out, sheet.size)


if __name__ == '__main__':
    main()
