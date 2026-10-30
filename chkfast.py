"""Check the fast dimg.to_image against the original per-pixel decoder."""
import time

from PIL import Image, ImageChops

import dimg
import viewer2


def slow(d, o, w, h, bpp=2, alpha_high=True):
    img = Image.new('RGBA', (w, h))
    if bpp == 4:
        img.putdata([dimg.pixel4(d, o + 4 * i) for i in range(w * h)])
    else:
        img.putdata([dimg.pixel(d, o + 2 * i, alpha_high) for i in range(w * h)])
    return img


def frame0(rel):
    d = viewer2.src_bytes(rel)
    r = dimg.parse(d, brute=True)
    if not r.get('ok'):
        return None
    f = [x for x in r['frames'] if x[3] is not None][0]
    return d, f


CASES = ['avatar/npc/npc1000101.gsn', 'avatar/npc/npc539801e.gsn',
         'avatar/cap/cap0001.gsn', 'avatar/cap/cap1001.gsn']
bad = 0
for rel in CASES:
    got = frame0(rel)
    if not got:
        print(rel, 'skipped')
        continue
    d, f = got
    _pre, w, h, px, bpp = f[:5]
    # warm up (import / codec setup) then time 5 runs each
    dimg.to_image(d, px, w, h, bpp)
    t0 = time.time()
    for _ in range(5):
        fast = dimg.to_image(d, px, w, h, bpp)
    t1 = time.time()
    for _ in range(5):
        ref = slow(d, px, w, h, bpp)
    t2 = time.time()
    same = ImageChops.difference(fast, ref).getbbox() is None
    print('%-30s %3dx%-3d bpp=%d  fast %6.2f ms  slow %7.2f ms  same=%s'
          % (rel, w, h, bpp, (t1 - t0) * 200, (t2 - t1) * 200, same))
    bad += 0 if same else 1
print('mismatches:', bad)
