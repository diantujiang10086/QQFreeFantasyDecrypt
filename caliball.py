"""Calibrate every reference render: place the known body frame and the head layer by exact pixels.

  python caliball.py [--head head2151]

The map below is the user's (m02600); body frames and head directions come from it.
Mirrored views flip both sprites horizontally.
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
BODY = 'npc1000101'

# (ref name, body frame, head dir, mirrored)
MAP = [
    ('\u524d',   4, 5, False),   # 前
    ('\u540e',   3, 4, False),   # 后
    ('\u5de6',   1, 2, False),   # 左
    ('\u53f3',   1, 2, True),    # 右
    ('\u5de6\u4e0a', 2, 3, False),   # 左上
    ('\u53f3\u4e0a', 2, 3, True),    # 右上
    ('\u5de6\u4e0b', 0, 1, False),   # 左下
    ('\u53f3\u4e0b', 0, 1, True),    # 右下
]


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def body_sprite(d, frame):
    r = dimg.parse(d)
    pre, w, h, px, bpp = r['frames'][frame]
    return dimg.to_image(d, px, w, h, bpp).convert('RGBA'), r


def head_sprite(d, rec_i):
    recs, extra, k = headtool.segment(d)
    p, w, h, s, f = recs[rec_i]
    return dimg.to_image(d, p + 16, w, h, s // w).convert('RGBA')


def search(ref, spr):
    arr = np.asarray(spr).astype(np.int32)
    m = arr[:, :, 3] > 200
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
    a = sys.argv[1:]
    head = a[a.index('--head') + 1] if '--head' in a else 'head2151'
    db = open(os.path.join(SRC, 'npc', BODY + '.gsn'), 'rb').read()
    dh = open(os.path.join(SRC, 'head', head + '.gsn'), 'rb').read()
    recs, extra, k = headtool.segment(dh)
    print('body %s draws=%d | head %s records=%d' % (BODY, len(dimg.parse(db)['frames']), head, len(recs)))
    deltas = []
    for name, bf, hd, mir in MAP:
        fn = name + '.png'
        path = os.path.join(REF, fn)
        if not os.path.exists(path):
            print('missing', esc(fn))
            continue
        ref = np.asarray(Image.open(path).convert('RGB')).astype(np.int32)
        bs, r = body_sprite(db, bf)
        hi = (2 * (hd - 1)) if len(recs) >= 2 * (dimg.u32(dh, 20) or 5) else (hd - 1)
        hi = (hd - 1) if len(recs) <= 5 else 2 * (hd - 1)
        hs = head_sprite(dh, hi)
        if mir:
            bs = bs.transpose(Image.FLIP_LEFT_RIGHT)
            hs = hs.transpose(Image.FLIP_LEFT_RIGHT)
        hb, bx, by, nb = search(ref, bs)
        hh, hx, hy, nh = search(ref, hs)
        print('%-6s %-18s body f%d %2dx%-2d -> (%2d,%2d) %5.1f%%   head d%d rec%-2d %2dx%-2d -> (%2d,%2d) %5.1f%%   delta (%+d,%+d)'
              % (esc(fn).replace('\\u', 'u'), 'mirror' if mir else '', bf, bs.width, bs.height, bx, by,
                 100.0 * hb / nb, hd, hi, hs.width, hs.height, hx, hy, 100.0 * hh / nh, hx - bx, hy - by))
        deltas.append((esc(fn), hx - bx, hy - by))

    print('\nhead delta relative to body sprite:')
    for n, dx, dy in deltas:
        print('   %-22s (%+d,%+d)' % (n, dx, dy))
    if deltas:
        xs = [d for _, d, _ in deltas]
        ys = [d for _, _, d in deltas]
        print('   spread x %d..%d   y %d..%d' % (min(xs), max(xs), min(ys), max(ys)))


if __name__ == '__main__':
    main()
