"""Build the 'compose' view: reference renders next to the .gsn recomposite, plus sprite browsers."""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402
import paths

SRC = paths.sub('data/official/avatar')
OUT = os.path.join(HERE, 'out')
REF = os.path.join(OUT, 'ref')
DST = os.path.join(OUT, 'compose')
BODY = 'npc1000101'

MAP = [
    ('\u524d', 4, 5, False), ('\u540e', 3, 4, False), ('\u5de6', 1, 2, False), ('\u53f3', 1, 2, True),
    ('\u5de6\u4e0a', 2, 3, False), ('\u53f3\u4e0a', 2, 3, True),
    ('\u5de6\u4e0b', 0, 1, False), ('\u53f3\u4e0b', 0, 1, True),
]


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def search(ref, spr, thr=200):
    arr = np.asarray(spr).astype(np.int32)
    m = arr[:, :, 3] > thr
    rgb = arr[:, :, :3][m]
    th, tw = m.shape
    H, W = ref.shape[:2]
    best = (-1, -1, -1)
    for y in range(0, max(1, H - th + 1)):
        for x in range(0, max(1, W - tw + 1)):
            hits = int(np.all(ref[y:y + th, x:x + tw][m] == rgb, axis=1).sum())
            if hits > best[0]:
                best = (hits, x, y)
    return best[0], best[1], best[2], int(m.sum())


def main():
    os.makedirs(DST, exist_ok=True)
    db = open(os.path.join(SRC, 'npc', BODY + '.gsn'), 'rb').read()
    rb = dimg.parse(db)
    head = 'head2151'
    dh = open(os.path.join(SRC, 'head', head + '.gsn'), 'rb').read()
    recs, extra, k = headtool.segment(dh)
    views = []
    for i, (name, bf, hd, mir) in enumerate(MAP):
        path = os.path.join(REF, name + '.png')
        if not os.path.exists(path):
            continue
        ref_im = Image.open(path).convert('RGB')
        ref = np.asarray(ref_im).astype(np.int32)
        pre, w, h, px, bpp = rb['frames'][bf]
        body = dimg.to_image(db, px, w, h, bpp).convert('RGBA')
        p, hw, hh, s, f = recs[hd - 1]
        head_im = dimg.to_image(dh, p + 16, hw, hh, s // w).convert('RGBA')
        best = None
        for bmir in ({True, False} if mir else {False}):
            for hmir in ({True, False} if mir else {False}):
                b2 = body.transpose(Image.FLIP_LEFT_RIGHT) if bmir else body
                h2 = head_im.transpose(Image.FLIP_LEFT_RIGHT) if hmir else head_im
                hb, bx, by, nb = search(ref, b2)
                hh2, hx, hy, nh = search(ref, h2)
                cand = (hb / nb + hh2 / nh, bmir, hmir, b2, bx, by, h2, hx, hy, hb, nb, hh2, nh)
                if best is None or cand[0] > best[0]:
                    best = cand
        s0, bmir, hmir, b2, bx, by, h2, hx, hy, hb, nb, hh2, nh = best
        comp = Image.new('RGBA', ref_im.size, (0, 0, 0, 0))
        comp.alpha_composite(b2, (bx, by))
        comp.alpha_composite(h2, (hx, hy))
        ca = np.asarray(comp)
        m = ca[:, :, 3] > 200
        exact = float(np.all(ca[:, :, :3][m] == ref[m], axis=1).mean())
        diff = np.abs(np.asarray(ref_im).astype(np.int32) - np.asarray(comp.convert('RGB')).astype(np.int32)).sum(axis=2)
        z = 3
        W, H = ref_im.size
        tile = Image.new('RGB', (W * 3 * z + 16, H * z + 22), (24, 24, 28))
        tile.paste(ref_im.resize((W * z, H * z), Image.NEAREST), (0, 22))
        bg = Image.new('RGB', ref_im.size, (24, 24, 28))
        bg.paste(comp.convert('RGB'), (0, 0), comp)
        tile.paste(bg.resize((W * z, H * z), Image.NEAREST), (W * z + 8, 22))
        tile.paste(Image.fromarray((255 - np.clip(diff * 3, 0, 255)).astype(np.uint8)).convert('RGB')
                   .resize((W * z, H * z), Image.NEAREST), (W * 2 * z + 16, 22))
        fn = 'v%d_%s.png' % (i, esc(name).replace('\\u', 'u'))
        tile.save(os.path.join(DST, fn))
        views.append(dict(name=name, png=fn, body='%s f%d' % (BODY, bf), head='%s d%d' % (head, hd),
                          mirror=bool(bmir or hmir), exact=round(100 * exact, 1),
                          at=[int(bx), int(by), int(hx), int(hy)]))
        print('%s %s -> %s exact %.1f%%' % (esc(name), fn, 'mirror' if (bmir or hmir) else '', 100 * exact))

    heads = []
    hp = os.path.join(OUT, 'head')
    for d in sorted(os.listdir(hp)):
        if not os.path.isdir(os.path.join(hp, d)):
            continue
        pngs = sorted(n for n in os.listdir(os.path.join(hp, d)) if n.endswith('.png'))
        if pngs:
            heads.append(dict(n=d, d1=pngs[0], all=pngs))
    npcs = [dict(f=n) for n in sorted(os.listdir(os.path.join(OUT, 'npc'))) if n.endswith('.png')]
    man = dict(views=views, heads=heads, npcs=npcs, body=BODY)
    with open(os.path.join(DST, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False)
    print('heads %d  npcs %d  -> %s' % (len(heads), len(npcs), esc(os.path.join(DST, 'manifest.json'))))


if __name__ == '__main__':
    main()
