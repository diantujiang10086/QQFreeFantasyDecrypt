"""列出 pkg 里某张地图的全套文件，并看 .smp 头部。"""
import struct

import pkg

idx = pkg.pkg_index() if hasattr(pkg, 'pkg_index') else None


def entries():
    out = {}
    for path, ver, k, err in pkg.catalog():
        for j in range(k.count):
            key = k.key_at(j)
            if key.startswith('map/'):
                out.setdefault(key.rsplit('/', 1)[-1].rsplit('.', 1)[0], []).append(
                    (key, k.raw_at(j)))
    return out


def main():
    ent = entries()
    name = 'qw0001'
    print('map stems like', name, ent.get(name))
    for key, size in sorted(ent.get(name, [])):
        try:
            d = pkg.read(key)
        except Exception as exc:      # noqa: BLE001
            print(' ', key, size, 'ERR', exc)
            continue
        head = d[:48]
        print('\n== %s  %d B  head=%r' % (key, len(d), head[:32]))
        print('   u32@0..32', [struct.unpack_from('<I', d, o)[0] for o in range(0, 32, 4)] if len(d) >= 32 else None)


if __name__ == '__main__':
    main()
