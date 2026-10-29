# -*- coding: utf-8 -*-
"""
Structured hypothesis search for the DIMG (.gsn) container.

Model:
  [file header H bytes]
  then per frame either
     layout A: record(R bytes) + pixels(w*h*2)
     layout B: record(R bytes)            (all records first)
  ...then all pixel blocks in frame order (layout B only)
  optionally T trailing bytes.

A record must contain exactly one index k with
     rec[k+2] == 2*rec[k]  and  rec[k+3] == 1
which is the (w, h, stride, flag=1) tail observed in every real file.
"""
import os
import struct
import sys

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'

SAMPLES = [
    'npc64402.gsn', 'npc64403.gsn', 'npc64404.gsn', 'npc64405.gsn',
    'npc64401.gsn', 'npc64501.gsn', 'npc59503.gsn', 'npc57101.gsn',
    'npc57301.gsn', 'npc559201t.gsn', 'npc559201.gsn', 'npc20406.gsn',
    'npc108905.gsn', 'npc174501.gsn', 'npc1955501.gsn', 'npc61401.gsn',
    'npc57102.gsn', 'npc58501.gsn', 'npc64406.gsn', 'npc540201.gsn',
]


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def rec_tail(rec):
    """Return list of k where rec[k+2]==2*rec[k] and rec[k+3]==1."""
    ks = []
    for k in range(0, len(rec) - 4):
        w = rec[k]
        h = rec[k + 1]
        if 0 < w <= 4096 and 0 < h <= 4096 and rec[k + 2] == 2 * w and rec[k + 3] == 1:
            ks.append(k)
    return ks


def walk(data, size, nframes, H, R, layout):
    pos = H
    frames = []
    for i in range(nframes):
        if pos + R * 4 > size:
            return None
        rec = [u32(data, pos + 4 * j) for j in range(R)]
        ks = rec_tail(rec)
        if len(ks) != 1:
            return None
        k = ks[0]
        w, h = rec[k], rec[k + 1]
        frames.append((pos, k, w, h, rec))
        if layout == 'A':
            pos = pos + R * 4 + w * h * 2
        else:
            pos += R * 4
    if layout == 'B':
        for _, _, w, h, _ in frames:
            pos += w * h * 2
    return frames, pos


def search(data, size, verbose=True):
    hits = []
    hdr = u32(data, 16)
    hdr2 = u32(data, 20)
    for nframes in sorted({hdr, hdr2, hdr * hdr2}):
        if not (0 < nframes <= 4096):
            continue
        for H in range(0, 200, 4):
            for R in range(6, 129):
                for layout in ('A', 'B'):
                    r = walk(data, size, nframes, H, R, layout)
                    if not r:
                        continue
                    frames, pos = r
                    trail = size - pos
                    if 0 <= trail <= 64 and trail % 4 == 0:
                        hits.append((layout, nframes, H, R, trail, frames))
    return hits


def main():
    names = sys.argv[1:] or SAMPLES
    for name in names:
        path = os.path.join(SRC, name)
        if not os.path.isfile(path):
            print(f'{name}: MISSING')
            continue
        data = open(path, 'rb').read()
        size = len(data)
        hits = search(data, size)
        print('=' * 90)
        print(f'{name} size={size} n@16={u32(data,16)} n@20={u32(data,20)} '
              f'major={u32(data,8)&0xffff} f12={u32(data,12)}  hits={len(hits)}')
        seen = set()
        shown = 0
        for layout, nframes, H, R, trail, frames in hits:
            key = (R, trail, tuple((f[2], f[3]) for f in frames))
            if key in seen:
                continue
            seen.add(key)
            shown += 1
            if shown > 8:
                continue
            print(f'   layout={layout} N={nframes} H={H} R={R*4}B trail={trail} '
                  f'sizes={[(f[2], f[3]) for f in frames[:6]]}')
            print(f'      rec0={frames[0][4]}')
        if not hits:
            print('   !! no solution')


if __name__ == '__main__':
    main()
