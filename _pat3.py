"""把 pkg_hit 改成从 (pkg 序号, 条目序号) 还原 (路径, 条目)。"""
p = 'viewer2.py'
s = open(p, encoding='utf-8').read()
old = ("def pkg_hit(rel):\n"
       "    key = pkg_key(rel)\n"
       "    if key is None:\n"
       "        return None\n"
       "    return pkg_index().get(key)\n")
new = ("def pkg_hit(rel):\n"
       "    key = pkg_key(rel)\n"
       "    if key is None:\n"
       "        return None\n"
       "    hit = pkg_index().get(key)\n"
       "    if not hit:\n"
       "        return None\n"
       "    pi, j = hit\n"
       "    path = _PKG_PATHS[pi]\n"
       "    try:\n"
       "        return (path, pkg.pkg(path).entries[j])\n"
       "    except Exception:            # noqa: BLE001\n"
       "        return None\n")
assert old in s
s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print('pkg_hit patched')

# effimg: LRU 上限
q = 'effimg.py'
e = open(q, encoding='utf-8').read()
e = e.replace('_SPR = {}', '_SPR = {}                 # 有上限的精灵图 LRU（见 _spr_put）\n_SPR_MAX = 120\n_ADD = {}')
if '_spr_put' not in e:
    e = e.replace('def _stem(name):',
                  "def _spr_put(key, val):\n"
                  "    _SPR[key] = val\n"
                  "    while len(_SPR) > _SPR_MAX:\n"
                  "        _SPR.pop(next(iter(_SPR)))\n"
                  "    return val\n\n\n"
                  "def _stem(name):", 1)
    # 写入点
    import re
    m = re.search(r'\n(\s+)_SPR\[key\] = out\n', e)
    if m:
        e = e[:m.start()] + '\n' + m.group(1) + '_spr_put(key, out)\n' + e[m.end():]
        print('sprite cache write patched')
    else:
        print('WARN: sprite cache write point not found')
open(q, 'w', encoding='utf-8').write(e)
print('effimg patched')
