# -*- coding: utf-8 -*-
"""Print the header words of .gsn files side by side.

    python hdr.py <file> [file...]
"""
import mmap
import struct
import sys


def main():
    for p in sys.argv[1:]:
        fh = open(p, 'rb')
        d = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        u16 = lambda o: struct.unpack_from('<H', d, o)[0]      # noqa: E731
        u32 = lambda o: struct.unpack_from('<I', d, o)[0]      # noqa: E731
        name = p.replace('\\', '/').split('/')[-1]
        b = [d[i] for i in range(24)]
        print(f'{name:20s} size={len(d):>10,}')
        print(f'{"":20s} raw24={bytes(b).hex(" ")}')
        print(f'{"":20s} u16@0..22={[u16(i * 2) for i in range(12)]}')
        print(f'{"":20s} u32@0..20={[u32(i * 4) for i in range(6)]}')
        print(f'{"":20s} preamble@24={[u32(24 + 4 * i) for i in range(9)]}')
        print(f'{"":20s} prefix@60  ={[u32(60 + 4 * i) for i in range(6)]}')
        print(f'{"":20s} sig@84     ={[u32(84 + 4 * i) for i in range(4)]}')
        d.close()
        fh.close()


if __name__ == '__main__':
    main()
