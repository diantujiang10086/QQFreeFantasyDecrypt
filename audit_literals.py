# -*- coding: utf-8 -*-
"""统计离线脚本里外部路径字面量的形态（用于批量改成 paths.py）。"""
import glob
import io
import re
from collections import Counter

PAT = re.compile(r"""(?:r|)['"]([A-Za-z]:[\\/][^'"]*)['"]""")
cnt = Counter()
files = {}
for f in sorted(glob.glob('*.py')):
    try:
        s = io.open(f, encoding='utf-8').read()
    except Exception:                       # noqa: BLE001
        continue
    for m in PAT.finditer(s):
        lit = m.group(1)
        if 'FFO_DATA' in m.group(0):
            continue
        cnt[lit] += 1
        files.setdefault(lit, set()).add(f)
for lit, n in cnt.most_common():
    print('%3d  %s   e.g. %s' % (n, lit.encode('unicode_escape').decode()[:90],
                                 sorted(files[lit])[0]))
print('distinct', len(cnt))
