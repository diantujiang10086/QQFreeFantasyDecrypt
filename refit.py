"""Fit body+head sprites onto the reference render by mask correlation (FFT).

  python refit.py [--ref 0] [--body npc1000101] [--head head0101] [--top 5]

For every placement of a sprite inside the reference we get, via FFT cross-correlation,
how many sprite pixels land on foreground.  Body and head are fitted independently:
the body first (it defines the whole silhouette), then the head on the pixels the body
cannot explain plus the head-shaped blob above it.
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

REF = os.path.join(HERE, 'out', 'ref')
SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def fg_mask(im, tol=60, grid=True):
    """grid=True: pixels on the 4-bit x17 colour grid (i.e. sprite pixels, the background
    texture is not on it).  grid=False: border flood fill of the beige background."""
    a = np.asarray(im.convert('RGB')).astype(np.int16)
    if grid:
        return (a % 17 == 0).all(axis=2)
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


def correlate(mask, tpl):
    """cross-correlation: out[y,x] = sum(tpl * mask[y:y+th, x:x+tw])"""
    H, W = mask.shape
    th, tw = tpl.shape
    fh, fw = H + th - 1, W + tw - 1
    F = np.fft.rfft2(mask, (fh, fw)) * np.conj(np.fft.rfft2(tpl[::-1, ::-1], (fh, fw)))
    cc = np.fft.irfft2(F, (fh, fw))
    return np.rint(cc[th - 1:th - 1 + H - th + 1, tw - 1:tw - 1 + W - tw + 1]).astype(int)


def split_scores(mask, tpl):
    inter = correlate(mask, tpl)
    tot_t = int(tpl.sum())
    tot_m = int(mask.sum())
    union = tot_t + tot_m - inter
    iou = inter / np.maximum(union, 1)
    cover = inter / max(tot_t, 1)
    return inter, iou, cover


def body_sprite(path, frame=0):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    pre, w, h, px, bpp = r['frames'][frame]
    im = dimg.to_image(d, px, w, h, bpp)
    return im


def head_sprite(path, idx=0):
    d = open(path, 'rb').read()
    recs, extra, k = headtool.segment(d)
    p, w, h, s, f = recs[idx]
    return dimg.to_image(d, p + 16, w, h, s // w)


def top_positions(score, n=5):
    flat = score.ravel()
    idx = np.argpartition(flat, -n)[-n:]
    idx = idx[np.argsort(-flat[idx])]
    return [(int(i % score.shape[1]), int(i // score.shape[1]), float(flat[i])) for i in idx]


def main():
    args = sys.argv[1:]
    idx = int(args[args.index('--ref') + 1]) if '--ref' in args else 0
    body = args[args.index('--body') + 1] if '--body' in args else 'npc1000101'
    head = args[args.index('--head') + 1] if '--head' in args else 'head0101'
    n = int(args[args.index('--top') + 1]) if '--top' in args else 5
    name = ALL[idx]
    ref = Image.open(os.path.join(REF, name)).convert('RGB')
    mask = fg_mask(ref)
    M = mask.astype(float)
    print('ref %-10s %dx%d fg=%d' % (esc(name), ref.width, ref.height, int(mask.sum())))

    bimg = body_sprite(os.path.join(SRC, 'npc', body + '.gsn'))
    B = (np.asarray(bimg)[:, :, 3] > 40).astype(float)
    inter, iou, cover = split_scores(M, B)
    print('body %-12s %dx%d px=%d' % (body, bimg.width, bimg.height, int(B.sum())))
    for x, y, s in top_positions(iou, n):
        print('   iou=%.3f cover=%.3f at (%2d,%2d)' % (iou[y, x], cover[y, x], x, y))
    bx, by, _ = top_positions(iou, 1)[0]

    himg = head_sprite(os.path.join(SRC, 'head', head + '.gsn'))
    Hpt = (np.asarray(himg)[:, :, 3] > 40).astype(float)
    # head-only mask: foreground not explained by the body at its best position
    rest = M.copy()
    Hh, Ww = M.shape
    if 0 <= by <= Hh - B.shape[0] and 0 <= bx <= Ww - B.shape[1]:
        rest[by:by + B.shape[0], bx:bx + B.shape[1]] -= B
    rest = np.clip(rest, 0, 1)
    inter2, iou2, cover2 = split_scores(rest, Hpt)
    print('head %-12s %dx%d px=%d' % (head, himg.width, himg.height, int(Hpt.sum())))
    for x, y, s in top_positions(iou2, n):
        print('   iou=%.3f cover=%.3f at (%2d,%2d)  rel-to-body (%+d,%+d)'
              % (iou2[y, x], cover2[y, x], x, y, x - bx, y - by))
    hx, hy, _ = top_positions(iou2, 1)[0]
    print('=> body sprite at (%d,%d), head sprite at (%d,%d)  rel (%+d,%+d)'
          % (bx, by, hx, hy, hx - bx, hy - by))

    for tag, (px, py) in (('fit', (hx, hy)), ('user 9,4', (bx + 9, by + 4)), ('user 8,4', (bx + 8, by + 4))):
        out = Image.new('RGBA', ref.size, (0, 0, 0, 0))
        out.alpha_composite(bimg.convert('RGBA'), (bx, by))
        out.alpha_composite(himg.convert('RGBA'), (px, py))
        both = Image.new('RGB', (ref.width * 2 + 12, ref.height), (46, 46, 52))
        both.paste(ref, (0, 0))
        ov = ref.copy()
        ov.paste(out.convert('RGB'), (0, 0), out)
        both.paste(ov, (ref.width + 12, 0))
        safe = tag.replace(' ', '').replace(',', '-')
        dst = os.path.join(HERE, 'out', 'fit_%s_%s.png' % (safe, esc(name).replace('.png', '').replace('\\u', 'u')))
        both.resize((both.width * 4, both.height * 4), Image.NEAREST).save(dst)
        print('wrote', esc(dst))


if __name__ == '__main__':
    main()
