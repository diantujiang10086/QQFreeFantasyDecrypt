"""objects*.pkg 读取器（按需解码，不落盘）。

格式与算法来自私服工程 `official_pkg60.py` 对 foplayer.exe 的逆向结果：
    16 字节头：u32 version / u32 count / u32 index_offset / u32 index_length
    尾部索引（不压缩），每项：
        u16 name_len / GBK 路径 / u32 flags / u32 offset / u32 raw_size / u32 compressed_size
    flags: bit0 = 压缩；bit7(0x80) = 先做 XOR
    version: 100 zlib / 101 lzma(跳过 5 字节) / 102 xor+zlib / 103 xor+zstd / 104 xor+lz4
"""
from __future__ import annotations

import os
import struct
import zlib

MASK32 = 0xFFFFFFFF
PKG_ROOT = r'F:\WG自由幻想\自由幻想\data'


def _u32(x):
    return x & MASK32


def _imul(a, b):
    return (a * b) & MASK32


def pkg_seeds(flags_hi12, nibble, raw, comp):
    rot_n = (nibble + 1) & 0x1F
    const = 0x7E197612
    rot = const if rot_n == 0 else _u32((const >> (32 - rot_n)) | (const << rot_n))
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


def pkg_xor_inplace(buf, flags, raw, comp):
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


def decompress(stored, version, flags, raw):
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
            raise ValueError('lz4 size %d != raw %d' % (len(out), raw))
        return out
    raise ValueError('unsupported pkg version %d' % version)


class Pkg:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as fh:
            head = fh.read(16)
            self.version, self.count, idx_off, idx_len = struct.unpack('<4I', head)
            fh.seek(idx_off)
            idx = fh.read(idx_len)
        self.entries = []
        pos, end = 0, len(idx)
        while pos + 2 <= end and len(self.entries) < self.count:
            (nlen,) = struct.unpack_from('<H', idx, pos)
            pos += 2
            name = idx[pos:pos + nlen].decode('gbk', 'replace')
            pos += nlen
            if pos + 16 > end:
                break
            flags, off, raw, comp = struct.unpack_from('<4I', idx, pos)
            pos += 16
            self.entries.append({'name': name, 'key': name.replace('\\', '/').lower(),
                                 'flags': flags, 'off': off, 'raw': raw, 'comp': comp})
        self.by_key = {e['key']: e for e in self.entries}

    def read_entry(self, entry):
        with open(self.path, 'rb') as fh:
            fh.seek(entry['off'])
            blob = fh.read(entry['comp'])
        out = decompress(blob, self.version, entry['flags'], entry['raw'])
        if entry['raw'] and len(out) != entry['raw']:
            raise ValueError('%s: %d != raw %d' % (entry['name'], len(out), entry['raw']))
        return out

    def read(self, name):
        key = name.replace('\\', '/').lower().lstrip('/')
        e = self.by_key.get(key)
        if e is None:
            for k, v in self.by_key.items():
                if k.endswith('/' + key):
                    e = v
                    break
        if e is None:
            raise KeyError(name)
        return self.read_entry(e)

    def names(self):
        return [e['key'] for e in self.entries]


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
    """返回 (pkg_path, entry) 或 (None, None)。"""
    key = name.replace('\\', '/').lower().lstrip('/')
    for p in all_pkgs(root):
        try:
            k = pkg(p)
        except Exception:
            continue
        e = k.by_key.get(key)
        if e is None:
            for kk, v in k.by_key.items():
                if kk.endswith('/' + key):
                    e = v
                    break
        if e is not None:
            return p, e
    return None, None


def read(name, root=PKG_ROOT):
    p, e = find(name, root)
    if p is None:
        raise KeyError(name)
    return pkg(p).read_entry(e)


def catalog(root=PKG_ROOT):
    """[(pkg_path, pkg_version, [entry...])]"""
    out = []
    for p in all_pkgs(root):
        try:
            k = pkg(p)
        except Exception as e:
            out.append((p, -1, [], str(e)))
            continue
        out.append((p, k.version, k.entries, ''))
    return out


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        data = read(sys.argv[1])
        print('%s: %d bytes, head %s' % (sys.argv[1], len(data), data[:16].hex(' ')))
    else:
        tot = 0
        for p, ver, ent, err in catalog():
            print('%-16s v%-3d entries %5d %s' % (os.path.basename(p), ver, len(ent), err))
            tot += len(ent)
        print('total entries', tot)
