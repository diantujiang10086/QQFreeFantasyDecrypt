# -*- coding: utf-8 -*-
"""Explain why a .gsn file fails to walk.

usage: python whyfail.py file [file ...]
"""
import os
import sys

import dimg


def report(name):
    p = os.path.join(dimg.SRC, name)
    d = open(p, 'rb').read()
    h = dimg.head(d)
    print('=' * 92)
    print(f'{name} size={len(d)} major={h["major"]} minor={h["minor"]} '
          f'dirs={h["n_dirs"]} frames={h["n_frames"]}')
    for fp, oh, tag in dimg.hints(h):
        frames, ok, why = dimg.walk(d, fp, oh, h['n_frames'])
        print(f'  {tag}: first_px={fp} oh={oh} -> {len(frames)} frames, {why}')
        if not frames:
            continue
        start = max(0, len(frames) - 4)
        for i in range(start, len(frames)):
            pre, w, hh, px = frames[i]
            end = px + 2 * w * hh
            print(f'    f{i}: prefix@{pre} sig@({w},{hh}) px@{px} end={end} '
                  f'gap_next={2*w*hh}')
        last = frames[-1]
        q0 = last[3] + 2 * last[1] * last[2]
        found = 0
        q = q0 - 8
        while q < min(len(d) - 16, q0 + 400000):
            s = dimg.sig_at(d, q)
            if s:
                print(f'    next sig {q:>9} (delta from px end {q-q0:+}) '
                      f'{s}')
                found += 1
                if found >= 3:
                    break
            q += 2
    dt_ok, counts = dimg.dir_table(d, h['n_dirs'], h['n_frames'])
    tail = d[-12 * h['n_dirs']:]
    print(f'  dir table ok={dt_ok} counts={counts}')


def main():
    for name in sys.argv[1:]:
        report(name)


if __name__ == '__main__':
    main()
