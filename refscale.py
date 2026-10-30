"""Try candidate bodies against the reference mask at several scales.

  python refscale.py --ref 0 --names npc1000101,npc509001 [--scales 1.0,1.1,1.2,1.3,1.4,1.5]

The game may render avatars at a zoom factor; a nearest-neighbour resize keeps palette
colours exact, so the 17-grid mask stays valid and only the silhouette scale changes.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402

REF = os.path.join(HERE, 'out', 'ref')
SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def alpha0(path):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    if not r.get('ok'):
        return None
    pre, w, h, px, bpp = r['frames'][0]
    if not px:
        return None
    return np.asarray(dimg.to_image(d, px, w, h, bpp))[:, :, 3]


def fit(mask, tpl):
    H, W = mask.shape
    th, tw = tpl.shape
    if th > H or tw > W:
        return 0.0, -1, -1
    fh, fw = H + th - 1, W + tw - 1
    F = np.fft.rfft2(mask, (fh, fw)) * np.conj(np.fft.rfft2(tpl[::-1, ::-1], (fh, fw)))
    cc = np.rint(np.fft.irfft2(F, (fh, fw))[th - 1:th - 1 + H - th + 1, tw - 1:tw - 1 + W - tw + 1])
    inter = np.maximum(cc, 0)
    union = float(tpl.sum()) + float(mask.sum()) - inter
    iou = inter / np.maximum(union, 1)
    y, x = np.unravel_index(int(np.argmax(iou)), iou.shape)
    return float(iou[y, x]), int(x), int(y)


def main():
    a = sys.argv[1:]
    idx = int(a[a.index('--ref') + 1]) if '--ref' in a else 0
    names = (a[a.index('--names') + 1] if '--names' in a else 'npc1000101').split(',')
    scales = [float(v) for v in (a[a.index('--scales') + 1] if '--scales' in a else
                                 '1.0,1.1,1.2,1.3,1.4,1.5,0.9').split(',')]
    mask = (np.asarray(Image.open(os.path.join(REF, ALL[idx])).convert('RGB')).astype(np.int16)
            % 17 == 0).all(axis=2).astype(float)
    print('ref %-8s mask=%d' % (esc(ALL[idx]), int(mask.sum())))
    for n in names:
        al = alpha0(os.path.join(SRC, n + '.gsn'))
        if al is None:
            print('  %-14s (no frame 0)' % n)
            continue
        base = Image.fromarray(al)
        best = None
        for s in scales:
            im = base.resize((max(1, round(base.width * s)), max(1, round(base.height * s))), Image.NEAREST)
            t = (np.asarray(im) > 40).astype(float)
            iou, x, y = fit(mask, t)
            if best is None or iou > best[0]:
                best = (iou, s, x, y, t.shape[1], t.shape[0])
            print('  %-14s scale %.2f  iou %.3f  at (%2d,%2d)  %dx%d'
                  % (n, s, iou, x, y, t.shape[1], t.shape[0]))
        print('  => best %-14s scale %.2f iou %.3f' % (n, best[1], best[0]))


if __name__ == '__main__':
    main()
