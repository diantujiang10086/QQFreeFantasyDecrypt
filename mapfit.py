# -*- coding: utf-8 -*-
"""检查每张地图的「可走区域」有多少落在底图不透明区域内（低分=底图与网格不匹配）。"""
import json
import os

import numpy as np
from PIL import Image

import maps

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'map_fit.json')
W = 180


def score(name):
    sk = maps.sketch(name)
    m = maps.mask(name)
    if sk is None or m is None:
        return None
    if len(m['cells']) != m['w'] * m['h']:
        return None
    h = max(1, int(round(sk.height * W / sk.width)))
    size = (W, h)
    alpha = np.asarray(sk.convert('RGBA').resize(size, Image.NEAREST))[:, :, 3] > 8
    cells = np.frombuffer(bytes(m['cells']), dtype=np.uint8).reshape(m['h'], m['w'])
    walk = (cells & 1) == 0
    im = Image.fromarray((walk * 255).astype('uint8')).resize(size, Image.NEAREST)
    w = np.asarray(im) > 127
    tot = int(w.sum())
    if not tot:
        return {'inside': 0.0, 'walk': 0, 'alpha': int(alpha.sum())}
    return {'inside': round(float((w & alpha).sum()) / tot, 4), 'walk': tot,
            'alpha': int(alpha.sum()), 'aspect_ok': abs((sk.width / sk.height) - (m['w'] / m['h'])) < 0.05}


def main():
    names = maps.stems_with_sketch()
    res = {}
    for i, n in enumerate(names):
        try:
            r = score(n)
        except Exception:                        # noqa: BLE001
            r = None
        if r:
            res[n] = r
        if (i + 1) % 60 == 0:
            print('...%d/%d' % (i + 1, len(names)), flush=True)
    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    bad = sorted((v['inside'], k) for k, v in res.items())[:25]
    print('scanned', len(res), '->', OUT)
    print('worst:', bad)


if __name__ == '__main__':
    main()
