"""Dump head + tail bytes of .gsa files to find frame-table structure."""
import os
import struct
import sys

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\res'


def show(p):
    d = open(p, 'rb').read()
    print('=== %s  %d B' % (os.path.relpath(p, ROOT), len(d)))
    u = struct.unpack_from('<10I', d, 8)
    print('   u:', u)
    print('   first 64 after 52:', d[52:116].hex(' '))
    print('   last 96:', d[-96:].hex(' '))
    tail16 = [struct.unpack_from('<I', d, len(d) - 16 - 4 * i)[0] for i in range(4)]
    print('   last 4 u32:', tail16)
    for fs in (32 * 32 * 2, 64 * 32, 96 * 96 * 2, 4096, 2048):
        body = len(d) - 52
        print('     body=%d  /%d = %.3f  rem %d' % (body, fs, body / fs, body % fs))


if __name__ == '__main__':
    for a in sys.argv[1:]:
        show(a if os.path.isabs(a) else os.path.join(ROOT, a))
