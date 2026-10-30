"""Align the body/head sprites to the reference render using measured landmarks.

  python refalign.py [--ref 0] [--body npc1000101] [--head head0101]

Steps:
  1. background removal on the reference (border flood fill) -> foreground mask
  2. largest connected component -> body bbox (should be 43x82 for sprite 43x82)
  3. skin-coloured pixels inside the body bbox -> where the body's own skin (necks/hands) is
  4. like 3. but for the head sprite -> face bbox inside the sprite
  5. head offset = ref_face - sprite_face; print canvas coords and render the composite
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
        q.append((y + 1, x))
        q.append((y - 1, x))
        q.append((y, x + 1))
        q.append((y, x - 1))
    return ~seen


def largest(mask):
    h, w = mask.shape
    seen = np.zeros((h, w), bool)
    best = None
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            q = deque([(y, x)])
            seen[y, x] = True
            pts = []
            while q:
                cy, cx = q.popleft()
                pts.append((cy, cx))
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if best is None or len(pts) > len(best):
                best = pts
    arr = np.array(best)
    return arr[:, 0].min(), arr[:, 1].min(), arr[:, 0].max(), arr[:, 1].max(), len(best)


def skin_bbox(rgb, alpha, region=None):
    r = rgb[:, :, 0].astype(int)
    g = rgb[:, :, 1].astype(int)
    b = rgb[:, :, 2].astype(int)
    m = (r > 180) & (r - b > 45) & (g > 130) & (g < 225) & (r - g > 25) & alpha
    if region:
        y0, x0, y1, x1 = region
        mm = np.zeros_like(m)
        mm[y0:y1 + 1, x0:x1 + 1] = m[y0:y1 + 1, x0:x1 + 1]
        m = mm
    if not m.any():
        return None
    ys, xs = np.where(m)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), int(m.sum())


def body_sprite(path, frame=0):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    pre, w, h, px, bpp = r['frames'][frame]
    im = dimg.to_image(d, px, w, h, bpp)
    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    b0 = [dimg.u32(d, pre + 4 * i) for i in range(4)]
    r['canvas_w'], r['canvas_h'] = pw[3], pw[4]
    r['pivot_x'], r['pivot_y'] = pw[5], pw[6]
    r['at'] = (b0[1], b0[2])
    return im, r


def head_sprite(path, idx=0):
    d = open(path, 'rb').read()
    recs, extra, k = headtool.segment(d)
    p, w, h, s, f = recs[idx]
    im = dimg.to_image(d, p + 16, w, h, s // w)
    return im, recs


def main():
    args = sys.argv[1:]
    idx = int(args[args.index('--ref') + 1]) if '--ref' in args else 0
    body = args[args.index('--body') + 1] if '--body' in args else 'npc1000101'
    head = args[args.index('--head') + 1] if '--head' in args else 'head0101'
    name = ALL[idx]
    ref = Image.open(os.path.join(REF, name)).convert('RGB')
    mask = fg_mask(ref)
    y0, x0, y1, x1, npx = largest(mask)
    print('ref %-8s %dx%d  fg=%d  largest=%d px bbox=(%d,%d)-(%d,%d) %dx%d'
          % (esc(name), ref.width, ref.height, int(mask.sum()), npx, x0, y0, x1, y1, x1 - x0 + 1, y1 - y0 + 1))

    bimg, br = body_sprite(os.path.join(SRC, 'npc', body + '.gsn'))
    print('body %-12s sprite %dx%d  canvas %sx%s pivot %s,%s at %s' % (
        body, bimg.width, bimg.height, br['canvas_w'], br['canvas_h'], br['pivot_x'], br['pivot_y'], br['at']))
    bmask = np.asarray(bimg)[:, :, 3] > 40
    print('body alpha=%d  ref-largest=%d  size-match=%s'
          % (int(bmask.sum()), npx, (bimg.width, bimg.height) == (x1 - x0 + 1, y1 - y0 + 1)))

    refrgb = np.asarray(ref).astype(int)
    refa = mask
    rb = skin_bbox(refrgb, refa, (y0, x0, y1, x1))
    print('ref body-region skin bbox:', rb)

    himg, recs = head_sprite(os.path.join(SRC, 'head', head + '.gsn'), 0)
    harr = np.asarray(himg)
    hb = skin_bbox(harr[:, :, :3].astype(int), harr[:, :, 3] > 40)
    print('head %-12s sprite %dx%d  skin bbox: %s' % (head, himg.width, himg.height, hb))

    if rb and hb:
        dx = (rb[0] + rb[2]) // 2 - (hb[0] + hb[2]) // 2
        dy = rb[1] - hb[1]
        print('=> head sprite offset in ref coords: (%+d,%+d)   body at (%d,%d) -> rel to body (%+d,%+d)'
              % (dx, dy, x0, y0, dx - x0, dy - y0))
        canvas = (x0 + dx - 0, y0 + dy - 0)
        print('   head sprite top-left in ref = (%d,%d)' % (dx, dy))

    # render: body at (x0,y0), head at measured offset
    out = Image.new('RGBA', (ref.width, ref.height), (0, 0, 0, 0))
    out.alpha_composite(bimg.convert('RGBA'), (x0, y0))
    if rb and hb:
        out.alpha_composite(himg.convert('RGBA'), (dx, dy))
    comp = Image.new('RGB', (ref.width * 3 + 20, ref.height), (40, 40, 46))
    comp.paste(ref, (0, 0))
    comp.paste(out.convert('RGB'), (ref.width + 10, 0))
    ov = ref.copy()
    ov.paste(out.convert('RGB'), (0, 0), out)
    comp.paste(ov, (ref.width * 2 + 20, 0))
    dst = os.path.join(HERE, 'out', 'align_%s.png' % esc(name).replace('.png', '').replace('\\u', 'u'))
    comp.resize((comp.width * 3, comp.height * 3), Image.NEAREST).save(dst)
    print('wrote', esc(dst), '(ref | composite | overlay)')


if __name__ == '__main__':
    main()
