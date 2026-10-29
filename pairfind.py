# -*- coding: utf-8 -*-
"""Find a 2-byte-per-pixel twin of a 4-byte frame, to learn the channel order.

The alpha mask is channel-order independent, so a frame whose alpha mask is
identical in a 2-byte file and a 4-byte file is very likely the same artwork.
The 2-byte format's (R, G, B) nibbles then tell us which of the four bytes of
the 4-byte pixel carries each channel.

    python pairfind.py [--targets out/failA.txt] [--frames 3]
                       [--limit N] [--dump out/pairfind.txt]
"""
import argparse
import hashlib
import mmap
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg  # noqa: E402

SRC = dimg.SRC
T_LO = bytes((v & 0x0F) * 17 for v in range(256))
T_HI = bytes((v >> 4) * 17 for v in range(256))
NIB_LO = bytes(v & 0x0F for v in range(256))
NIB_HI = bytes(v >> 4 for v in range(256))


def open_mm(path):
    fh = open(path, 'rb')
    return fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)


def alpha4(d, px, n):
    return d[px + 3:px + 4 * n:4]


def alpha2(d, px, n):
    return d[px + 1:px + 2 * n:2].translate(T_HI)   # alpha = high nibble


def colours2(d, px, n):
    """(r, g, b) 8-bit byte strings for the 2-byte format."""
    b0 = d[px:px + 2 * n:2]
    b1 = d[px + 1:px + 2 * n:2]
    return b1.translate(T_LO), b0.translate(T_HI), b0.translate(T_LO)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--targets', default='out/failA.txt')
    ap.add_argument('--frames', type=int, default=2)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--dump', default='')
    a = ap.parse_args()
    out = []
    say = lambda s: (print(s, flush=True), out.append(s))

    targets = [l.strip() for l in open(a.targets, encoding='utf-8') if l.strip()]
    say(f'targets: {len(targets)}')

    # --- target index: (w, h, md5(alpha)) -> (file, frame) for 4-byte frames
    tindex = {}
    for name in targets:
        path = os.path.join(SRC, name)
        fh, d = open_mm(path)
        r = dimg.parse(d)
        if r.get('ok'):
            for i, (pre, w, h, px, bpp) in enumerate(r['frames'][:a.frames]):
                if px is None:
                    continue
                if bpp == 4:
                    key = (w, h, hashlib.md5(alpha4(d, px, w * h)).digest())
                else:
                    key = (w, h, hashlib.md5(alpha2(d, px, w * h)).digest())
                tindex.setdefault(key, []).append((name, i, bpp))
        d.close()
        fh.close()
    say(f'target frames indexed: {sum(len(v) for v in tindex.values())}')

    # --- scan the library for 2-byte frames whose alpha mask matches
    names = sorted(f for f in os.listdir(SRC) if f.endswith('.gsn') and f not in set(targets))
    if a.limit:
        names = names[:a.limit]
    say(f'scanning {len(names)} files...')
    hits = []
    for k, name in enumerate(names):
        if k % 2000 == 0:
            say(f'  {k}/{len(names)} hits={len(hits)}')
        path = os.path.join(SRC, name)
        try:
            fh, d = open_mm(path)
            r = dimg.parse(d)
        except Exception as e:                                  # noqa: BLE001
            say(f'  {name}: {e}')
            continue
        if r.get('ok'):
            for i, (pre, w, h, px, bpp) in enumerate(r['frames'][:a.frames]):
                if px is None or bpp != 2:
                    continue
                key = (w, h, hashlib.md5(alpha2(d, px, w * h)).digest())
                if key in tindex:
                    for tname, ti, tbpp in tindex[key]:
                        hits.append((name, i, px, w, h, tname, ti, tbpp))
        d.close()
        fh.close()
    say(f'hits: {len(hits)}')
    for (name, i, px, w, h, tname, ti, tbpp) in hits:
        say(f'  {name} f{i} ({w}x{h}) == {tname} f{ti} (bpp{tbpp})')
        if tbpp != 4:
            continue
        fh1, d1 = open_mm(os.path.join(SRC, name))
        fh2, d2 = open_mm(os.path.join(SRC, tname))
        r2 = dimg.parse(d2)
        pre2, w2, h2, px2, _ = r2['frames'][ti]
        n = w * h
        r2b, g2b, b2b = colours2(d1, px, n)
        raw4 = d2[px2:px2 + 4 * n]
        cols = [raw4[j::4] for j in range(4)]
        opaque = sum(1 for v in cols[3] if v)
        say(f'    opaque {opaque / n:.1%}')
        for label, ref, nib in (('R', r2b, NIB_LO), ('G', g2b, NIB_HI),
                                ('B', b2b, NIB_LO)):
            row = [sum(1 for x, y in zip(cols[j], nib) if (x >> 4) == y) / n
                   for j in range(4)]
            say(f'    {label} vs byte0..3 high-nibble agreement: '
                + ' '.join(f'{v:7.1%}' for v in row))
        d1.close()
        fh1.close()
        d2.close()
        fh2.close()

    if a.dump:
        with open(a.dump, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out) + '\n')
        print(f'wrote {a.dump}')


if __name__ == '__main__':
    main()
