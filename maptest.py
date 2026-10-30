# -*- coding: utf-8 -*-
"""测试碰撞网格与底图之间的几何关系：原样 / 上下翻转 / 左右翻转 / 旋转 180°。"""
import numpy as np
from PIL import Image

import maps

W = 240


def _scores(name):
    sk = maps.sketch(name)
    if sk is None:
        return None
    h = max(1, int(round(sk.height * W / sk.width)))
    size = (W, h)
    alpha = np.asarray(sk.convert('RGBA').resize(size, Image.NEAREST))[:, :, 3] > 8
    m = maps.mask(name)
    cells = np.frombuffer(bytes(m['cells']), dtype=np.uint8).reshape(m['h'], m['w'])
    walk = (cells & 1) == 0
    im = Image.fromarray((walk * 255).astype('uint8')).resize(size, Image.NEAREST)
    base = np.asarray(im) > 127

    variants = {
        'identity': base,
        'flip_y': base[::-1, :],
        'flip_x': base[:, ::-1],
        'rot180': base[::-1, ::-1],
    }
    wf = 1.0 / max(1, int(walk.sum()))
    out = {}
    for k, v in variants.items():
        a = alpha.astype(np.float32)
        b = v.astype(np.float32)
        corr = float((a * b).sum())
        # 归一化：可走区域落在岛内的比例
        out[k] = round(corr / max(1.0, b.sum()), 4)
    return out, int(walk.sum()), int(alpha.sum())


if __name__ == '__main__':
    import sys
    for n in sys.argv[1:] or ['qw0001', 'pw21000', 'pw22901']:
        r = _scores(n)
        print(n, r)
