"""SMapFile (.smp) 头部与格式推断。"""
import struct

import pkg


def probe(name='qw0001'):
    d = pkg.read('map/%s.smp' % name)
    print('== %s.smp %d B' % (name, len(d)))
    print('magic', d[:28])
    print('u32 @28..80', [struct.unpack_from('<I', d, o)[0] for o in range(28, 80, 4)])
    print('u16 @28..48', [struct.unpack_from('<H', d, o)[0] for o in range(28, 48, 2)])
    for off in range(24, 80, 4):
        w = struct.unpack_from('<I', d, off)[0]
        h = struct.unpack_from('<I', d, off + 4)[0]
        if 0 < w < 20000 and 0 < h < 20000:
            for bpp in (1, 2, 3, 4):
                rest = len(d) - (off + 8)
                if rest == w * h * bpp:
                    print('CANDIDATE w,h @%d = %d x %d  bpp=%d  (data begins %d)' % (off, w, h, bpp, off + 8))
    return d


if __name__ == '__main__':
    probe()
