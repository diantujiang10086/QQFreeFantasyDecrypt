# -*- coding: utf-8 -*-
"""估算 sketchmap 底图与 .msk 碰撞网格之间的平移偏差（纯 numpy FFT 互相关）。

用法：
    python mapalign.py --probe pw21000 qw0001 pw22901    # 只测这几张，打印
    python mapalign.py --scan [--step N]                 # 全量扫描 → out/map_align.json

原理：底图里 alpha>0 = 岛（可走区域的外扩），.msk 里 bit0=0 = 可走。
把两者缩到同一尺寸后用互相关找最佳平移；峰位就是底图相对网格的偏移（像素）。
"""
import json
import os
import sys

import numpy as np
from PIL import Image

import maps

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'map_align.json')
W = 240                      # 相关计算用的宽度（原图 720 → 240）


def _walk_mask(name, size):
    m = maps.mask(name)
    if not m or len(m['cells']) != m['w'] * m['h']:
        return None
    cells = np.frombuffer(bytes(m['cells']), dtype=np.uint8).reshape(m['h'], m['w'])
    walk = (cells & 1) == 0
    im = Image.fromarray((walk * 255).astype('uint8'))
    im = im.resize(size, Image.NEAREST)
    return np.asarray(im) > 127


def align(name):
    sk = maps.sketch(name)
    if sk is None:
        return None
    h = max(1, int(round(sk.height * W / sk.width)))
    size = (W, h)
    alpha = np.asarray(sk.convert('RGBA').resize(size, Image.NEAREST))[:, :, 3] > 8
    walk = _walk_mask(name, size)
    if walk is None:
        return None

    a = alpha.astype(np.float32)
    b = walk.astype(np.float32)
    sh = (h * 2, W * 2)
    fa = np.fft.rfft2(a, sh)
    fb = np.fft.rfft2(b, sh)
    corr = np.fft.irfft2(np.conj(fa) * fb, sh)
    iy, ix = np.unravel_index(int(np.argmax(corr)), corr.shape)
    dy = iy if iy <= sh[0] // 2 else iy - sh[0]
    dx = ix if ix <= sh[1] // 2 else ix - sh[1]
    peak = float(corr[iy, ix])
    base = float(corr[0, 0])
    return {'dx': int(dx), 'dy': int(dy), 'peak': round(peak, 1), 'base': round(base, 1),
            'size': list(size)}


def main():
    args = sys.argv[1:]
    if '--probe' in args:
        i = args.index('--probe')
        for n in args[i + 1:]:
            print(n, align(n))
        return
    step = 1
    if '--step' in args:
        step = max(1, int(args[args.index('--step') + 1]))
    names = maps.stems_with_sketch()[::step]
    res, bad = {}, 0
    for k, n in enumerate(names):
        try:
            r = align(n)
        except Exception:                              # noqa: BLE001
            r, bad = None, bad + 1
        if r:
            res[n] = r
        if (k + 1) % 50 == 0:
            print('...%d/%d' % (k + 1, len(names)), flush=True)
    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    moved = sum(1 for r in res.values() if r['dx'] or r['dy'])
    print('aligned %d / %d (moved %d, failed %d) -> %s'
          % (len(res), len(names), moved, bad, OUT))


if __name__ == '__main__':
    main()
