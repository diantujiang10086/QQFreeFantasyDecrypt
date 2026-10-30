"""zipbin container decoder: header = <4I  magic 0x5566, version 1, row width, row count>.

Verified against the server source (`server/resources60.py:table`, `server/extra_tables60.py:_read`):
    magic, version, size, count = struct.unpack_from('<4I', data, 0)
    assert (magic, version, size) == (0x5566, 1, width) and len(data) == 16 + size * count
"""
import collections
import csv
import os
import struct
import sys

CLIENT = r'F:\WG自由幻想\自由幻想\data\data\official\zipbin'
SERVER = r'D:\ffo\FFO7.3\packages\自由幻想10.09\服务器\data\client60\resources\zipbin'
MAGIC = 0x5566


def read(path, width=None):
    return read_bytes(open(path, 'rb').read(), path, width)


def read_bytes(d, path='<mem>', width=None):
    if len(d) < 16:
        raise ValueError('%s: %d bytes, too short' % (path, len(d)))
    magic, ver, size, count = struct.unpack_from('<4I', d, 0)
    if magic != MAGIC:
        raise ValueError('%s: magic 0x%04X != 0x5566' % (path, magic))
    if width is not None and size != width:
        raise ValueError('%s: row width %d != expected %d' % (path, size, width))
    if len(d) != 16 + size * count:
        raise ValueError('%s: size %d != 16 + %d*%d = %d'
                         % (path, len(d), size, count, 16 + size * count))
    return {'magic': magic, 'ver': ver, 'width': size, 'count': count,
            'rows': [d[16 + i * size:16 + (i + 1) * size] for i in range(count)]}


def rows(path):
    return read(path)['rows']


def u32s(path, n=None):
    """Decode every row as u32 words (debug helper)."""
    r = read(path)
    n = n or r['width'] // 4
    return [[struct.unpack_from('<%dI' % n, row, 0)] for row in r['rows']]


def census(root=CLIENT):
    out = []
    for name in sorted(os.listdir(root)):
        if not name.lower().endswith('.bin'):
            continue
        p = os.path.join(root, name)
        try:
            h = read(p)
            out.append({'file': name, 'bytes': os.path.getsize(p), 'width': h['width'],
                        'count': h['count'], 'ver': h['ver'], 'ok': True})
        except Exception as e:                      # noqa: BLE001 - report, don't crash
            out.append({'file': name, 'bytes': os.path.getsize(p), 'width': 0,
                        'count': 0, 'ver': 0, 'ok': False, 'err': str(e)})
    return out


def compare_dirs(a=CLIENT, b=SERVER):
    fa = {n: os.path.getsize(os.path.join(a, n)) for n in os.listdir(a) if n.endswith('.bin')}
    fb = {n: os.path.getsize(os.path.join(b, n)) for n in os.listdir(b) if n.endswith('.bin')}
    both = sorted(set(fa) & set(fb))
    diff = [n for n in both if fa[n] != fb[n]]
    return {'client': len(fa), 'server': len(fb), 'both': len(both),
            'only_client': sorted(set(fa) - set(fb)), 'only_server': sorted(set(fb) - set(fa)),
            'size_differs': [(n, fa[n], fb[n]) for n in diff]}


def dump_csv(path, out):
    r = read(path)
    w = r['width']
    ncol = w // 4
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.writer(fh)
        wr.writerow(['row'] + ['u%d' % i for i in range(ncol)])
        for i, row in enumerate(r['rows']):
            vals = list(struct.unpack_from('<%dI' % ncol, row, 0))
            rest = row[ncol * 4:]
            if rest:
                vals.append(rest.hex())
            wr.writerow([i] + vals)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'census'
    if cmd == 'census':
        rows_ = census()
        ok = [r for r in rows_ if r['ok']]
        bad = [r for r in rows_ if not r['ok']]
        print('bin files %d  ok %d  bad %d' % (len(rows_), len(ok), len(bad)))
        tot = sum(r['bytes'] for r in rows_)
        print('total %d bytes = %.2f MB, rows %d' % (tot, tot / 1048576, sum(r['count'] for r in rows_)))
        hist = collections.Counter(r['width'] for r in ok)
        print('row widths: %d distinct, top' % len(hist), hist.most_common(12))
        by_rows = sorted(ok, key=lambda r: -r['count'])[:12]
        print('most rows:', [(r['file'], r['count'], r['width']) for r in by_rows])
        for r in bad:
            print('BAD', r['file'], r.get('err'))
        if len(sys.argv) > 2:
            with open(sys.argv[2], 'w', newline='', encoding='utf-8') as fh:
                wr = csv.DictWriter(fh, fieldnames=['file', 'bytes', 'width', 'count', 'ver', 'ok'])
                wr.writeheader()
                for r in rows_:
                    wr.writerow({k: r.get(k, '') for k in wr.fieldnames})
            print('csv ->', sys.argv[2])
    elif cmd == 'show':
        p = sys.argv[2]
        r = read(p)
        print('%s  width %d  rows %d' % (os.path.basename(p), r['width'], r['count']))
        for i, row in enumerate(r['rows'][:int(sys.argv[3]) if len(sys.argv) > 3 else 5]):
            print('  %3d %s' % (i, row.hex(' ')))
    elif cmd == 'csv':
        p, out = sys.argv[2], sys.argv[3]
        dump_csv(p, out)
        print('csv ->', out)
    elif cmd == 'compare':
        print(compare_dirs())
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
