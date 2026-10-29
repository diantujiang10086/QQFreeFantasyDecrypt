"""What is the grayscale second image in the 16 mask-bearing head files?

For every (colour, mask) pair it reports the overlap statistics and the mean
colour of the colour layer inside vs outside the mask.  If the mask tracked the
alpha channel the two opaque sets would coincide (IoU = 1); if it selects one
material (hair / face / clothes) it will be a strict subset with a distinctly
different mean colour.

    python headmask.py [--dir SRC] [--limit N]
"""
import os
import sys

import headtool
import dimg

HERE = os.path.dirname(os.path.abspath(__file__))


def alpha_of(d, c):
    p, w, h, stride, _ = c
    bpp = stride // w
    px = p + 16
    n = w * h
    if bpp == 2:
        raw = d[px:px + 2 * n]
        b1 = raw[1::2]
        return bytes(x >> 4 for x in b1), bpp, px
    raw = d[px:px + 4 * n]
    return bytes(x >> 4 for x in raw[3::4]), bpp, px


def rgb_at(d, c, bpp, px):
    p, w, h, stride, _ = c
    n = w * h
    if bpp == 2:
        raw = d[px:px + 2 * n]
        b0, b1 = raw[0::2], raw[1::2]
        r = bytes(x & 15 for x in b1)
        g = bytes(x >> 4 for x in b0)
        b = bytes(x & 15 for x in b0)
    else:
        raw = d[px:px + 4 * n]
        r = bytes(x >> 4 for x in raw[0::4])
        g = bytes(x >> 4 for x in raw[1::4])
        b = bytes(x >> 4 for x in raw[2::4])
    return r, g, b


def main():
    a = sys.argv[1:]
    src = a[a.index('--dir') + 1] if '--dir' in a else headtool.SRC
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 10 ** 9
    n_files = 0
    for fn in sorted(os.listdir(src)):
        if not fn.lower().endswith('.gsn'):
            continue
        d = open(os.path.join(src, fn), 'rb').read()
        recs, extra, k = headtool.segment(d)
        h = dimg.head(d)
        if k != 2 * h['n_frames'] or not recs:
            continue
        n_files += 1
        if n_files > limit:
            break
        print('%s  (%d pairs, extra=%d)' % (fn, k // 2, extra))
        for pair in range(k // 2):
            c_rec, m_rec = recs[2 * pair], recs[2 * pair + 1]
            ca, cbpp, cpx = alpha_of(d, c_rec)
            ma, mbpp, mpx = alpha_of(d, m_rec)
            n = len(ca)
            if len(ma) != n:
                print('   d%d: size differs  colour %dx%d (%d px)  mask %dx%d (%d px)'
                      % (pair + 1, c_rec[1], c_rec[2], n, m_rec[1], m_rec[2], len(ma)))
                continue
            cin = [i for i in range(n) if ca[i] and ma[i]]
            conly = [i for i in range(n) if ca[i] and not ma[i]]
            monly = [i for i in range(n) if ma[i] and not ca[i]]
            inter, union = len(cin), len([i for i in range(n) if ca[i] or ma[i]])
            r, g, b = rgb_at(d, c_rec, cbpp, cpx)
            def mean(idx):
                if not idx:
                    return (0, 0, 0)
                return (round(sum(r[i] for i in idx) / len(idx), 1),
                        round(sum(g[i] for i in idx) / len(idx), 1),
                        round(sum(b[i] for i in idx) / len(idx), 1))
            print('   d%d %dx%d  colour_opaque=%d mask_opaque=%d IoU=%.3f '
                  'mask_outside_colour=%d  in-mask RGB=%s  out-mask RGB=%s'
                  % (pair + 1, c_rec[1], c_rec[2], len([i for i in ca if i]),
                     len([i for i in ma if i]), inter / union if union else 0,
                     len(monly), mean(cin), mean(conly)))


if __name__ == '__main__':
    main()
