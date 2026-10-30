"""读取游戏的 `.pkg` 容器（索引紧凑版，内存占用小）。

一个 `.pkg` 由三部分组成：

    16 字节头  u32 version / u32 count / u32 index_offset / u32 index_length
    数据区     每条：flags bit0=压缩、bit7=先 XOR；version 100 zlib / 101 lzma
               / 102 xor+zlib / 103 xor+zstd / 104 xor+lz4
    索引区     u16 name_len + GBK 路径 + u32 flags + u32 offset + u32 raw + u32 comp

索引只保留「名字列表 + 定长元数据数组（array('I')） + 每条元数据在索引里的偏移」，
不再为 9 万多条目各建一个 dict —— 打开 17 个包从 ~150MB 降到 ~20MB。

    python pkg.py                 # 列出所有包与条目数
    python pkg.py avatar/head/head0101.gsn    # dump 一个条目
"""
import importlib.util
import os
import struct
from array import array
import paths

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_ROOT = paths.DATA

# 底层的 XOR / zstd / lz4 逻辑复用私服工程的原始实现
_spec = importlib.util.spec_from_file_location(
    '_official_pkg60', os.path.join(HERE, '_official_pkg60.py'))
_ref = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ref)
decompress = _ref.pkg_decompress


class Pkg:
    """一个 .pkg 包。"""

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
    def name_at(self, j):
        return self.names[j]

    def key_at(self, j):
        return self.names[j].replace('\\', '/').lower()

    def raw_at(self, j):
        return self.meta[4 * j + 2]

    def entry_at(self, j):
        f, off, raw, comp = self.meta[4 * j:4 * j + 4]
        return {'name': self.names[j], 'key': self.key_at(j), 'flags': f,
                'off': off, 'raw': raw, 'comp': comp}

    @property
    def by_key(self):
        """key -> 序号（懒建，只在按名字查找时才需要）。"""
        if self._by_key is None:
            self._by_key = {self.key_at(j): j for j in range(self.count)}
        return self._by_key

    def find_index(self, name):
        key = name.replace('\\', '/').lower().lstrip('/')
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


_cache = {}


def all_pkgs(root=PKG_ROOT):
    out = []
    for i in range(7):
        p = os.path.join(root, 'objects%d.pkg' % i)
        if os.path.isfile(p):
            out.append(p)
    if os.path.isdir(root):
        for n in sorted(os.listdir(root)):
            if n.lower().endswith('.pkg') and not n.lower().startswith('objects'):
                p = os.path.join(root, n)
                if os.path.isfile(p):
                    out.append(p)
    return out


def pkg(path):
    if path not in _cache:
        _cache[path] = Pkg(path)
    return _cache[path]


def find(name, root=PKG_ROOT):
    """返回 (pkg_path, 条目序号) 或 (None, None)。"""
    for p in all_pkgs(root):
        try:
            k = pkg(p)
        except Exception:        # noqa: BLE001
            continue
        j = k.find_index(name)
        if j is not None:
            return p, j
    return None, None


def read(name, root=PKG_ROOT):
    p, j = find(name, root)
    if p is None:
        raise KeyError(name)
    return pkg(p).read_at(j)


def catalog(root=PKG_ROOT):
    """[(pkg_path, pkg_version, Pkg, err)]"""
    out = []
    for p in all_pkgs(root):
        try:
            k = pkg(p)
        except Exception as e:   # noqa: BLE001
            out.append((p, -1, None, str(e)))
            continue
        out.append((p, k.version, k, ''))
    return out


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        data = read(sys.argv[1])
        print('%s: %d bytes, head %s' % (sys.argv[1], len(data), data[:16].hex(' ')))
    else:
        tot = 0
        for p, ver, k, err in catalog():
            n = len(k.names) if k else 0
            print('%-16s v%-3d entries %5d %s' % (os.path.basename(p), ver, n, err))
            tot += n
        print('total entries', tot)
