"""探查 .gsm 地图文件结构（从 pkg 直读，不落盘）。"""
import struct

import pkg

MAGIC = b'Tencent QQShowChat Map File'


def dump_map(name):
    d = pkg.read('map/' + name + '.gsm')
    print('== %s  %d bytes  magic_ok=%s' % (name, len(d), d[:28] == MAGIC))
    print('head u32 @28..108:', [struct.unpack_from('<I', d, o)[0] for o in range(28, 108, 4)])
    for magic in (b'BM', b'\x89PNG', b'QQF\x1a', b'<thumb', b'jpeg', b'JFIF'):
        pos, n = d.find(magic), 0
        while pos >= 0 and n < 5:
            print('   %r @ %d' % (magic, pos))
            n += 1
            pos = d.find(magic, pos + 1)
    w, h = struct.unpack_from('<II', d, 68)
    print('width,height @68 =', w, h)
    # 对象/标记扫描：u32 4 + id
    from collections import Counter
    kinds = Counter()
    for off in range(0, len(d) - 8, 4):
        a, b = struct.unpack_from('<II', d, off)
        if a in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10) and 0 < b < 100000:
            kinds[(a, b)] += 1
    print('kind/id pairs top:', kinds.most_common(12))


if __name__ == '__main__':
    for n in ('qw0001',):
        try:
            dump_map(n)
        except Exception as exc:      # noqa: BLE001
            print(n, 'ERR', type(exc).__name__, exc)
