"""Sanity sweep over out/mix: does the head actually sit on the body?

For every composite we recompute the placement from the two source files and
report three numbers:

  gap  = body's first opaque row - head's last opaque row
         (negative: the head is pushed into the body, which is what we want)
  cxo  = head centroid x - x of the body's first opaque row centre
  cov  = fraction of head pixels that land on an opaque body pixel

Bodies whose top is a weapon or a wing (not a neck) show up as positive gap or
a large |cxo|.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mix   # noqa: E402


def first_row(a):
    ys = np.nonzero(a.any(axis=1))[0]
    return int(ys[0]) if len(ys) else None


def main():
    d = os.path.join(mix.OUT, 'mix')
    files = sorted(f for f in os.listdir(d) if f.endswith('.png'))
    rows = []
    for f in files:
        stem = f[:-4]
        parts = stem.split('_')
        if len(parts) < 3:
            continue
        body, head = parts[0], parts[1]
        b = mix.body_frame(os.path.join(mix.SRC, 'npc', body + '.gsn'), 0)
        h = mix.head_pic(os.path.join(mix.SRC, 'head', head + '.gsn'), 1)
        if not b or not h:
            continue
        im, (hx, hy) = mix.compose(b['img'], h)
        ba = np.asarray(b['img'])[:, :, 3] > 128
        ha = np.asarray(h['img'])[:, :, 3] > 128
        btop = first_row(ba)
        # head pixels in body coordinates
        by0, by1 = max(0, hy), hy + ha.shape[0]
        hbot = hy + (np.nonzero(ha.any(axis=1))[0].max() + 1 if ha.any() else 0)
        gap = (btop + 0) - hbot
        bx = np.nonzero(ba[btop])[0]
        bcx = (bx.min() + bx.max() + 1) / 2.0
        hxs = np.nonzero(ha)[1]
        hcx = hx + (hxs.min() + hxs.max() + 1) / 2.0 if len(hxs) else hx
        cxo = hcx - bcx
        # coverage: head pixels over opaque body
        cov_n = 0
        tot = 0
        for yy in range(ha.shape[0]):
            by = hy + yy
            if by < 0 or by >= ba.shape[0]:
                continue
            for xx in range(ha.shape[1]):
                if not ha[yy, xx]:
                    continue
                tot += 1
                bx_ = hx + xx
                if 0 <= bx_ < ba.shape[1] and ba[by, bx_]:
                    cov_n += 1
        rows.append((f, gap, cxo, cov_n / tot if tot else 1.0, b['img'].width, b['img'].height))
    print('%-42s %5s %7s %6s' % ('tile', 'gap', 'cxo', 'cov'))
    bad = 0
    for r in rows:
        flag = ''
        if r[1] > -2 or abs(r[2]) > 10 or r[3] < 0.2:
            flag = '  <-- check'
            bad += 1
        print('%-42s %5d %+7.1f %6.2f%s' % (r[0], r[1], r[2], r[3], flag))
    print('\n%d tiles, %d flagged' % (len(rows), bad))


if __name__ == '__main__':
    main()
