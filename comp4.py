"""Render the layered avatar (body + head + cap + face) at a given neck joint.

  python comp4.py [--body npc1000101] [--head head0101] [--cap cap0101] [--face face0101]
                  [--joint 26,31] [--ref 0] [--zoom 5]

All head-slot layers (head/cap/face) hang off one joint, so their canvases are placed by
aligning their pivots to that joint.  The joint is expressed in *body canvas* coordinates;
the body's own pivot (usually the ground line) stays fixed.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
REF = os.path.join(HERE, 'out', 'ref')


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def load(path):
    d = open(path, 'rb').read()
    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    W, H, cx, cy = pw[3], pw[4], pw[5], pw[6]
    r = dimg.parse(d)
    if r.get('ok'):
        pre, w, h, px, bpp = r['frames'][0]
        im = dimg.to_image(d, px, w, h, bpp)
    else:
        recs, extra, k = headtool.segment(d)
        p, w, h, s, f = recs[0]
        im = dimg.to_image(d, p + 16, w, h, s // w)
    return dict(img=im.convert('RGBA'), W=W, H=H, cx=cx, cy=cy, w=im.width, h=im.height)


def main():
    a = sys.argv[1:]
    def opt(k, d):
        return a[a.index(k) + 1] if k in a else d
    body = opt('--body', 'npc1000101')
    head = opt('--head', 'head0101')
    cap = opt('--cap', 'cap0101')
    face = opt('--face', 'face0101')
    joint = tuple(int(v) for v in opt('--joint', '26,31').split(','))
    zoom = int(opt('--zoom', 5))
    idx = int(opt('--ref', 0))

    L = [load(os.path.join(SRC, 'npc', body + '.gsn'))]
    names = ['body']
    for sub, stem in (('head', head), ('cap', cap), ('face', face)):
        if stem == '-':
            L.append(None)
            names.append('-')
            continue
        L.append(load(os.path.join(SRC, sub, stem + '.gsn')))
        names.append(stem)
    print('layers', names)
    print('canvases', [(x['W'], x['H'], x['cx'], x['cy'], x['w'], x['h']) if x else None for x in L])

    # composite in body-canvas space, padded
    pad = 30
    cw, ch = L[0]['W'] + 2 * pad, L[0]['H'] + 2 * pad
    tiles = []
    for k in range(1, len(L) + 1):
        c = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
        # body: its canvas at (pad, pad)
        c.alpha_composite(L[0]['img'], (pad + 0, pad + 0))
        for lay in L[1:k]:
            if lay is None:
                continue
            c.alpha_composite(lay['img'], (pad + joint[0] - lay['cx'], pad + joint[1] - lay['cy']))
        tiles.append((names[k - 1] if k > 1 else 'body', c))

    # reference next to the tiles for comparison
    refim = None
    if idx >= 0:
        names_ref = sorted(n for n in os.listdir(REF) if n.endswith('.png'))
        refim = Image.open(os.path.join(REF, names_ref[idx])).convert('RGB')

    scale = zoom
    tw, th = cw * scale, ch * scale
    n = len(tiles) + (1 if refim else 0)
    sheet = Image.new('RGB', (n * (tw + 8), th + 22), (44, 44, 50))
    x = 0
    if refim:
        r = refim.resize((refim.width * scale // 2, refim.height * scale // 2), Image.NEAREST)
        sheet.paste(r, (x + (tw - r.width) // 2, (th - r.height) // 2))
        x += tw + 8
    for label, im in tiles:
        rgb = Image.new('RGB', (cw, ch), (150, 150, 160))
        rgb.paste(im, (0, 0), im)
        sheet.paste(rgb.resize((tw, th), Image.NEAREST), (x, 0))
        x += tw + 8
    dst = os.path.join(HERE, 'out', 'comp4_%s_j%dx%d.png' % (esc(head).replace('.gsn', ''), joint[0], joint[1]))
    sheet.save(dst)
    print('wrote', esc(dst), 'sheet %dx%d tiles: %s' % (sheet.width, sheet.height, [t[0] for t in tiles]))


if __name__ == '__main__':
    main()
