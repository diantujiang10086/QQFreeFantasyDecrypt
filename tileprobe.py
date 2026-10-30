"""Probe binary headers of tile\\*.til / tileimg*.dat / terrashp*.dat."""
import os
import struct
import sys

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\tile'


def hexdump(d, off, n=64):
    return ' '.join('%02x' % b for b in d[off:off + n])


def dump(name, n=160):
    p = os.path.join(ROOT, name)
    d = open(p, 'rb').read()
    print('=' * 78)
    print('%s   %d bytes' % (name, len(d)))
    print('  head:', hexdump(d, 0, min(n, len(d))))
    print('  u32 @0..64:', struct.unpack_from('<16I', d, 0) if len(d) >= 64 else '')
    print('  tail:', hexdump(d, max(0, len(d) - 48), 48))
    # look for a magic ascii
    print('  ascii head:', ''.join(chr(b) if 32 <= b < 127 else '.' for b in d[:32]))


def main():
    names = sys.argv[1:]
    if not names:
        names = ['tileimg.dat', 'tileimg01.dat', 'terrashp.dat']
    for n in names:
        dump(n)


if __name__ == '__main__':
    main()
