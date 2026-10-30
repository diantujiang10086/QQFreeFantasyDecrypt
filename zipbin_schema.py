"""Cross-check zipbin row widths against the server source's `table('ov_x.bin', W)` calls."""
import collections
import csv
import os
import re

import zipbin

SRV = r'D:\ffo\FFO7.3\packages\自由幻想10.09\服务器\server'
CALL = re.compile(r"table\(\s*['\"]([\w.]+\.bin)['\"]\s*,\s*(\d+)\s*\)", re.I)


def server_widths():
    seen = collections.defaultdict(set)
    files = collections.defaultdict(set)
    for f in sorted(os.listdir(SRV)):
        if not f.endswith('.py'):
            continue
        try:
            s = open(os.path.join(SRV, f), 'rb').read().decode('utf-8', 'ignore')
        except OSError:
            continue
        for m in CALL.finditer(s):
            seen[m.group(1).lower()].add(int(m.group(2)))
            files[m.group(1).lower()].add(f)
    return seen, files


def main():
    srv, files = server_widths()
    print('server code declares widths for %d tables' % len(srv))
    rows = []
    for name in sorted(os.listdir(zipbin.CLIENT)):
        if not name.lower().endswith('.bin'):
            continue
        p = os.path.join(zipbin.CLIENT, name)
        try:
            h = zipbin.read(p)
            cw, cc = h['width'], h['count']
        except Exception:                       # noqa: BLE001
            cw = cc = -1
        sw = sorted(srv.get(name.lower(), []))
        rows.append({'file': name, 'client_width': cw, 'client_count': cc,
                     'server_width': sw[0] if len(sw) == 1 else (sw or ''),
                     'server_widths': ' '.join(map(str, sw)),
                     'match': bool(sw) and cw in sw, 'declared_in': ' '.join(sorted(files.get(name.lower(), [])))})
    n_match = sum(1 for r in rows if r['match'])
    n_decl = sum(1 for r in rows if r['server_widths'])
    n_bad = sum(1 for r in rows if r['server_widths'] and not r['match'])
    print('client tables %d, declared by server %d, width match %d, mismatch %d'
          % (len(rows), n_decl, n_match, n_bad))
    for r in rows:
        if r['server_widths'] and not r['match']:
            print('  MISMATCH %-30s client %-5s server %s' % (r['file'], r['client_width'], r['server_widths']))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'zipbin_schema.csv')
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=['file', 'client_width', 'client_count', 'server_width',
                                            'server_widths', 'match', 'declared_in'])
        wr.writeheader()
        for r in rows:
            wr.writerow(r)
    print('csv ->', out)
    undeclared = [r['file'] for r in rows if not r['server_widths']]
    print('not declared in server code (%d): %s' % (len(undeclared), ', '.join(undeclared[:20])))


if __name__ == '__main__':
    main()
