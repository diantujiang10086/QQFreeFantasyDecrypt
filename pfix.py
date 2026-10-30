"""Print per-frame record prefixes (signed words) for 2.36-style files.

  python pfix.py npc1000101 npc1000102 npc1000103
  python pfix.py --all npc1000101        # also try every dir/action sibling
  python pfix.py --head head0101
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg  # noqa: E402
import paths

BASE = paths.sub('data/official/avatar')


def find(stem):
    for sub in ('npc', 'head'):
        p = os.path.join(BASE, sub, stem + '.gsn')
        if os.path.exists(p):
            return p
    raise FileNotFoundError(stem)


def words(d, off, n):
    return [struct.unpack_from('<i', d, off + 4 * j)[0] for j in range(n)]


def dump(path, nw=20):
    d = open(path, 'rb').read()
    h = dimg.head(d)
    r = dimg.parse(d)
    print('== %-14s size %6d  ver %d.%d  nDirs %d nFrames %d  w0..w2 %s'
          % (os.path.basename(path), len(d), h['major'], h['minor'],
             h['n_dirs'], h['n_frames'], (h['w0'], h['w1'], h['w2'])))
    print('   preamble@24 %s' % (words(d, 24, 9),))
    if not r['ok']:
        print('   PARSE FAIL', r.get('err'))
        return
    print('   fp %d oh %d frames %d dirs %s bpp %s tail %d extra %d'
          % (r['first_px'], r['oh'], len(r['frames']), r['dir_counts'], r['bpps'], r['tail'], r['extra']))
    for i, f in enumerate(r['frames']):
        pre, w, hh, px, bpp = f
        k = min(nw, max(1, (r['oh'] - 16) // 4))
        gap = '' if i == 0 else ' gap=%d' % (pre - r['frames'][i - 1][3] - r['frames'][i - 1][4] * r['frames'][i - 1][1] * r['frames'][i - 1][2])
        print('   f%-2d pre=%-7d %3dx%-3d px=%-7s bpp=%d%s  pre=%s'
              % (i, pre, w, hh, px, bpp, gap, words(d, pre, k)))


args = [a for a in sys.argv[1:] if not a.startswith('--')]
allmode = '--all' in sys.argv
for stem in args:
    if allmode:
        base = stem
        for sub in ('npc',):
            d0 = os.path.join(BASE, sub)
            for nm in sorted(os.listdir(d0)):
                if nm.startswith(base) and nm.endswith('.gsn') and nm[:-4].isdigit() is False:
                    dump(os.path.join(d0, nm))
    else:
        dump(find(stem))
