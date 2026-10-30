"""在剑客符咒服务端里找地图相关解码（gsm/msk/smp/npc/link/碰撞）。"""
import os
import re
import sys
import paths

ROOT = paths.SERVER
SKIP = {'__pycache__', 'runtime', 'site-packages', 'Lib', '.git', 'node_modules'}

TERMS = ['.gsm', '.msk', '.smp', 'gsm', 'msk', 'smp', 'collision', 'walkmask',
         'blockmask', 'mapinfo', 'map_info', 'load_map', 'loadmap', 'terrain']


def files():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP]
        for f in fns:
            if f.lower().endswith(('.py', '.ini', '.txt', '.lua', '.json')):
                yield os.path.join(dp, f)


def main():
    counts = {}
    hits = {}
    for p in files():
        try:
            t = open(p, 'r', encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        low = t.lower()
        for term in TERMS:
            c = low.count(term.lower())
            if c:
                counts[term] = counts.get(term, 0) + c
                hits.setdefault(term, []).append((c, p))
    print('term counts:', {k: v for k, v in sorted(counts.items(), key=lambda x: -x[1])})
    for term in ('gsm', 'msk', 'smp', 'collision', 'walkmask', 'blockmask', 'mapinfo'):
        lst = sorted(hits.get(term, []), reverse=True)[:8]
        print('\n==', term, len(hits.get(term, [])), 'files')
        for c, p in lst:
            print('  %4d %s' % (c, os.path.relpath(p, ROOT)))


if __name__ == '__main__':
    main()
