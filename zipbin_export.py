"""Dump every zipbin table to CSV (u32 columns + trailing bytes as hex).

Usage:
    python zipbin_export.py [outdir] [--max-rows N] [--only PATTERN]
"""
import os
import struct
import sys

import zipbin

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'zipbin_csv')


def dump(path, outdir, max_rows=None):
    r = zipbin.read(path)
    w = r['width']
    ncol = w // 4
    rest = w - ncol * 4
    name = os.path.splitext(os.path.basename(path))[0]
    out = os.path.join(outdir, name + '.csv')
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        hdr = ['row'] + ['u%d' % i for i in range(ncol)]
        if rest:
            hdr.append('tail_hex')
        fh.write(','.join(hdr) + '\n')
        for i, row in enumerate(r['rows'][:max_rows] if max_rows else r['rows']):
            vals = ['%d' % v for v in struct.unpack_from('<%dI' % ncol, row, 0)]
            if rest:
                vals.append(row[ncol * 4:].hex())
            fh.write('%d,%s\n' % (i, ','.join(vals)))
    return out, r['count'], os.path.getsize(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    outdir = args[0] if args else OUT
    max_rows = None
    only = None
    for a in sys.argv[1:]:
        if a.startswith('--max-rows='):
            max_rows = int(a.split('=', 1)[1])
        if a.startswith('--only='):
            only = a.split('=', 1)[1].lower()
    os.makedirs(outdir, exist_ok=True)
    total = 0
    index = []
    for name in sorted(os.listdir(zipbin.CLIENT)):
        if not name.lower().endswith('.bin'):
            continue
        if only and only not in name.lower():
            continue
        p = os.path.join(zipbin.CLIENT, name)
        try:
            h = zipbin.read(p)
        except Exception as e:                  # noqa: BLE001
            print('SKIP %-28s %s' % (name, e))
            continue
        out, n, sz = dump(p, outdir, max_rows)
        total += sz
        index.append((name, h['width'], h['count'], sz))
        print('%-30s w=%-5d rows=%-6d -> %8.1f KB' % (name, h['width'], h['count'], sz / 1024))
    with open(os.path.join(outdir, '_index.csv'), 'w', encoding='utf-8') as fh:
        fh.write('file,width,rows,csv_bytes\n')
        for name, w, n, sz in index:
            fh.write('%s,%d,%d,%d\n' % (name, w, n, sz))
    print('tables %d, csv total %.1f MB -> %s' % (len(index), total / 1048576, outdir))


if __name__ == '__main__':
    main()
