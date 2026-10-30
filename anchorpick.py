"""Pick the best horizontal anchor for the head, using the 5 exact truths.

Truth (relative to the body sprite crop, head2151 pivot = 20,28):
    f0 -> dx +11   f1 -> +4   f2 -> +16   f3 -> +9   f4 -> +3
i.e. the head pivot has to sit at these sprite-local x values:
    f0 -> 31   f1 -> 24   f2 -> 36   f3 -> 29   f4 -> 23

We test a bunch of cheap silhouette anchors and report the error of each.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mix   # noqa: E402

WANT = {0: 31.0, 1: 24.0, 2: 36.0, 3: 29.0, 4: 23.0}


def anchors(a):
    """a = bool alpha array."""
    ys = np.nonzero(a.any(axis=1))[0]
    y0 = int(ys[0])
    out = {}
    r = np.nonzero(a[y0])[0]
    out['top_row_run'] = (r.min() + r.max() + 1) / 2.0
    out['top3_centroid'] = float(np.nonzero(a[y0:y0 + 3])[1].mean())
    out['top5_centroid'] = float(np.nonzero(a[y0:y0 + 5])[1].mean())
    out['top10_centroid'] = float(np.nonzero(a[y0:y0 + 10])[1].mean())
    out['bbox_center'] = (np.nonzero(a)[1].min() + np.nonzero(a)[1].max() + 1) / 2.0
    # narrowest row in the top 12 rows (the neck stub)
    best = None
    for y in range(y0, min(y0 + 12, a.shape[0])):
        rr = np.nonzero(a[y])[0]
        if not len(rr):
            continue
        w = rr.max() - rr.min() + 1
        if best is None or w < best[0]:
            best = (w, (rr.min() + rr.max() + 1) / 2.0)
    out['narrowest_top_row'] = best[1] if best else out['top_row_run']
    # centre of widest row within the top 40% of the sprite (shoulders)
    h = int(a.shape[0])
    best = None
    for y in range(y0, y0 + int(h * 0.4) + 1):
        rr = np.nonzero(a[y])[0]
        if not len(rr):
            continue
        w = rr.max() - rr.min() + 1
        if best is None or w > best[0]:
            best = (w, (rr.min() + rr.max() + 1) / 2.0)
    out['widest_top40'] = best[1] if best else out['top_row_run']
    # feet line (bottom opaque row) - for a standing character the whole body
    # is supposed to be balanced over the feet
    yb = int(ys[-1])
    rb = np.nonzero(a[yb])[0]
    out['bottom_row_run'] = (rb.min() + rb.max() + 1) / 2.0
    out['bottom5_centroid'] = float(np.nonzero(a[max(0, yb - 4):yb + 1])[1].mean())
    out['feet_to_head_axis'] = out['bottom_row_run']
    # column with the most opaque pixels below mid-height (the supporting leg)
    lower = a[yb - int(h * 0.3) if False else y0:, :]
    # keep it cheap: vertical axis through the widest row of the bottom 25%
    ylo = max(y0, int(a.shape[0] * 0.75))
    bestb = None
    for y in range(ylo, a.shape[0]):
        rr = np.nonzero(a[y])[0]
        if not len(rr):
            continue
        w = rr.max() - rr.min() + 1
        if bestb is None or w > bestb[0]:
            bestb = (w, (rr.min() + rr.max() + 1) / 2.0)
    out['widest_bottom25'] = bestb[1] if bestb else out['bottom_row_run']
    return out


def main():
    bp = os.path.join(mix.SRC, 'npc', 'npc1000101.gsn')
    frames = {}
    for fr in range(5):
        b = mix.body_frame(bp, fr)
        frames[fr] = anchors(np.asarray(b['img'])[:, :, 3] > 128)
    names = list(frames[0].keys())
    print('%-18s %s   mean|err|  max|err|' % ('anchor', ''.join('%8s' % ('f%d' % f) for f in range(5))))
    for nm in names:
        errs = [frames[f][nm] - WANT[f] for f in range(5)]
        print('%-18s %s   %8.2f  %8.2f'
              % (nm, ''.join('%+8.1f' % e for e in errs),
                 float(np.mean(np.abs(errs))), float(np.max(np.abs(errs)))))


if __name__ == '__main__':
    main()
