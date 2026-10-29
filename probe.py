# -*- coding: utf-8 -*-
"""
DIMG (.gsn) format probe.
Goal: find (header_len, desc_len_int32) such that
      file_size == header_len + sum(desc_len*4 + w*h*2)
i.e. exact byte conservation.  Layout A = interleaved desc/pixels,
Layout B = all descriptors first, then all pixel blocks.
"""
import os
import struct
import sys

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'

SAMPLES = [
    'npc64402.gsn', 'npc64403.gsn', 'npc64404.gsn', 'npc64405.gsn',
    'npc64401.gsn', 'npc64501.gsn', 'npc59503.gsn', 'npc57101.gsn',
    'npc57301.gsn', 'npc559201t.gsn', 'npc559201.gsn', 'npc20406.gsn',
    'npc108905.gsn', 'npc174501.gsn', 'npc1955501.gsn', 'npc64402.gsn',
]


def u32(data, off):
    return struct.unpack_from('<I', data, off)[0]


def header_info(data):
    assert data[:8] == b'QQF\x1aDIMG', 'bad magic'
    major = struct.unpack_from('<H', data, 8)[0]
    f10 = struct.unpack_from('<H', data, 10)[0]
    f12 = struct.unpack_from('<H', data, 12)[0]
    f14 = struct.unpack_from('<H', data, 14)[0]
    return dict(major=major, f10=f10, f12=f12, f14=f14,
                n_at16=u32(data, 16), n_at20=u32(data, 20))


def find_landmarks(data, start, stop):
    """Return list of (offset, w, h) where u32[o]=w, u32[o+4]=h, u32[o+8]=2w, u32[o+12]=1."""
    out = []
    for o in range(start, stop - 16, 4):
        w = u32(data, o)
        h = u32(data, o + 4)
        if w == 0 or h == 0 or w > 4096 or h > 4096:
            continue
        if u32(data, o + 8) == 2 * w and u32(data, o + 12) == 1:
            out.append((o, w, h))
    return out


def try_layout_A(data, size, nframes, H, K):
    """header(H) + per frame: K int32 desc, then w*h*2 pixels."""
    pos = H
    frames = []
    for _ in range(nframes):
        end = pos + K * 4
        if end > size:
            return None
        marks = find_landmarks(data, pos, end)
        if len(marks) != 1:
            return None
        o, w, h = marks[0]
        vals = [u32(data, pos + 4 * i) for i in range(K)]
        frames.append((vals, o - pos, w, h))
        pos = end + w * h * 2
    return frames, pos


def try_layout_B(data, size, nframes, H, K):
    """header(H) + nframes*K int32 descs, then pixel blocks in order."""
    pos = H
    frames = []
    for _ in range(nframes):
        end = pos + K * 4
        if end > size:
            return None
        marks = find_landmarks(data, pos, end)
        if len(marks) != 1:
            return None
        o, w, h = marks[0]
        vals = [u32(data, pos + 4 * i) for i in range(K)]
        frames.append((vals, o - pos, w, h))
        pos = end
    total = pos + sum(w * h * 2 for _, _, w, h in frames)
    if total != size:
        return None
    return frames, total


def main():
    files = [f for f in SAMPLES if os.path.isfile(os.path.join(SRC, f))]
    print('samples present:', len(files))
    for name in files:
        path = os.path.join(SRC, name)
        data = open(path, 'rb').read()
        size = len(data)
        hi = header_info(data)
        print('=' * 100)
        print(f'{name}  size={size}  major={hi["major"]} f10={hi["f10"]} '
              f'f12={hi["f12"]} f14={hi["f14"]} n@16={hi["n_at16"]} n@20={hi["n_at20"]}')
        # first int32s
        head = ' '.join(f'{i}:{u32(data, i*4)}' for i in range(14))
        print('  int32[0..13]:', head)
        marks = find_landmarks(data, 8, min(size, 8 + 40 * 40))
        print(f'  landmarks in first ~40 int32s ({len(marks)}):',
              [(o, w, h) for o, w, h in marks[:6]])

        hits = []
        for nframes in {hi['n_at16'], hi['n_at20']}:
            if not (0 < nframes < 100000):
                continue
            for H in range(16, 41, 4):
                for K in range(4, 33):
                    r = try_layout_A(data, size, nframes, H, K)
                    if r:
                        frames, pos = r
                        if pos == size:
                            hits.append(('A', nframes, H, K, frames))
                    r = try_layout_B(data, size, nframes, H, K)
                    if r:
                        frames, pos = r
                        hits.append(('B', nframes, H, K, frames))
        if not hits:
            print('  !! no exact byte-conservation solution')
        for layout, nframes, H, K, frames in hits[:6]:
            print(f'  ** MATCH layout={layout} nframes={nframes} header={H} desc={K} int32({K*4}B)')
            for i, (vals, woff, w, h) in enumerate(frames[:8]):
                print(f'     frame{i}: w={w} h={h} w_at_desc[{woff//4}] vals={vals}')
    print('=' * 100)


if __name__ == '__main__':
    main()
