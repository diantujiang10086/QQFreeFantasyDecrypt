"""内存优化补丁：
1) viewer2.pkg_index 只存 (pkg 序号, 条目序号)，不再为每个条目复制 dict；
2) effimg 的 _SPR / _ADD 改成有上限的 LRU，避免精灵图无限累积。
"""
import re

# ---------------------------------------------------------------- viewer2
p = 'viewer2.py'
s = open(p, encoding='utf-8').read()

old_idx = """                idx = {}
                for path, ver, ents, err in pkg.catalog():
                    for e in ents:
                        idx[e['key']] = (path, e)
                _PKG_IDX = idx"""
new_idx = """                idx = {}
                paths = []
                for path, ver, ents, err in pkg.catalog():
                    paths.append(path)
                    pi = len(paths) - 1
                    for j, e in enumerate(ents):
                        idx[e['key']] = (pi, j)
                _PKG_PATHS[:] = paths
                _PKG_IDX = idx"""
assert old_idx in s, 'pkg_index body not found'
s = s.replace(old_idx, new_idx)

# 声明 _PKG_PATHS
s = s.replace('_PKG_IDX = None', '_PKG_IDX = None\n_PKG_PATHS = []', 1)

# pkg_hit 需要把 (pi, j) 还原成 (path, entry)
m = re.search(r'def pkg_hit\(rel\):\n(.*?)\n\n\n', s, re.S)
assert m, 'pkg_hit not found'
body = m.group(0)
print('--- old pkg_hit ---')
print(body)
open(p, 'w', encoding='utf-8').write(s)
print('viewer2 pkg_index patched')
