# -*- coding: utf-8 -*-
"""统计工作区里仍带外部盘符字面量的脚本（区分运行期与离线探针）。"""
import glob
import io
import os
import re

PAT = re.compile(r"['\"][A-Za-z]:[\\/]")
RUNTIME = {'viewer2.py', 'maps.py', 'pkg.py', 'gsa.py', 'tile.py', 'zipbin.py', 'eff.py',
           'effimg.py', 'dimg.py', 'headtool.py', 'effboxes.py', 'zipbinnames.py'}

rt, offline = [], []
for f in sorted(glob.glob('*.py')):
    s = io.open(f, encoding='utf-8', errors='ignore').read()
    n = sum(1 for ln in s.splitlines() if PAT.search(ln))
    if not n:
        continue
    (rt if os.path.basename(f) in RUNTIME else offline).append((f, n))

print('runtime modules with external literals:', len(rt))
for f, n in rt:
    print('   ', f, n)
print('offline/probe scripts with external literals:', len(offline))
for f, n in offline:
    print('   ', f, n)
