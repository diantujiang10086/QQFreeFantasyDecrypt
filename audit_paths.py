# -*- coding: utf-8 -*-
"""静态审计：运行期模块里是否还有外部盘符字面量（除 FFO_DATA 之外）。"""
import io
import re

MODS = ['viewer2.py', 'maps.py', 'pkg.py', 'gsa.py', 'tile.py', 'zipbin.py', 'eff.py',
        'effimg.py', 'dimg.py', 'headtool.py', 'effboxes.py', 'zipbinnames.py']
PAT = re.compile(r"['\"][A-Za-z]:[\\/]")

for m in MODS:
    try:
        s = io.open(m, encoding='utf-8').read()
    except FileNotFoundError:
        continue
    bad = [(i, ln.strip()[:100]) for i, ln in enumerate(s.splitlines(), 1)
           if PAT.search(ln) and 'FFO_DATA' not in ln]
    print('%-16s %d' % (m, len(bad)))
    for i, ln in bad[:5]:
        print('    %4d  %s' % (i, ln))
