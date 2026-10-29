# -*- coding: utf-8 -*-
"""Self-test: parse the verified sample set and check every expectation.

usage: python selftest.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg

SRC = dimg.SRC

# file: (oh, first_px, frames, skipped, dir_counts, bpp)  -- measured by hand
EXPECT = {
    'npc540201.gsn': (40, 100, 115, 8, [23] * 5, 2),
    'npc559201.gsn': (80, 100, 60, 0, [12] * 5, 2),
    'npc59503.gsn': (40, 100, 1, 0, [1], 2),
    'npc64404.gsn': (28, 80, 5, 0, [1] * 5, 2),
    'npc1955501.gsn': (40, 100, 40, 0, [8] * 5, 2),
    'npc174501.gsn': (96, 140, 5, 0, [1] * 5, 2),
    'npc305001.gsn': (48, 100, 20, 0, [10, 10], 2),
    'npc20301.gsn': (40, 100, 20, 0, [10, 10], 2),
    'npc499203.gsn': (40, 100, 60, 0, [15] * 4, 2),
    'npc108905.gsn': (96, 92, 9, 0, [9], 2),
    'npc15311.gsn': (96, 92, 12, 0, [4] * 3, 2),
    'npc98203.gsn': (40, 100, 16, 0, [8, 8], 2),
    'npc528901.gsn': (40, 100, 18, 0, [9, 9], 2),
    'npc61401.gsn': (28, 92, 50, 0, [10] * 5, 2),
    'npc31809.gsn': (28, 92, 32, 0, [8] * 4, 2),
    'npc280702.gsn': (40, 100, 6, 0, [6], 2),
    'npc64401.gsn': (28, 92, 12, 0, [6, 6], 2),
    'npc64402.gsn': (28, 80, 2, 0, [1, 1], 2),
    'npc64403.gsn': (28, 92, 6, 0, [3, 3], 2),
    'npc64405.gsn': (28, 80, 8, 0, [4, 4], 2),
    'npc64501.gsn': (28, 92, 5, 0, [1] * 5, 2),
    'npc57101.gsn': (40, 100, 7, 0, [7], 2),
    'npc57301.gsn': (40, 100, 5, 0, [5], 2),
    'npc20101.gsn': (28, 92, 14, 0, [7, 7], 2),
    'npc20406.gsn': (28, 80, 5, 0, [1] * 5, 2),
    'npc29408.gsn': (28, 92, 4, 0, [4], 2),
    'npc511901t.gsn': (40, 100, 125, 100, [25] * 5, 2),
    'npc559201t.gsn': (40, 100, 60, 60, [12] * 5, 2),
    'npc511901.gsn': (56, 100, 125, 0, [25] * 5, 2),
    # --- 4 bytes/pixel family (signature flag=2) -------------------------
    'npc539701.gsn': (80, 100, 40, 0, [8] * 5, 4),
    'npc539701e.gsn': (40, 100, 40, 0, [8] * 5, 4),
    'npc539801t.gsn': (40, 100, 40, 24, [8] * 5, 4),
    'npc540001t.gsn': (40, 100, 40, 16, [8] * 5, 4),
    # --- dir-table exceptions -------------------------------------------
    'npc191405.gsn': (96, 92, 39, 4, [7] * 5, 2),      # trailing padding
    'npc304403.gsn': (40, 100, 51, 1, [10] * 5, 2),    # trailing padding
    'npc488903.gsn': (40, 100, 48, 3, [9] * 5, 2),     # trailing padding
    'npc61903.gsn': (28, 92, 17, 1, [8, 8], 2),        # trailing padding
    'npc42102.gsn': (40, 100, 10, 4, [], 2),           # dir table all zeros
}


def trailing_empty(frames):
    """Count the run of pixel-less records at the END of the frame list."""
    n = 0
    for f in reversed(frames):
        if f[3] is None:
            n += 1
        else:
            break
    return n


def main():
    bad = 0
    for name, (oh, fp, nf, skip, dirs, bpp) in EXPECT.items():
        p = os.path.join(SRC, name)
        d = open(p, 'rb').read()
        r = dimg.parse(d)
        errs = []
        if not r['ok']:
            errs.append('parse failed: ' + ' ; '.join(r['tried']))
        else:
            if r['oh'] != oh:
                errs.append(f'oh {r["oh"]} != {oh}')
            if r['first_px'] != fp:
                errs.append(f'first_px {r["first_px"]} != {fp}')
            if len(r['frames']) != nf or r['header']['n_frames'] != nf:
                errs.append(f'frames {len(r["frames"])}/{r["header"]["n_frames"]} != {nf}')
            if r['skipped'] != skip:
                errs.append(f'skipped {r["skipped"]} != {skip}')
            if r['dir_counts'] != dirs:
                errs.append(f'dirs {r["dir_counts"]} != {dirs}')
            if r['tail'] != 12 * r['header']['n_dirs'] + r['oh'] - 28:
                errs.append('tail formula broken')
            # The dir table sums either to every frame (pixel-less frames are
            # counted) or to every frame minus a trailing run of pixel-less
            # records (those are padding).  An all-zero table maps nothing.
            if dirs:
                trail = trailing_empty(r['frames'])
                if sum(dirs) not in (nf, nf - trail):
                    errs.append(f'dir sum {sum(dirs)} not in ({nf}, {nf - trail})')
            if r['end'] + r['tail'] != len(d):
                errs.append('end+tail != size')
            # pixel accounting:  size = fp - oh + nFrames*oh + sum(bpp*wh) + tail
            px = sum(b * w * h for _, w, h, q, b in r['frames']
                     if q is not None)
            if r['first_px'] - r['oh'] + nf * r['oh'] + px + r['tail'] != len(d):
                errs.append('record accounting broken')
            want = [] if skip == nf else [bpp]
            if r['bpps'] != want:
                errs.append(f'bpp {r["bpps"]} != {want}')
            if skip < nf and r['bpp'] != bpp:
                errs.append(f'bpp field {r["bpp"]} != {bpp}')
        if errs:
            bad += 1
            print(f'FAIL {name:20s} ' + ' | '.join(errs))
        else:
            print(f'ok   {name:20s} oh={oh:3d} fp={fp:4d} frames={nf:4d} '
                  f'skip={skip:3d} bpp={bpp}')
    print(f'\n{len(EXPECT) - bad} ok, {bad} failed')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
