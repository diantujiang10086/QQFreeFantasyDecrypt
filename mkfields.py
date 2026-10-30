"""预计算 zipbin 表的字段名 → out/fields_cache.json（从 pkg 现读行宽 + 扫私服源码）。"""
import json
import os
import struct
import sys

import pkg
import zipbinnames

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'fields_cache.json')


def widths_from_pkg():
    w = {}
    for path, ver, k, err in pkg.catalog():
        for j in range(k.count):
            key = k.key_at(j)
            if key.startswith('zipbin/') and key.endswith('.bin'):
                try:
                    d = pkg.pkg(path).read_at(j)
                    w[os.path.basename(key)] = struct.unpack_from('<I', d, 8)[0]
                except Exception as ex:            # noqa: BLE001
                    print('skip', key, ex, file=sys.stderr)
    return w


def main():
    w = widths_from_pkg()
    print('tables with width:', len(w))
    fm = zipbinnames.fieldmap(w)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(fm, f, ensure_ascii=False)
    named = sum(1 for k, v in fm.items() if v)
    print('tables with fields:', named, '/', len(fm), '->', OUT)
    print('bytes', os.path.getsize(OUT))


if __name__ == '__main__':
    main()
