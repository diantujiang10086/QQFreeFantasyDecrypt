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
import os
import struct
import zlib
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
# 只允许读「游戏资源目录」这一处外部路径；可用环境变量 FFO_DATA 或 viewer2 --data 覆盖。
PKG_ROOT = os.environ.get('FFO_DATA', '')   # 由 --data / FFO_DATA / data\\ffo_data.txt 提供
if not PKG_ROOT:                     # 未设置环境变量时，回落到本地配置（data/ffo_data.txt）
    try:
        import paths
        PKG_ROOT = paths.DATA
    except Exception:
        PKG_ROOT = ''

MASK32 = 0xFFFFFFFF


def set_root(path):
    """切换资源根（pkg 缓存随之清空）。"""
    global PKG_ROOT
    path = os.path.abspath(path)
    if path != PKG_ROOT:
        PKG_ROOT = path
        _cache.clear()
    return PKG_ROOT


def _u32(x: int) -> int:
    return x & MASK32


def _imul(a: int, b: int) -> int:
    return (a * b) & MASK32


def pkg_seeds(flags_hi12: int, nibble: int, raw: int, comp: int) -> tuple[int, int]:
    """foplayer 0x54994C → (seed1, seed2)."""
    rot_n = (nibble + 1) & 0x1F
    const = 0x7E197612
    if rot_n == 0:
        rot = const
    else:
        rot = _u32((const >> (32 - rot_n)) | (const << rot_n))
    edx = _imul(nibble, 0x415D42A)
    saved = rot ^ 0xE3C0CFE1
    edi = _u32(0xFDF515EB - edx)
    a2 = raw
    ecx = _imul(a2, 0x27D4EB2F)
    edx = _u32((a2 >> 19) | (a2 << 13))
    eax = _imul(flags_hi12, 0x85EBCA6B)
    eax ^= edx
    eax ^= saved
    eax = _u32(eax - _imul(comp, 0x3D4D51CB))
    edi ^= 0xD4966A5C
    eax ^= 0xFDF515EB
    edx = _u32((eax >> 16) ^ eax)
    edx = _imul(edx, 0x85EBCA6B)
    eax = _u32((edx >> 13) ^ edx)
    eax = _imul(eax, 0xC2B2AE35)
    seed1 = _u32((eax >> 16) ^ eax)
    eax = flags_hi12 ^ comp
    ebx = _u32((eax >> 15) | (eax << 17))
    ecx ^= ebx
    rot7 = _u32((flags_hi12 >> 25) | ((flags_hi12 << 7) & MASK32))
    ecx ^= edi
    eax = _u32(rot7 + ecx) ^ 0x7E197612
    ecx = _u32((eax >> 16) ^ eax)
    ecx = _imul(ecx, 0x85EBCA6B)
    eax = _u32((ecx >> 13) ^ ecx)
    eax = _imul(eax, 0xC2B2AE35)
    seed2 = _u32((eax >> 16) ^ eax)
    if seed1 == 0:
        seed1 = 0xE3C0CFE1
    if seed2 == 0:
        seed2 = 0xD4966A5D
    return seed1, seed2


def pkg_xor_inplace(buf: bytearray, flags: int, raw: int, comp: int) -> int:
    """foplayer 0x549A4E. Only the first xor_len bytes are touched."""
    flags_hi12 = flags >> 12
    xor_len = (flags_hi12 & 0x7F) + 0x80
    nibble = (flags >> 8) & 0xF
    if xor_len > comp:
        xor_len = comp
    edi, edx = pkg_seeds(flags_hi12, nibble, raw, comp)
    i = 0
    while i < xor_len:
        edi ^= _u32(edi << 13)
        edi ^= edi >> 17
        edi ^= _u32(edi << 5)
        edx ^= _u32(edx << 5)
        edx ^= edx >> 3
        edx ^= _u32(edx << 21)
        bitpos = 0
        while i < xor_len:
            mix = _u32(edi + edx)
            buf[i] ^= (mix >> bitpos) & 0xFF
            i += 1
            bitpos += 8
            if bitpos >= 0x20:
                break
    return xor_len


def pkg_decompress(stored: bytes, version: int, flags: int, raw: int) -> bytes:
    """foplayer 0x54A06F version switch."""
    buf = bytearray(stored)
    comp = len(stored)
    if version in (102, 103, 104) and (flags & 0x80):
        pkg_xor_inplace(buf, flags, raw, comp)
    if version in (100, 102):
        return zlib.decompress(bytes(buf))
    if version == 101:
        import lzma
        return lzma.decompress(bytes(buf[5:]))
    if version == 103:
        import zstandard as zstd
        return zstd.ZstdDecompressor().decompress(bytes(buf), max_output_size=raw)
    if version == 104:
        import lz4.block
        out = lz4.block.decompress(bytes(buf), uncompressed_size=raw)
        if len(out) != raw:
            raise ValueError(f'lz4 size {len(out)} != raw {raw}')
        return out
    raise ValueError(f'unsupported official pkg version {version}')

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
        out = pkg_decompress(blob, self.version, f, raw)
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


def all_pkgs(root=None):
    root = root or PKG_ROOT
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
