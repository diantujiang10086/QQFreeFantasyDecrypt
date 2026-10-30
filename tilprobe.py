"""Probe tile\\*.til headers (names are GBK; output goes to out/tile_probe.txt as UTF-8)."""
import glob
import os
import struct
import paths

ROOT = paths.sub('data/official/tile')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tile_probe.txt')


def hx(d, off, n):
    return ' '.join('%02x' % b for b in d[off:off + n])


def main():
    files = sorted(glob.glob(os.path.join(ROOT, '*.til')))
    lines = []
    lines.append('til count %d' % len(files))
    sizes = {}
    for p in files:
        sizes[os.path.getsize(p)] = sizes.get(os.path.getsize(p), 0) + 1
    lines.append('size histogram: %s' % sorted(sizes.items()))
    for p in files[:6]:
        d = open(p, 'rb').read()
        lines.append('=' * 78)
        lines.append('%s  %d bytes' % (os.path.basename(p), len(d)))
        lines.append('  head 96: ' + hx(d, 0, 96))
        lines.append('  ascii   : ' + ''.join(chr(b) if 32 <= b < 127 else '.' for b in d[:24]))
        lines.append('  u32@0..16: %s' % (struct.unpack_from('<16I', d, 0),))
        lines.append('  tail 64 : ' + hx(d, len(d) - 64, 64))
        lines.append('  size-4k mod 65536 = %d' % ((len(d) - 1024) % 65536))
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
