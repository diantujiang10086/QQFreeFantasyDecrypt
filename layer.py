"""Compose the avatar the way the engine stacks layers, then fit it to the reference.

  python layer.py [--ref 0] [--body npc1000101] [--head head0101] [--cap cap0101]
                  [--face face0101] [--dir 1] [--search]

Layers (body / head / cap / face) are placed by aligning their pivots: head, cap and face
all hang off the same neck joint, the body defines the canvas.  The joint position is
searched over a grid; the composite alpha is compared with the reference foreground mask
(IoU), and the best and the current candidates are written next to the reference.
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402
import paths

REF = os.path.join(HERE, 'out', 'ref')
SRC = paths.sub('data/official/avatar')
SKIN = paths.sub('data/official/avatar')
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def fg_mask(im, tol=60):
    a = np.asarray(im.convert('RGB')).astype(np.int16)
    h, w = a.shape[:2]
    seed = a[0, 0]
    seen = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        q.append((0, x))
        q.append((h - 1, x))
    for y in range(h):
        q.append((y, 0))
        q.append((y, w - 1))
    while q:
        y, x = q.popleft()
        if y < 0 or x < 0 or y >= h or x >= w or seen[y, x]:
            continue
        if np.abs(a[y, x] - seed).sum() > tol * 3:
            continue
        seen[y, x] = True
        q.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    return ~seen


def load(path):
    """-> (Image RGBA sprite, canvas W, H, pivot x, y)"""
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
    return im.convert('RGBA'), W, H, cx, cy


def join(files, out_w=240, out_h=300, origin=(0, 0)):
    """files = [(sprite, canvas_w, canvas_h, pivot_x, pivot_y, tx, ty)] ; tx,ty = where the
    pivot goes, in composite pixels (origin is added, default none)."""
    canvas = Image.new('RGBA', (out_w, out_h), (0, 0, 0, 0))
    for im, W, H, cx, cy, tx, ty in files:
        canvas.alpha_composite(im, (origin[0] + tx - cx, origin[1] + ty - cy))
    return canvas


def iou(a, b):
    """bbox-aligned silhouette comparison: crop each mask to its own bbox, then pad."""
    def crop(m):
        m = m.astype(bool)
        ys, xs = np.where(m)
        if len(ys) == 0:
            return m
        return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    A, B = crop(a), crop(b)
    h = max(A.shape[0], B.shape[0])
    w = max(A.shape[1], B.shape[1])
    def pad(m):
        out = np.zeros((h, w), bool)
        out[:m.shape[0], :m.shape[1]] = m
        return out
    A, B = pad(A), pad(B)
    inter = float((A & B).sum())
    union = float((A | B).sum())
    return inter / union if union else 0.0


def main():
    a = sys.argv[1:]
    def opt(k, dflt):
        return a[a.index(k) + 1] if k in a else dflt
    idx = int(opt('--ref', 0))
    body, head, cap, face = opt('--body', 'npc1000101'), opt('--head', 'head0101'), opt('--cap', 'cap0101'), opt('--face', 'face0101')
    name = ALL[idx]
    rimg = Image.open(os.path.join(REF, name)).convert('RGB')
    rmask = fg_mask(rimg)

    b = load(os.path.join(SRC, 'npc', body + '.gsn'))
    parts = [b]
    for sub, stem in (('head', head), ('cap', cap), ('face', face)):
        if stem and stem != '-':
            parts.append(load(os.path.join(SRC, sub, stem + '.gsn')))
    print('layers:', [(p[1], p[2], p[3], p[4]) for p in parts])

    # body: pivot at body pivot; head/cap/face: pivots at the same neck joint
    bx, by = 110, 210
    stack = [(parts[0][0], *parts[0][1:], bx, by)]
    best = None
    for jx in range(60, 160, 2):
        for jy in range(60, 200, 2):
            st = stack + [(p[0], *p[1:], jx, jy) for p in parts[1:]]
            im = join(st)
            arr = np.asarray(im)[:, :, 3] > 40
            s = iou(arr, rmask)
            if best is None or s > best[0]:
                best = (s, jx, jy)
    print('best joint (%d,%d) iou=%.3f' % (best[1], best[2], best[0]))
    st = stack + [(p[0], *p[1:], best[1], best[2]) for p in parts[1:]]
    im = join(st)
    save_pair(rimg, im, 'layer_best', best[1], best[2], best[0])


def fit(rmask, cmask):
    """crop both to their bbox and pad to a common size"""
    def crop(m):
        ys, xs = np.where(m)
        if len(ys) == 0:
            return m
        return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    a, b = crop(rmask), crop(cmask)
    h = max(a.shape[0], b.shape[0])
    w = max(a.shape[1], b.shape[1])
    def pad(m):
        out = np.zeros((h, w), bool)
        out[:m.shape[0], :m.shape[1]] = m
        return out
    return pad(b)


def save_pair(rimg, comp, tag, jx=None, jy=None, score=None):
    h = max(rimg.height, comp.height)
    both = Image.new('RGB', (rimg.width + comp.width + 12, h), (46, 46, 52))
    both.paste(rimg, (0, 0))
    both.paste(comp.convert('RGB'), (rimg.width + 12, 0), comp)
    ov = rimg.copy()
    ov.paste(comp.convert('RGB'), (0, 0), comp)
    out = Image.new('RGB', (both.width + rimg.width + 12, h), (46, 46, 52))
    out.paste(both, (0, 0))
    out.paste(ov, (both.width + 12, 0))
    dst = os.path.join(HERE, 'out', '%s%s.png' % (tag, '' if jx is None else '_j%dx%d' % (jx, jy)))
    out.resize((out.width * 3, out.height * 3), Image.NEAREST).save(dst)
    print('wrote', esc(dst), 'score=', score)


if __name__ == '__main__':
    main()
