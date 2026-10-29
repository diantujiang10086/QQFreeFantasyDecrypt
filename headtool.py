"""Segment `avatar/head/*.gsn` files.

What the head family does differently from npc sprites
------------------------------------------------------
* The record grid is not a constant stride: the bytes between a pixel block and
  the next signature are 12, 16, 20 or 48 long (the value varies per record), so
  `oh` cannot be used.  A chain has to be found by searching.
* Every direction stores TWO images: a colour layer and an identical-size
  *grayscale* mask (mean |R-G|+|G-B| == 0 over its opaque pixels).
* The dir-table tail is still `12 * n_dirs`, and `sum(dir counts) == n_frames`
  with `records == 2 * n_frames`.

So: collect every plausible signature, then pick the chain of `2*n_frames`
records that ends exactly `12*n_dirs` bytes before EOF, preferring small gaps.

    python headtool.py --probe FILE      # show candidates + the chosen chain
    python headtool.py --scan            # every file -> out/head.csv
    python headtool.py --png out\\head     # export colour+mask PNGs
"""
import csv
import os
import struct
import sys

import dimg

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\head'
MAX_GAP = 512


def sig_at(d, p):
    if p < 0 or p + 16 > len(d):
        return None
    w, h, s, f = struct.unpack_from('<4I', d, p)
    if not (1 <= w <= 1024 and 1 <= h <= 1024):
        return None
    if f not in (1, 2) or s != 2 * f * w:
        return None
    return w, h, s, f


def candidates(d, start=60):
    out = []
    for p in range(start, len(d) - 16, 2):
        s = sig_at(d, p)
        if s:
            w, h, stride, flag = s
            if p + 16 + stride * h <= len(d):
                out.append((p, w, h, stride, flag))
    return out


def end_of(c):
    p, w, h, stride, _ = c
    return p + 16 + stride * h


def chain(cands, k_need, targets, max_gap=MAX_GAP):
    """Cheapest chain of k_need records whose last pixel ends at one of `targets`."""
    n = len(cands)
    succ = {}
    for i in range(n):
        e = end_of(cands[i])
        lst = []
        for j in range(i + 1, n):
            q = cands[j][0]
            if q < e:
                continue
            if q - e > max_gap:
                break
            lst.append(j)
        succ[i] = lst
    best = [None]

    def dfs(i, k, path, cost):
        if best[0] is not None and cost >= best[0][0]:
            return
        e = end_of(cands[i])
        if k == k_need:
            if e in targets:
                best[0] = (cost, list(path), e)
            return
        for j in succ[i]:
            dfs(j, k + 1, path + [j], cost + (cands[j][0] - e))

    for i in range(n):
        dfs(i, 1, [i], 0)
    return None if best[0] is None else ([cands[i] for i in best[0][1]], best[0][2])


def segment(d, n_frames=None, n_dirs=None, max_extra=256):
    """Pick the record chain that accounts for the whole file.  Returns
    (records, tail_extra, k) where tail_extra is the bytes between the last
    pixel block and the 12*n_dirs dir table."""
    if n_frames is None:
        h = dimg.head(d)
        n_frames, n_dirs = h['n_frames'], h['n_dirs']
    cands = candidates(d)
    base = len(d) - 12 * n_dirs
    targets = {base - e for e in range(0, max_extra + 1, 4) if base - e > 0}
    order = []
    for k in range(2 * n_frames, n_frames - 1, -1):
        order.append(k)
    for k in order:
        got = chain(cands, k, targets)
        if got:
            recs, end = got
            return recs, base - end, k
    return [], len(d), 0


def gray_score(d, c, alpha_min=1):
    p, w, h, stride, flag = c
    bpp = stride // w
    px = p + 16
    n = w * h
    if bpp == 2:
        raw = d[px:px + 2 * n]
        b0, b1 = raw[0::2], raw[1::2]
        a = bytes(x >> 4 for x in b1)
        rr = bytes(x & 15 for x in b1)
        gg = bytes(x >> 4 for x in b0)
        bb = bytes(x & 15 for x in b0)
    else:
        raw = d[px:px + 4 * n]
        rr = bytes(x >> 4 for x in raw[0::4])
        gg = bytes(x >> 4 for x in raw[1::4])
        bb = bytes(x >> 4 for x in raw[2::4])
        a = bytes(x >> 4 for x in raw[3::4])
    tot = cnt = 0
    for i in range(n):
        if a[i] >= alpha_min:
            tot += abs(rr[i] - gg[i]) + abs(gg[i] - bb[i])
            cnt += 1
    return (round(tot / cnt, 2) if cnt else 0.0), cnt


def probe(path):
    d = open(path, 'rb').read()
    h = dimg.head(d)
    print('=== %s  %d B  ver %d.%d.%d  frames=%d dirs=%d' % (
        os.path.basename(path), len(d), h['major'], h['minor'], h['n_dirs'],
        h['n_frames'], h['n_dirs']))
    print('  preamble:', [struct.unpack_from('<i', d, 24 + 4 * i)[0] for i in range(9)])
    cands = candidates(d)
    print('  candidates: %d  (dir table %d B, so px must end at %d)'
          % (len(cands), 12 * h['n_dirs'], len(d) - 12 * h['n_dirs']))
    for c in cands:
        g, cnt = gray_score(d, c)
        print('    sig@%-6d %3dx%-3d bpp=%d end=%-6d opaque=%-5d gray=%-6s'
              % (c[0], c[1], c[2], c[3] // c[1], end_of(c), cnt, g))
    recs, extra, k = segment(d)
    print('  chain: %d records (k=%d)  tail_extra=%d  %s' % (
        len(recs), k, extra, 'OK' if recs else 'MISS'))
    prev = None
    for i, c in enumerate(recs):
        gap = '' if prev is None else '  gap=%d' % (c[0] - prev)
        print('    #%-2d sig@%-6d %3dx%-3d bpp=%d%s' % (
            i, c[0], c[1], c[2], c[3] // c[1], gap))
        prev = end_of(c)


def scan(rows_out):
    rows = []
    bad = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.lower().endswith('.gsn'):
            continue
        d = open(os.path.join(SRC, fn), 'rb').read()
        h = dimg.head(d)
        recs, extra, k = segment(d)
        ok = bool(recs)
        g = [gray_score(d, c)[0] for c in recs]
        masks = sum(1 for i, v in enumerate(g) if i % 2 == 1 and v == 0.0)
        row = {
            'file': fn, 'size': len(d), 'n_frames': h['n_frames'],
            'n_dirs': h['n_dirs'], 'records': len(recs), 'k': k,
            'expected2': 2 * h['n_frames'], 'chain_ok': int(ok),
            'tail_extra': extra,
            'gap_min': min((recs[i + 1][0] - end_of(recs[i]) for i in range(len(recs) - 1)),
                           default=-1),
            'gap_max': max((recs[i + 1][0] - end_of(recs[i]) for i in range(len(recs) - 1)),
                           default=-1),
            'mask_odd': masks, 'color_even': sum(1 for i, v in enumerate(g) if i % 2 == 0 and v > 0),
            'bpps': '|'.join(sorted({str(c[3] // c[1]) for c in recs})),
            'sizes': ' '.join('%dx%d' % (c[1], c[2]) for c in recs),
        }
        rows.append(row)
        if not ok:
            bad.append(row)
    print('files: %d  chain ok: %d  bad: %d' % (len(rows), len(rows) - len(bad), len(bad)))
    ks = {}
    for r in rows:
        ks[(r['records'], r['k'], r['tail_extra'])] = ks.get((r['records'], r['k'], r['tail_extra']), 0) + 1
    print('(records, k, tail_extra) histogram:')
    for key in sorted(ks, key=lambda t: (-t[1], t[0], t[2])):
        print('   %-18s %d file(s)' % (str(key), ks[key]))
    print('odd records that are pure grayscale: %d' % sum(r['mask_odd'] for r in rows))
    print('even records that are colourful: %d' % sum(r['color_even'] for r in rows))
    print('gap range across all chains: %d..%d' % (
        min((r['gap_min'] for r in rows if r['gap_min'] >= 0), default=-1),
        max(r['gap_max'] for r in rows)))
    print('bpp sets:', sorted({r['bpps'] for r in rows}))
    for r in bad[:8]:
        print('  BAD %-12s records=%d k=%d extra=%d gaps=%d..%d' % (
            r['file'], r['records'], r['k'], r['tail_extra'], r['gap_min'], r['gap_max']))
    with open(rows_out, 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', rows_out)


def export(png_dir):
    os.makedirs(png_dir, exist_ok=True)
    n = nf = 0
    for fn in sorted(os.listdir(SRC)):
        if not fn.lower().endswith('.gsn'):
            continue
        d = open(os.path.join(SRC, fn), 'rb').read()
        recs, extra, k = segment(d)
        if not recs:
            print('  skip (no chain):', fn)
            nf += 1
            continue
        out = os.path.join(png_dir, fn[:-4])
        os.makedirs(out, exist_ok=True)
        paired = k == 2 * dimg.head(d)['n_frames']
        for i, c in enumerate(recs):
            p, w, h, stride, _ = c
            bpp = stride // w
            img = dimg.to_image(d, p + 16, w, h, bpp)
            if paired:
                name = 'd%d_%s.png' % (i // 2 + 1, 'c' if i % 2 == 0 else 'm')
            else:
                name = 'd%d.png' % (i + 1)
            img.save(os.path.join(out, name))
            n += 1
    print('wrote %d PNGs under %s (files skipped: %d)' % (n, png_dir, nf))


def main():
    a = sys.argv[1:]
    if '--probe' in a:
        probe(a[a.index('--probe') + 1])
    if '--scan' in a:
        scan(os.path.join(HERE, 'out', 'head.csv'))
    if '--png' in a:
        j = a.index('--png')
        export(a[j + 1] if j + 1 < len(a) else os.path.join(HERE, 'out', 'head'))
    if not a:
        print(__doc__)


if __name__ == '__main__':
    main()
