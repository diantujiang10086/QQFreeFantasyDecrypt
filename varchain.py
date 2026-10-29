# -*- coding: utf-8 -*-
"""Chain search for the unparsed variant family (npc5397xx/5398xx/5400xx/5488xx/
5489xx/5490xx).

Hypothesis: a frame record is  [L bytes of record head][2*w*h pixel bytes],
with (w,h) stored at word offset `wo` inside the head (0,0 == pixel-less frame),
exactly like the main format but with a different head length / word layout.

This brute-forces (start, wo, L) and keeps the parameter sets that walk the
header's n_frames records and land exactly on the trailing direction table.

    python varchain.py <file...>
"""
import mmap
import struct
import sys

DIRW = 12


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def u16(d, o):
    return struct.unpack_from('<H', d, o)[0]


def chain(d, p0, wo, L, n):
    """Walk n records.  Returns (end_offset, [(w,h)...]) or None."""
    p = p0
    sizes = []
    for _ in range(n):
        if p + L > len(d):
            return None
        a, b = u32(d, p + wo), u32(d, p + wo + 4)
        if a == 0 and b == 0:
            sizes.append((0, 0))
            p += L
            continue
        if not (1 <= a <= 8192 and 1 <= b <= 8192):
            return None
        if p + L + 2 * a * b > len(d):
            return None
        sizes.append((a, b))
        p += L + 2 * a * b
    return p, sizes


def dir_table(d, n_dirs, n_frames):
    if n_dirs <= 0 or len(d) < DIRW * n_dirs:
        return None
    o = len(d) - DIRW * n_dirs
    counts = []
    for _ in range(n_dirs):
        n, a, b = u32(d, o), u32(d, o + 4), u32(d, o + 8)
        if a or b or not (0 < n <= 65535):
            return None
        counts.append(n)
        o += DIRW
    return counts if sum(counts) == n_frames else None


def probe(path):
    with open(path, 'rb') as fh:
        try:
            d = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        except ValueError:
            return
        n = u16(d, 16)
        nd = u16(d, 20)
        size = len(d)
        print(f'== {path.split(chr(92))[-1]}  size={size:,} frames={n} dirs={nd}')
        print('   head words: ' + ' '.join(str(u32(d, o)) for o in range(24, 24 + 4 * 26, 4)))
        counts0 = dir_table(d, nd, n)
        print(f'   dir table @EOF: {"counts=" + str(counts0) if counts0 else "not a plain table"}')
        hits = []
        best = []
        for p0 in range(24, 132, 4):
            for wo in (0, 4, 8, 12, 16, 20, 24, 28, 32, 36):
                for L in (16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 64, 72, 80):
                    r = chain(d, p0, wo, L, n)
                    if not r:
                        continue
                    end, sizes = r
                    rest = size - end
                    c = dir_table(d, nd, n)
                    if c is not None and rest == DIRW * nd:
                        hits.append((p0, wo, L, rest, sizes))
                    elif 0 <= rest <= 4096:
                        best.append((rest, p0, wo, L, sizes))
        for p0, wo, L, rest, sizes in hits:
            px = sum(2 * a * b for a, b in sizes)
            skip = sum(1 for a, b in sizes if a == 0)
            print(f'   HIT start={p0} wo={wo} L={L} rest={rest} px={px:,} skip={skip}')
            print('       first sizes: ' + str(sizes[:8]))
        if not hits:
            best.sort()
            print(f'   no exact hit; {len(best)} near misses (rest <= 4096):')
            for rest, p0, wo, L, sizes in best[:6]:
                print(f'     rest={rest} start={p0} wo={wo} L={L} first={sizes[:6]}')
        d.close()


if __name__ == '__main__':
    for p in sys.argv[1:]:
        probe(p)
