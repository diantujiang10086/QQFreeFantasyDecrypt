"""Locate body and head sprites inside a reference render using silhouette agreement.

  python refshape.py [--ref 0] [--scales 0.9,1.0,1.1] [--top 6]

Stage 1 finds the body placement (sprite fully inside the character mask, nothing outside).
Stage 2, with the body fixed, finds the head placement the same way. The resulting
head-minus-body offset is the composite anchor the real render uses.
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import combo     # noqa: E402

REF = os.path.join(HERE, 'out', 'ref')
SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def char_mask(rgb):
    a = rgb.astype(np.int16)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    lum = (R + G + B) / 3.0
    beige = (np.abs(R - G) < 30) & ((R - B) >= 0) & ((R - B) < 70) & (lum > 120)
    return ~beige


def largest(mask):
    h, w = mask.shape
    best = []
    seen = np.zeros_like(mask, dtype=bool)
    for y in range(h):
        for x in range(w):
            if mask[y, x] and not seen[y, x]:
                q = deque([(x, y)])
                seen[y, x] = True
                pts = []
                while q:
                    cx, cy = q.popleft()
                    pts.append((cx, cy))
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < w and 0 <= ny < h and mask[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True
                                q.append((nx, ny))
                if len(pts) > len(best):
                    best = pts
    out = np.zeros_like(mask)
    for x, y in best:
        out[y, x] = True
    return out


def load(path, frame=0, scale=1.0, head=False):
    if head:
        d, recs, r = combo.recursive_records(path)
        w, h, bpp, px = recs[frame]
    else:
        d = open(path, 'rb').read()
        r = dimg.parse(d)
        pre, w, h, px, bpp = r['frames'][frame]
    im = dimg.to_image(d, px, w, h, bpp)
    if scale != 1.0:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    a = np.asarray(im)[:, :, 3] > 40
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def scan(mask, tpl, inside_w=1.0, outside_w=2.0):
    H, W = mask.shape
    th, tw = tpl.shape
    n = int(tpl.sum())
    best = []
    for y in range(-th + 1, H):
        for x in range(-tw + 1, W):
            y0, y1 = max(0, y), min(H, y + th)
            x0, x1 = max(0, x), min(W, x + tw)
            if y1 <= y0 or x1 <= x0:
                continue
            sub_t = tpl[y0 - y:y1 - y, x0 - x:x1 - x]
            sub_m = mask[y0:y1, x0:x1]
            inside = int((sub_t & sub_m).sum())
            outside = int((sub_t & ~sub_m).sum())
            score = inside_w * inside - outside_w * outside
            best.append((score, x, y, inside, outside, n))
    best.sort(reverse=True)
    return best


def main():
    args = sys.argv[1:]
    idx = int(args[args.index('--ref') + 1]) if '--ref' in args else 0
    top = int(args[args.index('--top') + 1]) if '--top' in args else 6
    scales = [float(v) for v in (args[args.index('--scales') + 1] if '--scales' in args else '1.0').split(',')]
    name = ALL[idx]
    rgb = np.asarray(Image.open(os.path.join(REF, name)).convert('RGB'))
    m = largest(char_mask(rgb))
    ys, xs = np.nonzero(m)
    print('ref %s %dx%d mask=%d bbox=(%d,%d)-(%d,%d)' % (esc(name), rgb.shape[1], rgb.shape[0], m.sum(), xs.min(), ys.min(), xs.max(), ys.max()))
    body_p = os.path.join(SRC, 'npc', 'npc1000101.gsn')
    head_p = os.path.join(SRC, 'head', 'head0101.gsn')
    for sc in scales:
        b = load(body_p, 0, sc)
        hits = scan(m, b)[:top]
        print('== scale %.2f body %dx%d' % (sc, b.shape[1], b.shape[0]))
        for s, x, y, ins, outs, n in hits:
            print('   body at (%3d,%3d) inside=%4d/%d outside=%4d score=%6.1f' % (x, y, ins, n, outs, s))
        if not hits:
            continue
        _, bx, by, _, _, _ = hits[0]
        h = load(head_p, 0, sc, head=True)
        hits2 = scan(m, h, inside_w=1.0, outside_w=3.0)[:top]
        print('   head %dx%d candidates (offset from body top-left):' % (h.shape[1], h.shape[0]))
        for s, x, y, ins, outs, n in hits2:
            print('      head at (%3d,%3d) dx=%+3d dy=%+3d inside=%3d/%d outside=%3d score=%6.1f'
                  % (x, y, x - bx, y - by, ins, n, outs, s))


if __name__ == '__main__':
    main()
