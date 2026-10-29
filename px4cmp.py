# -*- coding: utf-8 -*-
"""4 字节像素通道序对照图：同一帧按多种 (r,g,b,a) 取序渲染成一条对比图。

python px4cmp.py [file] [frame] [--out path] [--scale N]
默认 npc539801t.gsn 第 0 帧，输出 out/px4cmp.png。
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))

import dimg                                   # noqa: E402

ORDERS = {
    'BGRA (2,1,0,3)': (2, 1, 0, 3),   # D3DFMT_A8R8G8B8 内存序，当前默认
    'RGBA (0,1,2,3)': (0, 1, 2, 3),
    'ARGB (1,2,3,0)': (1, 2, 3, 0),
    'ABGR (3,2,1,0)': (3, 2, 1, 0),
    'GRBA (1,0,2,3)': (1, 0, 2, 3),
    'BGR A? (2,1,0,0)': (2, 1, 0, 0),
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    name = args[0] if args else 'npc539801t.gsn'
    k = int(args[1]) if len(args) > 1 else 0
    out = os.path.join(HERE, 'out', 'px4cmp.png')
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]
    scale = int(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 2

    p = name if os.path.isabs(name) else os.path.join(dimg.SRC, name)
    d = open(p, 'rb').read()
    r = dimg.parse(d)
    assert r['ok'], r
    frames = [f for f in r['frames'] if f[3] is not None]
    pre, w, h, px, bpp = frames[k]
    assert bpp == 4, f'{name} frame {k} is bpp={bpp}'
    raw = np.frombuffer(d, dtype=np.uint8, count=4 * w * h, offset=px).reshape(h, w, 4)

    # 只看有像素区域，裁掉四周全透明
    alpha = raw[:, :, 3]
    ys, xs = np.nonzero(alpha)
    y0, y1 = max(0, ys.min() - 2), min(h, ys.max() + 3)
    x0, x1 = max(0, xs.min() - 2), min(w, xs.max() + 3)

    tiles = []
    for label, (ro, go, bo, ao) in ORDERS.items():
        img = np.empty((h, w, 4), dtype=np.uint8)
        img[:, :, 0] = raw[:, :, ro]
        img[:, :, 1] = raw[:, :, go]
        img[:, :, 2] = raw[:, :, bo]
        img[:, :, 3] = raw[:, :, ao]
        crop = img[y0:y1, x0:x1]
        im = Image.fromarray(crop, 'RGBA')
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        tile = Image.new('RGBA', (im.width, im.height + 20), (24, 24, 28, 255))
        tile.alpha_composite(im, (0, 20))
        ImageDraw.Draw(tile).text((4, 4), label, fill=(220, 220, 220, 255))
        tiles.append(tile)

    W = sum(t.width for t in tiles) + 8 * (len(tiles) - 1)
    H = max(t.height for t in tiles)
    sheet = Image.new('RGBA', (W, H), (12, 12, 14, 255))
    x = 0
    for t in tiles:
        sheet.alpha_composite(t, (x, 0))
        x += t.width + 8
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    print(f'{name} frame {k}: {w}x{h} bpp=4 crop=({x0},{y0})-({x1},{y1}) '
          f'-> {out} ({sheet.width}x{sheet.height})')
    # 顺带打印不透明像素三通道均值，供“暖色”参考
    op = raw[alpha > 200]
    for label, (ro, go, bo, ao) in list(ORDERS.items())[:4]:
        m = op[:, [ro, go, bo]].mean(axis=0)
        print(f'  {label:18s} mean R={m[0]:6.1f} G={m[1]:6.1f} B={m[2]:6.1f} '
              f'-> R-B={m[0]-m[2]:+6.1f}')


main()
