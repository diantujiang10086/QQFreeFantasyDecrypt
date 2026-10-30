"""Dump the per-record prefix words properly (64-byte prefix for frames>=1 in 2.36 files)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg  # noqa: E402
import paths

SRC = paths.sub('data/official/avatar')


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'npc1000101'
    path = os.path.join(SRC, 'npc', name + '.gsn')
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    print(name, 'oh', r['oh'], 'first_px', r['first_px'], 'frames', len(r['frames']))
    for i, (pre, w, h, px, bpp) in enumerate(r['frames']):
        plen = px - 16 - pre
        words = [dimg.u32(d, pre + 4 * j) for j in range(max(0, plen // 4))]
        print('f%d %2dx%-2d prefix@%d (%dB): %s' % (i, w, h, pre, plen, words))


if __name__ == '__main__':
    main()
