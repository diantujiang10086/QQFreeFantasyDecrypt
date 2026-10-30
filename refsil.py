"""Print the reference render as a character/background ASCII map (1 char per pixel).

Background is approximated by the beige/warm neutral family measured in refprobe.py;
everything else is drawn with a density symbol so the silhouette can be read as text.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'out', 'ref')


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def dump(name, step=1):
    a = np.asarray(Image.open(os.path.join(REF, name)).convert('RGB'), dtype=np.int16)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    lum = (R + G + B) / 3.0
    beige = (np.abs(R - G) < 30) & ((R - B) > 0) & ((R - B) < 70) & (lum > 120)
    blue = (B > R + 10)
    skin = (R > 200) & (G > 140) & (G < 230) & (B > 120) & (B < 200) & (R > G + 20)
    dark = lum < 110
    out = np.full(a.shape[:2], ' ', dtype='<U1')
    out[beige] = '.'
    out[~beige] = '#'
    out[blue] = 'B'
    out[skin] = 'S'
    out[dark] = 'K'
    print('file', esc(name), a.shape)
    for y in range(0, a.shape[0], step):
        print('%3d %s' % (y, ''.join(out[y, ::step])))


if __name__ == '__main__':
    names = sorted(n for n in os.listdir(REF) if n.endswith('.png'))
    tgt = sys.argv[1] if len(sys.argv) > 1 else None
    for n in names:
        if tgt is None or tgt in n:
            dump(n)
            break
