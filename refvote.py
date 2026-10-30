"""Exact-palette voting: find where a sprite was drawn in a reference render.

  python refvote.py --dir head --top 8 [--scales 1.0,1.25,1.5]

Sprites are drawn with exact palette colours (no resampling), so the fraction of a
sprite's opaque pixels that match the reference pixel byte-for-byte peaks sharply at the
true placement. This survives tinting of a few layers better than mean-difference.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402

REF = os.path.join(HERE, 'out', 'ref')
SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def first_record(path):
    d = open(path, 'rb').read()
    try:
        r = dimg.parse(d)
        if r.get('ok'):
            for pre, w, h, px, bpp in r['frames']:
                if px:
                    return d, w, h, bpp, px
    except Exception:
        pass
    import headtool
    recs, extra, k = headtool.segment(d)
    p, w, h, s, f = recs[0]
    return d, w, h, s // w, p + 16


def sprite(path, scale=1.0):
    d, w, h, bpp, px = first_record(path)
    im = dimg.to_image(d, px, w, h, bpp)
    if scale != 1.0:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.NEAREST)
    a = np.asarray(im)
    return a[:, :, :3].astype(np.int32), a[:, :, 3] > 40


def vote(ref, trgb, tmask):
    H, W = ref.shape[:2]
    th, tw = trgb.shape[:2]
    if th > H or tw > W:
        return 0.0, -1, -1
    n = int(tmask.sum())
    flat = trgb[tmask]
    best = (0.0, -1, -1)
    for y in range(H - th + 1):
        for x in range(W - tw + 1):
            hit = int(np.all(ref[y:y + th, x:x + tw][tmask] == flat, axis=1).sum())
            f = hit / float(n)
            if f > best[0]:
                best = (f, x, y)
    return best


def main():
    args = sys.argv[1:]
    idx = int(args[args.index('--ref') + 1]) if '--ref' in args else 0
    top = int(args[args.index('--top') + 1]) if '--top' in args else 8
    scales = [float(v) for v in (args[args.index('--scales') + 1] if '--scales' in args else '1.0').split(',')]
    sub = args[args.index('--dir') + 1] if '--dir' in args else 'head'
    only = args[args.index('--only') + 1].split(',') if '--only' in args else None
    name = ALL[idx]
    ref = np.asarray(Image.open(os.path.join(REF, name)).convert('RGB')).astype(np.int32)
    dirp = os.path.join(SRC, sub)
    files = sorted(n for n in os.listdir(dirp) if n.lower().endswith('.gsn'))
    if only:
        files = [n for n in files if any(o in n for o in only)]
    print('ref %s  %s files=%d' % (esc(name), sub, len(files)))
    scored = []
    for n in files:
        try:
            trgb, tmask = sprite(os.path.join(dirp, n), scales[0] if len(scales) == 1 else 1.0)
        except Exception as e:
            print('  skip', esc(n), e)
            continue
        f, x, y = vote(ref, trgb, tmask)
        scored.append((f, n, x, y, trgb.shape[1], trgb.shape[0]))
    scored.sort(reverse=True)
    for f, n, x, y, w, h in scored[:top]:
        print('   %-14s exact=%.3f at (%2d,%2d) tpl %dx%d' % (esc(n), f, x, y, w, h))


if __name__ == '__main__':
    main()
