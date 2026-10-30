"""6.0 objects*.pkg reader — same XOR + compress as official foplayer.

Format (little-endian), matching WeGame objects*.pkg:

    16-byte header: u32 version / u32 count / u32 index_offset / u32 index_length
    trailing index, uncompressed, each entry:
        u16 name_len
        char[name_len] GBK path (backslash)
        u32 flags   bit0=compressed; bit7=0x80 XOR the stored head first
        u32 offset
        u32 raw_size
        u32 compressed_size

Version branches (foplayer 0x54A06F):
    100 zlib
    101 LZMA (skip 5 bytes)
    102 XOR then zlib
    103 XOR then ZSTD   ← 6.0 objects0–4
    104 XOR then LZ4    ← 6.0 objects5–6

XOR: foplayer 0x549A4E / seeds 0x54994C, const 0x7E197612.

zipbin lives in objects4.pkg (227 tables). This module does not launch qqffo.exe.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import time
import zlib
from collections import Counter
from datetime import datetime
from pathlib import Path

# from inspect60_files import CLIENT, OUTPUT
CLIENT = Path(r'F:\WG自由幻想\自由幻想\data')
OUTPUT = Path(r'F:\WG自由幻想\自由幻想\data\data')

PKGS = tuple(f'objects{i}.pkg' for i in range(7))
ZIPBIN_PKG = 'objects4.pkg'
MASK32 = 0xFFFFFFFF
TABLE_MAGIC = 0x5566
QQF_MAGIC = b'QQF\x1a'


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


class OfficialPkg:
    def __init__(self, path: Path):
        self.path = path
        with path.open('rb') as fh:
            head = fh.read(16)
            self.version, self.count, idx_off, idx_len = struct.unpack('<4I', head)
            fh.seek(idx_off)
            idx = fh.read(idx_len)
        self.entries = []
        pos = 0
        end = len(idx)
        while pos + 2 <= end and len(self.entries) < self.count:
            (nlen,) = struct.unpack_from('<H', idx, pos)
            pos += 2
            name = idx[pos:pos + nlen].decode('gbk', 'replace')
            pos += nlen
            if pos + 16 > end:
                break
            flags, off, raw, comp = struct.unpack_from('<4I', idx, pos)
            pos += 16
            self.entries.append({
                'name': name,
                'key': name.replace('\\', '/').lower(),
                'flags': flags,
                'off': off,
                'raw': raw,
                'comp': comp,
            })

    def read(self, entry) -> bytes:
        with self.path.open('rb') as fh:
            fh.seek(entry['off'])
            blob = fh.read(entry['comp'])
        return self._decode(entry, blob)

    def iter_decoded(self):
        """Sequential decode in file-offset order (one open handle)."""
        with self.path.open('rb') as fh:
            for entry in sorted(self.entries, key=lambda e: e['off']):
                fh.seek(entry['off'])
                yield entry, self._decode(entry, fh.read(entry['comp']))

    def _decode(self, entry, blob: bytes) -> bytes:
        out = pkg_decompress(blob, self.version, entry['flags'], entry['raw'])
        if entry['raw'] and len(out) != entry['raw']:
            raise ValueError(
                f"{entry['name']} decompressed {len(out)} != raw {entry['raw']}")
        return out


def data_dir() -> Path:
    path = CLIENT
    if not path.is_dir():
        raise FileNotFoundError(f'6.0 data directory missing: {path}')
    return path


def zipbin_pkg() -> OfficialPkg:
    path = data_dir() / ZIPBIN_PKG
    if not path.is_file():
        raise FileNotFoundError(f'missing {path}')
    return OfficialPkg(path)


def zipbin_dest() -> Path:
    return OUTPUT / 'resources' / 'zipbin'


def official_dest() -> Path:
    return OUTPUT / 'official'


def catalog_path() -> Path:
    return OUTPUT / 'official_catalog.json'


def index_path() -> Path:
    return OUTPUT / 'official_index.jsonl'


def all_pkgs() -> list[OfficialPkg]:
    root = data_dir()
    pkgs = []
    for name in PKGS:
        path = root / name
        print(path, path.is_file())
        if path.is_file():
            pkgs.append(OfficialPkg(path))
    if not pkgs:
        raise FileNotFoundError(f'no objects*.pkg under {root}')
    return pkgs


def find_entry(want: str):
    want = want.replace('\\', '/').lower()
    if want.startswith('./'):
        want = want[2:]
    for pkg in all_pkgs():
        for entry in pkg.entries:
            if entry['key'] == want or entry['key'].endswith('/' + want):
                return pkg, entry
    return None, None


def classify_head(head: bytes, name: str) -> str:
    if head.startswith(QQF_MAGIC):
        kind = head[4:8]
        if kind == b'DIMG':
            return 'qqf-dimg'
        if kind == b'IANI':
            return 'qqf-iani'
        if kind == b'MASK':
            return 'qqf-mask'
        return f'qqf-{kind.decode("latin1", "replace").strip()}'
    if len(head) >= 4 and struct.unpack_from('<I', head)[0] == TABLE_MAGIC:
        return 'zipbin-table'
    if head.startswith(b'RIFF'):
        return 'wav'
    if head.startswith(b'OggS'):
        return 'ogg'
    if head.startswith(b'\xff\xd8'):
        return 'jpeg'
    if head.startswith(b'\x89PNG'):
        return 'png'
    if head.startswith(b'BM'):
        return 'bmp'
    if head.startswith(b'GIF8'):
        return 'gif'
    if head.startswith((b'<?xml', b'<', b'\xef\xbb\xbf<?xml')):
        return 'xml'
    if head.startswith(b'{') or head.startswith(b'['):
        return 'json'
    ext = Path(name).suffix.lower().lstrip('.')
    return ext or 'bin'


def _safe_rel(name: str) -> Path:
    rel = Path(name.replace('\\', '/'))
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError(f'refusing path {name}')
    return rel


def build_catalog(pkgs: list[OfficialPkg] | None = None) -> dict:
    pkgs = pkgs or all_pkgs()
    tops: Counter[str] = Counter()
    exts: Counter[str] = Counter()
    pkg_rows = []
    index_lines = []
    raw_total = 0
    comp_total = 0
    for pkg in pkgs:
        pkg_tops: Counter[str] = Counter()
        pkg_exts: Counter[str] = Counter()
        pkg_raw = pkg_comp = 0
        for entry in pkg.entries:
            top = entry['key'].split('/', 1)[0]
            ext = Path(entry['key']).suffix.lower() or '(none)'
            tops[top] += 1
            exts[ext] += 1
            pkg_tops[top] += 1
            pkg_exts[ext] += 1
            pkg_raw += entry['raw']
            pkg_comp += entry['comp']
            index_lines.append({
                'pkg': pkg.path.name,
                'name': entry['name'],
                'key': entry['key'],
                'raw': entry['raw'],
                'comp': entry['comp'],
                'flags': entry['flags'],
                'off': entry['off'],
            })
        raw_total += pkg_raw
        comp_total += pkg_comp
        pkg_rows.append({
            'name': pkg.path.name,
            'version': pkg.version,
            'count': len(pkg.entries),
            'raw_bytes': pkg_raw,
            'comp_bytes': pkg_comp,
            'tops': dict(pkg_tops.most_common()),
            'exts': dict(pkg_exts.most_common()),
        })
    catalog = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'client': str(CLIENT),
        'pkg_count': len(pkgs),
        'entry_count': sum(p['count'] for p in pkg_rows),
        'raw_bytes': raw_total,
        'comp_bytes': comp_total,
        'tops': dict(tops.most_common()),
        'exts': dict(exts.most_common()),
        'pkgs': pkg_rows,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    catalog_path().write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    with index_path().open('w', encoding='utf-8') as fh:
        for row in index_lines:
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    catalog['index_path'] = str(index_path())
    catalog['catalog_path'] = str(catalog_path())
    return catalog


def extract_all(*, overwrite: bool = False, dest: Path | None = None,
                kinds_limit: int = 8) -> dict:
    """Unpack every objects*.pkg entry into data/client60/official/."""
    target = dest or official_dest()
    target.mkdir(parents=True, exist_ok=True)
    pkgs = all_pkgs()
    written = skipped = mismatched = errors = 0
    kinds: dict[str, list[str]] = {}
    started = time.time()
    total = sum(len(pkg.entries) for pkg in pkgs)
    done = 0
    for pkg in pkgs:
        with pkg.path.open('rb') as fh:
            for entry in sorted(pkg.entries, key=lambda e: e['off']):
                done += 1
                try:
                    fh.seek(entry['off'])
                    blob = pkg._decode(entry, fh.read(entry['comp']))
                except Exception as exc:
                    errors += 1
                    print(f'FAIL {pkg.path.name} {entry["name"]}: {exc}', flush=True)
                    continue
                rel = _safe_rel(entry['name'])
                out = target / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                kind = classify_head(blob[:16], entry['name'])
                bucket = kinds.setdefault(kind, [])
                if len(bucket) < kinds_limit:
                    bucket.append(entry['key'])
                if out.is_file() and out.stat().st_size == len(blob) and not overwrite:
                    skipped += 1
                else:
                    if out.is_file() and out.stat().st_size != len(blob):
                        mismatched += 1
                    out.write_bytes(blob)
                    written += 1
                if done % 500 == 0 or done == total:
                    elapsed = max(0.001, time.time() - started)
                    print(
                        f'  {pkg.path.name} {done}/{total} '
                        f'写出={written} 跳过={skipped} 失败={errors} {elapsed:.0f}s',
                        flush=True)
    summary = {
        'dest': str(target),
        'total': total,
        'written': written,
        'skipped': skipped,
        'mismatched': mismatched,
        'errors': errors,
        'seconds': round(time.time() - started, 1),
        'kinds': {k: v for k, v in sorted(kinds.items())},
    }
    (OUTPUT / 'official_extract.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


def classify_extracted(root: Path | None = None) -> dict:
    root = root or official_dest()
    kinds: Counter[str] = Counter()
    samples: dict[str, str] = {}
    files = 0
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        files += 1
        head = path.read_bytes()[:16]
        kind = classify_head(head, path.name)
        kinds[kind] += 1
        samples.setdefault(kind, str(path.relative_to(root)).replace('\\', '/'))
    report = {
        'root': str(root),
        'files': files,
        'kinds': dict(kinds.most_common()),
        'samples': samples,
    }
    (OUTPUT / 'official_kinds.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def table_header(blob: bytes) -> tuple[int, int, int, int]:
    if len(blob) < 16:
        raise ValueError('table shorter than 16-byte header')
    return struct.unpack_from('<4I', blob)


def extract_zipbin(*, overwrite: bool = False, dest: Path | None = None) -> dict:
    """Unpack objects4.pkg zipbin tables into data/client60/resources/zipbin."""
    pkg = zipbin_pkg()
    if pkg.version != 103:
        raise ValueError(f'{ZIPBIN_PKG} version {pkg.version}, expected 103')
    target = dest or zipbin_dest()
    target.mkdir(parents=True, exist_ok=True)
    written, skipped, mismatched = [], [], []
    for entry in pkg.entries:
        name = Path(entry['name'].replace('\\', '/')).name
        out = target / name
        blob = pkg.read(entry)
        digest = hashlib.sha256(blob).hexdigest()
        if out.is_file():
            existing = hashlib.sha256(out.read_bytes()).hexdigest()
            if existing == digest:
                skipped.append(name)
                continue
            mismatched.append(name)
            if not overwrite:
                continue
        out.write_bytes(blob)
        written.append(name)
    return {
        'pkg': str(pkg.path),
        'version': pkg.version,
        'count': len(pkg.entries),
        'dest': str(target),
        'written': written,
        'skipped': skipped,
        'mismatched': mismatched,
    }


def cmd_list(sub: str = '') -> int:
    sub = sub.replace('\\', '/').lower()
    total = 0
    for pkg in all_pkgs():
        for entry in pkg.entries:
            if sub and sub not in entry['key']:
                continue
            print(
                f"{pkg.path.name:14s} {entry['name']:50s} "
                f"原始={entry['raw']:8d} 压缩={entry['comp']:8d} "
                f"标志={entry['flags']:08x}")
            total += 1
    print(f'共 {total} 条')
    return 0


def cmd_dirs(prefix: str = '') -> int:
    prefix = prefix.replace('\\', '/').lower().strip('/')
    prefix = (prefix + '/') if prefix else ''
    kids: Counter[str] = Counter()
    for pkg in all_pkgs():
        for entry in pkg.entries:
            if prefix and not entry['key'].startswith(prefix):
                continue
            rest = entry['key'][len(prefix):]
            kids[rest.split('/', 1)[0]] += 1
    if not kids:
        print(f'{prefix or "(根)"} 下没有条目')
        return 1
    print(f'{prefix or "(根)"} 下 {len(kids)} 个直接子项:')
    for name, count in kids.most_common():
        print(f'  {count:6d}  {name}')
    return 0


def cmd_catalog() -> int:
    catalog = build_catalog()
    print(f"条目 {catalog['entry_count']}  原始 {catalog['raw_bytes']/1024/1024:.1f} MB  "
          f"压缩 {catalog['comp_bytes']/1024/1024:.1f} MB")
    print(f"索引 -> {catalog['catalog_path']}")
    print(f"清单 -> {catalog['index_path']}")
    print('顶层:')
    for name, count in list(catalog['tops'].items())[:20]:
        print(f'  {count:6d}  {name}')
    print('后缀:')
    for name, count in list(catalog['exts'].items())[:20]:
        print(f'  {count:6d}  {name}')
    for row in catalog['pkgs']:
        print(f"{row['name']} v{row['version']} {row['count']} 条 "
              f"原始 {row['raw_bytes']/1024/1024:.1f} MB")
    return 0


def cmd_extract_all(*args: str) -> int:
    overwrite = '--force' in args
    print('开始整包解出 objects0-6 …')
    info = extract_all(overwrite=overwrite)
    print(f"写出 {info['written']}  跳过 {info['skipped']}  "
          f"尺寸不同 {info['mismatched']}  {info['seconds']}s")
    print(f"目录 {info['dest']}")
    print('类型样本:')
    for kind, samples in info['kinds'].items():
        print(f'  {kind}: {samples[0]}')
    kinds = classify_extracted()
    print(f"落地 {kinds['files']} 个文件 -> {OUTPUT / 'official_kinds.json'}")
    return 0


def cmd_extract(*args: str) -> int:
    overwrite = '--force' in args
    info = extract_zipbin(overwrite=overwrite)
    print(f"{info['pkg']} 版本={info['version']} 条目={info['count']}")
    print(f"写出 {len(info['written'])}  已相同 {len(info['skipped'])}  "
          f"哈希不同 {len(info['mismatched'])}  -> {info['dest']}")
    if info['written'][:20]:
        print('新解出:', ', '.join(info['written'][:20])
              + (' …' if len(info['written']) > 20 else ''))
    if info['mismatched'] and not overwrite:
        print('未覆盖:', ', '.join(info['mismatched'][:20]))
        print('要覆盖请加 --force')
        return 1
    return 0


def cmd_dump(name: str) -> int:
    pkg, entry = find_entry(name)
    if entry is None and '/' not in name.replace('\\', '/'):
        pkg, entry = find_entry('zipbin/' + name)
    if entry is None:
        print(f'{name} 没找到')
        return 1
    blob = pkg.read(entry)
    print(f"{entry['name']} <- {pkg.path.name} {len(blob)} 字节")
    print(f'  类型 {classify_head(blob[:16], entry["name"])}')
    print(f'  头: {blob[:16].hex(" ")}')
    if len(blob) >= 16:
        magic, version, width, count = table_header(blob)
        if magic == TABLE_MAGIC:
            print(f'  magic=0x{magic:x} version={version} width={width} count={count}')
            if 16 + width * count == len(blob) and width and count:
                shown = 0
                for i in range(count):
                    row = blob[16 + i * width:16 + (i + 1) * width]
                    if not any(row):
                        continue
                    print(f'  [{i}] {list(row[:min(32, width)])}')
                    shown += 1
                    if shown >= 16:
                        break
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ('-h', '--help'):
        print('python official_pkg60.py catalog')
        print('python official_pkg60.py dirs [前缀]')
        print('python official_pkg60.py list [子串]')
        print('python official_pkg60.py extract [--force]')
        print('python official_pkg60.py extract-all [--force]')
        print('python official_pkg60.py dump <路径>')
        return 0
    cmd = args[0]
    if cmd == 'catalog':
        return cmd_catalog()
    if cmd == 'dirs':
        return cmd_dirs(args[1] if len(args) > 1 else '')
    if cmd == 'list':
        return cmd_list(args[1] if len(args) > 1 else '')
    if cmd == 'extract':
        return cmd_extract(*args[1:])
    if cmd == 'extract-all':
        return cmd_extract_all(*args[1:])
    if cmd == 'dump' and len(args) > 1:
        return cmd_dump(args[1])
    print('未知命令', cmd)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
