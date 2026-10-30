"""Print the raw preamble / prefix words of a file (for comparing body vs head geometry)."""
import struct
import sys

import dimg
import paths

BASE = paths.sub('data/official/avatar')


def words(d, off, n):
    return [struct.unpack_from('<i', d, off + 4 * j)[0] for j in range(n)]


def dump(path, nw=20):
    d = open(path, 'rb').read()
    h = dimg.head(d)
    r = dimg.parse(d)
    print('==', path.split('\\')[-1], 'size', len(d))
    print('   ver %d.%d nDirs %d nFrames %d w0..w2 %s' %
          (h['major'], h['minor'], h['n_dirs'], h['n_frames'], (h['w0'], h['w1'], h['w2'])))
    print('   preamble@24 :', words(d, 24, 9), '(unsigned)', [w & 0xFFFFFFFF for w in words(d, 24, 9)])
    print('   fp', r['first_px'], 'oh', r['oh'], 'frames', len(r['frames']),
          'dirs', r['dir_counts'], 'bpps', r['bpps'])
    for i, f in enumerate(r['frames'][:8]):
        pre, w, hh, px, bpp = f
        k = min(nw, (r['oh'] - 16) // 4)
        print('   f%d pre=%d %dx%d px=%s bpp=%d prefix=%s' % (i, pre, w, hh, px, bpp, words(d, pre, k)))


for p in sys.argv[1:]:
    dump(p)
