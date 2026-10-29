# -*- coding: utf-8 -*-
"""Why does the dir-table check reject these files?

Prints, for each file, the record walk (hint fp/oh), where the pixel-less
records sit, and every possible reading of the trailing 12-byte records.

usage: python empties.py [file ...]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg

SRC = dimg.SRC
DEFAULT = ['npc191405.gsn', 'npc304403.gsn', 'npc42102.gsn', 'npc488903.gsn',
           'npc61903.gsn', 'npc540201.gsn']


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def main():
    names = sys.argv[1:] or DEFAULT
    for name in names:
        d = open(os.path.join(SRC, name), 'rb').read()
        h = dimg.head(d)
        print(f'### {name} v{h["major"]}.{h["minor"]} nDirs={h["n_dirs"]} '
              f'hdr_nFrames={h["n_frames"]} size={len(d)}')
        got = False
        for fp, oh, tag in dimg.hints(h):
            frames, ok, why = dimg.walk(d, fp, oh, h['n_frames'])
            if not ok:
                print(f'    {tag}: walk stops -> {why}')
                continue
            got = True
            skip = [i for i, f in enumerate(frames) if f[3] is None]
            pix = len(frames) - len(skip)
            last_pre, lw, lh, lpx, lbpp = frames[-1]
            end = last_pre + oh + (0 if lpx is None else lbpp * lw * lh)
            tail = len(d) - end
            print(f'    {tag}: fp={fp} oh={oh} records={len(frames)} '
                  f'pixel_frames={pix} empty={len(skip)} at {skip}')
            print(f'    end={end} tail={tail} '
                  f'(12*nDirs+oh-28={12*h["n_dirs"] + oh - 28})')
            for base_off, label in ((len(d) - 12 * h['n_dirs'], 'tail-aligned'),
                                    (end, 'walk-end-aligned')):
                if base_off < 0 or base_off + 12 * h['n_dirs'] > len(d):
                    continue
                rows = [tuple(u32(d, base_off + 12 * i + 4 * j)
                              for j in range(3)) for i in range(h['n_dirs'])]
                sums = [sum(r[j] for r in rows) for j in range(3)]
                print(f'      {label} @{base_off}: {rows}  colsums={sums}')
            n = min(40, len(d))
            print(f'      last 40B hex: {d[len(d)-n:].hex(" ")}')
        if not got:
            print('    no hint walk succeeded')


if __name__ == '__main__':
    main()
