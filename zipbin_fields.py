"""Recover which byte ranges of every zipbin row the server source actually interprets.

The server reads a table with `for row in table('ov_x.bin', W):` and then decodes the
fixed-width row with `struct.unpack_from('<fmt', row, OFF)` / `int.from_bytes(row[a:b])`.
This script aggregates those reads per table so we know the field map (and how much of
each row is still unexplained).
"""
import collections
import csv
import os
import re

import zipbin
import paths

SRV = os.path.join(paths.SERVER, 'server')
CALL = re.compile(r"table\(\s*['\"]([\w.]+\.bin)['\"]\s*,\s*(\d+)\s*\)", re.I)
ASSIGN = re.compile(r"([\w\s,\[\]\.]+?)=\s*struct\.unpack_from\(\s*['\"]([<>!=@]?[A-Za-z0-9]+)['\"]"
                    r"\s*,\s*([\w\.\[\]']+)\s*(?:,\s*(\d+)\s*)?\)")
PLAIN = re.compile(r"struct\.unpack_from\(\s*['\"]([<>!=@]?[A-Za-z0-9]+)['\"]\s*,\s*([\w\.\[\]']+)"
                   r"\s*(?:,\s*(\d+)\s*)?\)")
INTS = re.compile(r"int\.from_bytes\(\s*(?:row|r)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]")
ONE = re.compile(r"(?:row|r)\[\s*(\d+)\s*\]\s*(?:,|\))")
SIZE = {'b': 1, 'B': 1, '?': 1, 'h': 2, 'H': 2, 'i': 4, 'I': 4, 'l': 4, 'L': 4,
        'q': 8, 'Q': 8, 'f': 4, 'd': 8}


def fmt_size(fmt):
    return sum(SIZE.get(c, 0) for c in fmt.lstrip('<>!=@'))


def scan():
    """-> {table: {(offset, fmt): {'names': set, 'files': set}}}"""
    out = collections.defaultdict(dict)
    for f in sorted(os.listdir(SRV)):
        if not f.endswith('.py'):
            continue
        try:
            s = open(os.path.join(SRV, f), 'rb').read().decode('utf-8', 'ignore')
        except OSError:
            continue
        for m in CALL.finditer(s):
            name = m.group(1).lower()
            win = s[m.end():m.end() + 6000]
            ent = out[name]
            for a in ASSIGN.finditer(win):
                off = int(a.group(4) or 0)
                key = (off, a.group(2))
                d = ent.setdefault(key, {'names': set(), 'files': set()})
                d['names'].add(' '.join(a.group(1).split()))
                d['files'].add(f)
            for p in PLAIN.finditer(win):
                off = int(p.group(3) or 0)
                key = (off, p.group(1))
                d = ent.setdefault(key, {'names': set(), 'files': set()})
                d['files'].add(f)
            for i in INTS.finditer(win):
                a, b = int(i.group(1)), int(i.group(2))
                key = (a, 'int%d' % (b - a))
                d = ent.setdefault(key, {'names': set(), 'files': set()})
                d['files'].add(f)
            for o in ONE.finditer(win):
                key = (int(o.group(1)), 'u8')
                d = ent.setdefault(key, {'names': set(), 'files': set()})
                d['files'].add(f)
    return out


def main():
    found = scan()
    widths = {}
    for name in sorted(os.listdir(zipbin.CLIENT)):
        if name.lower().endswith('.bin'):
            try:
                widths[name.lower()] = zipbin.read(os.path.join(zipbin.CLIENT, name))['width']
            except Exception:                   # noqa: BLE001
                widths[name.lower()] = -1
    print('tables referenced by server code: %d' % len(found))
    rows = []
    cov = []
    for name, fields in found.items():
        w = widths.get(name, -1)
        covered = 0
        span = 0
        for (off, fmt), d in sorted(fields.items()):
            sz = fmt_size(fmt) if not fmt.startswith('int') and fmt != 'u8' else (
                int(fmt[3:]) if fmt.startswith('int') else 1)
            covered += sz
            span = max(span, off + sz)
            rows.append({'table': name, 'width': w, 'offset': off, 'fmt': fmt, 'size': sz,
                         'names': ' | '.join(sorted(d['names']))[:120],
                         'files': ' '.join(sorted(d['files']))[:120]})
        cov.append((name, w, covered, span, len(fields)))
    cov.sort(key=lambda t: -(t[2]))
    print('%-34s %5s %8s %6s %5s' % ('table', 'width', 'decoded', 'span', 'reads'))
    for name, w, covered, span, n in cov[:25]:
        print('%-34s %5d %8d %6d %5d' % (name, w, covered, span, n))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'zipbin_fields.csv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['table', 'width', 'offset', 'fmt', 'size', 'names', 'files'])
        wr.writeheader()
        for r in sorted(rows, key=lambda r: (r['table'], r['offset'])):
            wr.writerow(r)
    print('csv ->', out, '(%d field reads)' % len(rows))
    print('client tables with no row decoder: %d' % sum(1 for n in widths if n not in found))


if __name__ == '__main__':
    main()
