"""Dump the u32 header of one .gsa file with explicit indices."""
import struct
import sys
import os

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\res'


def dump(p, name=None):
    d = open(p, 'rb').read()
    print('===', name or os.path.relpath(p, ROOT), len(d))
    print('   magic', d[:8])
    for off in range(8, 56, 4):
        v = struct.unpack_from('<I', d, off)[0]
        print('   @%-3d u32=%-12d hex=%08x' % (off, v, v))


if __name__ == '__main__':
    for a in sys.argv[1:]:
        p = a if os.path.isabs(a) else os.path.join(ROOT, a)
        dump(p)
