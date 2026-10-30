"""让 pkg.Pkg 的索引变紧凑：名字列表 + array('I') 元数据，不再为每个条目建 dict。

对外 API 变化：
  Pkg.count / Pkg.key_at(j) / Pkg.name_at(j) / Pkg.raw_at(j) / Pkg.read_at(j)
  Pkg.entry_at(j)  —— 兼容旧代码的 dict 视图（按需构造）
  pkg.find(name) -> (path, j)      （以前返回 (path, entry)）
  pkg.read_at(name) / pkg.read(name)
  pkg.catalog() -> [(path, version, Pkg, err)]
"""
import os
import re
import struct
from array import array

p = 'pkg.py'
s = open(p, encoding='utf-8').read()

start = s.index('class Pkg:')
end = s.index('def all_pkgs(')
new_class = '''class Pkg:
    """一个 .pkg 包。索引以「名字列表 + 定长元数据数组」保存，省内存。"""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as fh:
            head = fh.read(16)
            self.version, self.count, idx_off, idx_len = struct.unpack('<4I', head)
            fh.seek(idx_off)
            self.idx = fh.read(idx_len)
        self.names = []            # 原始名字（保留大小写与反斜杠）
        self.meta = array('I')     # 每条 4 个 u32：flags, off, raw, comp
        self.pos = array('I')      # 条目 meta 在 self.idx 中的偏移
        pos, end = 0, len(self.idx)
        while pos + 2 <= end and len(self.names) < self.count:
            (nlen,) = struct.unpack_from('<H', self.idx, pos)
            pos += 2
            if pos + nlen + 16 > end:
                break
            self.names.append(self.idx[pos:pos + nlen].decode('gbk', 'replace'))
            pos += nlen
            self.pos.append(pos)
            self.meta.extend(struct.unpack_from('<4I', self.idx, pos))
            pos += 16
        self.count = len(self.names)
        self._by_key = None

    # ---------------------------------------------------------------- 查询
    def key_at(self, j):
        return self.names[j].replace('\\\\', '/').lower()

    def name_at(self, j):
        return self.names[j]

    def raw_at(self, j):
        return self.meta[4 * j + 2]

    def entry_at(self, j):
        f, off, raw, comp = self.meta[4 * j:4 * j + 4]
        return {'name': self.names[j], 'key': self.key_at(j), 'flags': f,
                'off': off, 'raw': raw, 'comp': comp}

    @property
    def by_key(self):
        """key -> 条目序号（懒建，只在按名字精确查找时才需要）。"""
        if self._by_key is None:
            self._by_key = {self.key_at(j): j for j in range(self.count)}
        return self._by_key

    def find_index(self, name):
        key = name.replace('\\\\', '/').lower().lstrip('/')
        j = self.by_key.get(key)
        if j is not None:
            return j
        for k, v in self.by_key.items():
            if k.endswith('/' + key):
                return v
        return None

    def read_at(self, j):
        f, off, raw, comp = self.meta[4 * j:4 * j + 4]
        with open(self.path, 'rb') as fh:
            fh.seek(off)
            blob = fh.read(comp)
        out = decompress(blob, self.version, f, raw)
        if raw and len(out) != raw:
            raise ValueError('%s: %d != raw %d' % (self.names[j], len(out), raw))
        return out

    # 兼容旧接口
    def read_entry(self, entry):
        if isinstance(entry, int):
            return self.read_at(entry)
        return self.read_at(self.find_index(entry['key']))

    def read(self, name):
        j = self.find_index(name)
        if j is None:
            raise KeyError(name)
        return self.read_at(j)

    def names_list(self):
        return [self.key_at(j) for j in range(self.count)]


'''
s = s[:start] + new_class + s[end:]

# find / read / catalog 适配新 API
old_find = s[s.index('def find('):s.index('def read(')]
new_find = '''def find(name, root=PKG_ROOT):
    """返回 (pkg_path, 条目序号) 或 (None, None)。"""
    for pth in all_pkgs(root):
        try:
            k = pkg(pth)
        except Exception:
            continue
        j = k.find_index(name)
        if j is not None:
            return pth, j
    return None, None


'''
s = s.replace(old_find, new_find)

s = s.replace("""def read(name, root=PKG_ROOT):
    p, e = find(name, root)
    if p is None:
        raise KeyError(name)
    return pkg(p).read_entry(e)""",
              """def read(name, root=PKG_ROOT):
    p, j = find(name, root)
    if p is None:
        raise KeyError(name)
    return pkg(p).read_at(j)""")

s = s.replace("        out.append((p, k.version, k.entries, ''))",
              "        out.append((p, k.version, k, ''))")
s = s.replace('    """[(pkg_path, pkg_version, [entry...])]"""',
              '    """[(pkg_path, pkg_version, Pkg, err)]"""')
s = s.replace("""        for p, ver, ent, err in catalog():
            print('%-16s v%-3d entries %5d %s' % (os.path.basename(p), ver, len(ent), err))
            tot += len(ent)""",
              """        for p, ver, k, err in catalog():
            print('%-16s v%-3d entries %5d %s' % (os.path.basename(p), ver, len(k.names), err))
            tot += len(k.names)""")

open(p, 'w', encoding='utf-8').write(s)
print('pkg.py refactored')

# ---------------------------------------------------------------- viewer2 适配
v = 'viewer2.py'
t = open(v, encoding='utf-8').read()
t = t.replace("""                for path, ver, ents, err in pkg.catalog():
                    paths.append(path)
                    pi = len(paths) - 1
                    for j, e in enumerate(ents):
                        idx[e['key']] = (pi, j)""",
              """                for path, ver, k, err in pkg.catalog():
                    paths.append(path)
                    pi = len(paths) - 1
                    for j in range(k.count):
                        idx[k.key_at(j)] = (pi, j)""")
t = t.replace("        return (path, pkg.pkg(path).entries[j])",
              "        return (path, j)")
t = t.replace("        return pkg.pkg(hit[0]).read_entry(hit[1])",
              "        return pkg.pkg(hit[0]).read_at(hit[1])")
t = t.replace("                d = pkg.pkg(hit[0]).read_entry(hit[1])",
              "                d = pkg.pkg(hit[0]).read_at(hit[1])")
t = t.replace("                    sz = pkg.pkg(_PKG_PATHS[hit[0]]).entries[hit[1]]['raw']",
              "                    sz = pkg.pkg(_PKG_PATHS[hit[0]]).raw_at(hit[1])")
t = t.replace("""            for k, (pp, e) in pkg_index().items():
                if k.startswith('zipbin/') and k.endswith('.bin'):
                    try:
                        d = pkg.pkg(pp).read_entry(e)""",
              """            for k, (pi, j) in pkg_index().items():
                if k.startswith('zipbin/') and k.endswith('.bin'):
                    try:
                        d = pkg.pkg(_PKG_PATHS[pi]).read_at(j)""")
open(v, 'w', encoding='utf-8').write(t)
print('viewer2 adapted')

# ---------------------------------------------------------------- mkfields 适配
m = open('mkfields.py', encoding='utf-8').read()
m = m.replace("""    for path, ver, ents, err in pkg.catalog():
        for e in ents:
            k = e['key']
            if k.startswith('zipbin/') and k.endswith('.bin'):
                try:
                    d = pkg.pkg(path).read_entry(e)""",
              """    for path, ver, k, err in pkg.catalog():
        for j in range(k.count):
            key = k.key_at(j)
            if key.startswith('zipbin/') and key.endswith('.bin'):
                try:
                    d = pkg.pkg(path).read_at(j)""")
m = m.replace("w[os.path.basename(k)] = struct.unpack_from('<I', d, 8)[0]",
              "w[os.path.basename(key)] = struct.unpack_from('<I', d, 8)[0]")
m = m.replace("print('skip', k, ex, file=sys.stderr)", "print('skip', key, ex, file=sys.stderr)")
open('mkfields.py', 'w', encoding='utf-8').write(m)
print('mkfields adapted')
