"""Analyze object\\ : .gso (DIMG) + .mask side files + small configs.

    python objstat.py            # sizes / versions / pairing
    python objstat.py --mask     # dump a few .mask samples of different sizes
"""
import collections
import os
import struct
import sys

import dimg

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\object'


def walk(ext):
    out = []
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if os.path.splitext(f)[1].lower() == ext:
                out.append(os.path.join(dp, f))
    return sorted(out)


def masks():
    ms = walk('.mask')
    sizes = collections.Counter(os.path.getsize(p) for p in ms)
    print('mask files', len(ms), 'distinct sizes', len(sizes))
    for s, c in sorted(sizes.items())[:12]:
        print('   %6d B x %d' % (s, c))
    print('   ...')
    for s, c in sorted(sizes.items())[-6:]:
        print('   %6d B x %d' % (s, c))
    shown = set()
    for p in ms:
        s = os.path.getsize(p)
        if s in shown or len(shown) >= 5:
            continue
        shown.add(s)
        d = open(p, 'rb').read()
        print('== %s  %d B' % (os.path.relpath(p, ROOT), len(d)))
        print('   head', d[:40].hex(' '))
        if len(d) > 40:
            print('   tail', d[-32:].hex(' '))


def gso():
    gs = walk('.gso')
    print('gso files', len(gs))
    ver = collections.Counter()
    nd = collections.Counter()
    nf = collections.Counter()
    perdir = collections.Counter()
    big = []
    tot = 0
    for p in gs:
        sz = os.path.getsize(p)
        tot += sz
        with open(p, 'rb') as fh:
            b = fh.read(24)
        ver['%d.%d' % (dimg.u16(b, 8), dimg.u16(b, 12))] += 1
        nd[dimg.u16(b, 20)] += 1
        nf[dimg.u16(b, 16)] += 1
        perdir[os.path.relpath(os.path.dirname(p), ROOT)] += 1
        big.append((sz, os.path.relpath(p, ROOT)))
    print('  total %.1f MB' % (tot / 1048576))
    print('  versions:', dict(ver.most_common()))
    print('  n_dirs:', dict(sorted(nd.items())))
    print('  n_frames top:', nf.most_common(12), 'max', max(nf))
    print('  per subdir:', dict(perdir.most_common()))
    print('  biggest:')
    for sz, n in sorted(big)[-8:][::-1]:
        print('    %10d B  %s' % (sz, n))


def pairing():
    gs = {os.path.splitext(os.path.relpath(p, ROOT))[0] for p in walk('.gso')}
    ms = {os.path.splitext(os.path.relpath(p, ROOT))[0] for p in walk('.mask')}
    print('gso %d mask %d both %d gso-only %d mask-only %d'
          % (len(gs), len(ms), len(gs & ms), len(gs - ms), len(ms - gs)))
    print('  mask-only sample', sorted(ms - gs)[:5])
    print('  gso-only sample', sorted(gs - ms)[:5])


def main():
    if '--mask' in sys.argv:
        masks()
        return
    if '--pair' in sys.argv:
        pairing()
        return
    gso()
    pairing()


if __name__ == '__main__':
    main()
