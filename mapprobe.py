"""地图/碰撞相关的关键文件取样。"""
import json
import os
import paths

ROOT = paths.SERVER


def head(p, n=40, enc='utf-8'):
    p = os.path.join(ROOT, p)
    print('=== %s (%d B)' % (p, os.path.getsize(p)))
    t = open(p, 'r', encoding=enc, errors='ignore').read()
    for i, line in enumerate(t.splitlines()[:n], 1):
        print('%4d| %s' % (i, line[:200]))
    print()


def grep(p, pat, limit=30, enc='utf-8'):
    import re
    p2 = os.path.join(ROOT, p)
    print('=== grep %s / %s' % (p, pat))
    t = open(p2, 'r', encoding=enc, errors='ignore').read()
    n = 0
    for i, line in enumerate(t.splitlines(), 1):
        if re.search(pat, line, re.I):
            print('%5d| %s' % (i, line.strip()[:200]))
            n += 1
            if n >= limit:
                break
    print()


if __name__ == '__main__':
    d = json.load(open(os.path.join(ROOT, 'data/client60/audit/portal-coordinates.json'),
                       encoding='utf-8'))
    print('portal-coordinates type', type(d).__name__, 'len', len(d))
    if isinstance(d, dict):
        ks = list(d)[:5]
        print('keys sample', ks)
        print('first value', json.dumps(d[ks[0]], ensure_ascii=False)[:600])
    elif isinstance(d, list):
        print('first', json.dumps(d[0], ensure_ascii=False)[:600])
    print()
    grep('server/portals60.py', r'gsm|msk|map', 25)
    grep('server/npcs60.py', r'gsm|msk|map', 20)
