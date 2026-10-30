# -*- coding: utf-8 -*-
"""列出运行期模块里对 out\\*.json 的引用（这些应改为 data\\*.json）。"""
import io
import re

MODS = ['viewer2.py', 'maps.py', 'effimg.py', 'eff.py', 'zipbin.py', 'zipbinnames.py',
        'tile.py', 'gsa.py', 'dimg.py', 'headtool.py', 'effboxes.py']
PAT = re.compile(r"out[\\/][A-Za-z0-9_\-]+\.json")
for m in MODS:
    try:
        s = io.open(m, encoding='utf-8').read()
    except FileNotFoundError:
        continue
    hits = [(i, ln.strip()[:110]) for i, ln in enumerate(s.splitlines(), 1) if PAT.search(ln)]
    if hits:
        print('==', m)
        for i, ln in hits:
            print('  %4d %s' % (i, ln))
