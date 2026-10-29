# -*- coding: utf-8 -*-
"""Run-length segmentation of the unparsed variant files.

Splits the file into (a) maximal runs of one repeated 32-bit word and (b) the
gaps between them, then prints the gaps as 32-bit words.  A gap is a record
head; a long run is a solid-colour frame's pixel payload.

    python varruns.py <file...> [--min N]
"""
import mmap
import struct
import sys

MIN = 64


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def segs(d, min_len):
    out = []
    n = len(d) // 4
    i = 0
    while i < n:
        v = u32(d, 4 * i)
        j = i + 1
        while j < n and u32(d, 4 * j) == v:
            j += 1
        ln = 4 * (j - i)
        if ln >= min_len:
            out.append((4 * i, ln, v, True))
        i = j
    return out


def show(path):
    with open(path, 'rb') as fh:
        d = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        print(f'== {path.split(chr(92))[-1]} size={len(d):,} frames={struct.unpack_from("<H", d, 16)[0]} '
              f'dirs={struct.unpack_from("<H", d, 20)[0]}')
        print('   @24 head words: ' + ' '.join(str(u32(d, o)) for o in range(24, 24 + 4 * 19, 4)))
        s = segs(d, MIN)
        print(f'   {len(s)} runs >= {MIN} B')
        prev_end = 100
        for k, (off, ln, v, _) in enumerate(s[:40]):
            gap = off - prev_end
            gw = []
            if 0 < gap <= 160:
                gw = [u32(d, prev_end + 4 * i) for i in range(gap // 4)]
            print(f'   run{k:<3} @{off:>10,} len={ln:>9,} val=0x{v:08X} gap_before={gap:>5} bytes'
                  + (f' words={gw}' if gw else ''))
            prev_end = off + ln
        tail = len(d) - prev_end
        if tail:
            o = prev_end
            words = [u32(d, o + 4 * i) for i in range(min(tail // 4, 24))]
            print(f'   after last run: {tail:,} bytes @{prev_end:,} words={words}')
        d.close()


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if '--min' in sys.argv:
        MIN = int(sys.argv[sys.argv.index('--min') + 1])
    for p in a:
        show(p)
