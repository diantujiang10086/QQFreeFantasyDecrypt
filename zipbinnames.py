"""Recover column names for zipbin tables from the private-server source.

The server decodes a fixed-width row with any of these idioms:

    item_id  = struct.unpack_from('<I', row)[0]
    delay, group = struct.unpack_from('<II', cool, 4)
    name     = row[4:68].split(b'\0', 1)[0].decode('gbk')
    flag     = int.from_bytes(row[12:14], 'little')
    level    = row[16]

`fieldmap()` turns those into an ordered column list per table; `dump_table()` writes a
typed CSV using those names (unknown spans keep an `@offset` name instead of `u12`).
"""
import collections
import os
import re
import struct

import zipbin

SRV = r'D:\ffo\FFO7.3\packages\自由幻想10.09\服务器\server'
HERE = os.path.dirname(os.path.abspath(__file__))

CALL = re.compile(r"table\(\s*['\"]([\w.]+\.bin)['\"]\s*,\s*(\d+)\s*\)", re.I)
UNPACK_ASSIGN = re.compile(
    r"([A-Za-z_][\w\s,\[\]\.\(\)]*?)\s*=\s*struct\.unpack(?:_from)?\(\s*['\"]([<>!=@]?[A-Za-z0-9]+)['\"]"
    r"\s*,\s*(?:row|cool|r|data|line|rec|raw)\s*(?:,\s*(\d+)\s*)?\)")
BYTES_ASSIGN = re.compile(
    r"([A-Za-z_][\w\s,\[\]\.\(\)]*?)\s*=\s*int\.from_bytes\(\s*(?:row|r|cool|rec)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]"
    r"\s*,\s*['\"](\w+)['\"]\s*(?:,\s*signed\s*=\s*(True|False)\s*)?\)")
SLICE_ASSIGN = re.compile(
    r"([A-Za-z_][\w\.]*)\s*=\s*(?:row|r|cool|rec)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]")
BYTE_ASSIGN = re.compile(r"([A-Za-z_][\w\.]*)\s*=\s*(?:row|r|cool|rec)\s*\[\s*(\d+)\s*\]")

SIZE = {'b': 1, 'B': 1, '?': 1, 'h': 2, 'H': 2, 'i': 4, 'I': 4, 'l': 4, 'L': 4,
        'q': 8, 'Q': 8, 'f': 4, 'd': 8}
FMT = re.compile(r'(\d*)([sbc?hHiIlLqQfd])')


def _printable(b):
    """True when the bytes look like GBK/ASCII text rather than binary."""
    if not b:
        return False
    ok = sum(1 for x in b if 32 <= x < 127 or x >= 0x81)
    return ok >= 0.9 * len(b)


def fmt_segments(fmt):
    """'<II' -> [(4,'I')], '<9I' -> nine 4-byte ints, '<16s' -> one 16-byte string."""
    out = []
    for count, ch in FMT.findall(fmt.lstrip('<>!=@')):
        n = int(count) if count else 1
        if ch == 's':
            out.append((n, 's'))
        else:
            for _ in range(n):
                out.append((SIZE[ch], 'i'))
    return out


def _clean_names(text):
    names = [n.strip().lstrip('(').strip() for n in text.split(',')]
    names = [n for n in names if re.fullmatch(r'[A-Za-z_]\w*', n or '')]
    return names


_SRC_CACHE = None


def _sources():
    """{文件名: 源码文本}，只读一次（225 张表 × 500 文件太慢）。"""
    global _SRC_CACHE
    if _SRC_CACHE is None:
        cache = {}
        for f in sorted(os.listdir(SRV)):
            if not f.endswith('.py'):
                continue
            try:
                cache[f] = open(os.path.join(SRV, f), 'rb').read().decode('utf-8', 'ignore')
            except OSError:
                pass
        _SRC_CACHE = cache
    return _SRC_CACHE


def scan_table(name):
    """Collect (offset, size, kind, name, file) candidates for one table."""
    cand = []
    for f, s in _sources().items():
        for m in re.finditer(r"table\(\s*['\"]%s['\"]\s*,\s*(\d+)\s*\)" % re.escape(name), s, re.I):
            win = s[m.end():m.end() + 6000]
            for a in UNPACK_ASSIGN.finditer(win):
                names = _clean_names(a.group(1))
                segs = fmt_segments(a.group(2))
                if not names:
                    continue
                off = int(a.group(3) or 0)
                if len(names) == len(segs):
                    for (sz, kind), nm in zip(segs, names):
                        cand.append((off, sz, kind, nm, f))
                        off += sz
                elif len(names) == 1:
                    total = sum(sz for sz, _ in segs)
                    kind = segs[0][1] if len(segs) == 1 else 'i'
                    cand.append((off, total, kind, names[0], f))
            for b in BYTES_ASSIGN.finditer(win):
                names = _clean_names(b.group(1))
                if not names:
                    continue
                a0, a1 = int(b.group(2)), int(b.group(3))
                signed = (b.group(5) == 'True') or b.group(4) == 'little' and False
                cand.append((a0, a1 - a0, 'si' if signed else 'i', names[0], f))
            for sl in SLICE_ASSIGN.finditer(win):
                nm = sl.group(1)
                if nm in ('row', 'r', 'cool', 'rec'):
                    continue
                a0, a1 = int(sl.group(2)), int(sl.group(3))
                cand.append((a0, a1 - a0, 's', nm, f))
            for by in BYTE_ASSIGN.finditer(win):
                nm = by.group(1)
                if nm in ('row', 'r', 'cool', 'rec'):
                    continue
                cand.append((int(by.group(2)), 1, 'i', nm, f))
    return cand


def fieldmap(widths=None):
    """-> {table: [(offset, size, kind, name)]} with conflicts resolved by vote.

    widths: 可选 {名字: 行宽}；不给就扫磁盘 zipbin 目录（磁盘被清空时请传入）。
    """
    tables = {}
    if widths is None:
        widths = {}
        for name in sorted(os.listdir(zipbin.CLIENT)):
            if not name.lower().endswith('.bin'):
                continue
            try:
                widths[name] = zipbin.read(os.path.join(zipbin.CLIENT, name))['width']
            except Exception:                   # noqa: BLE001
                continue
    for name in sorted(widths):
        w = widths[name]
        if not name.lower().endswith('.bin'):
            continue
        cand = scan_table(name)
        if not cand:
            tables[name.lower()] = []
            continue
        votes = collections.defaultdict(collections.Counter)
        for off, sz, kind, nm, _f in cand:
            votes[(off, sz, kind)][nm] += 1
        fields = []
        used_until = 0
        for (off, sz, kind), names in sorted(votes.items()):
            if off + sz > w:
                continue
            nm = names.most_common(1)[0][0]
            fields.append((off, sz, kind, nm))
        # resolve overlaps: keep the field with more votes / larger size first
        fields.sort(key=lambda t: (t[0], -t[1]))
        clean = []
        for f in fields:
            if clean and f[0] < clean[-1][0] + clean[-1][1]:
                continue
            clean.append(f)
        tables[name.lower()] = clean
    return tables


def dump_table(path, out_csv, fields):
    r = zipbin.read(path)
    w = r['width']
    rows = r['rows']
    cols = []                                   # (name, offset, size, kind)
    cur = 0
    for off, sz, kind, nm in fields:
        if off > cur:
            cols.extend(_unknown_cols(rows, cur, off))
        cols.append((nm, off, sz, kind))
        cur = off + sz
    if cur < w:
        cols.extend(_unknown_cols(rows, cur, w))
    # disambiguate repeated names (e.g. `strength` at two offsets)
    seen = collections.Counter()
    final = []
    for nm, off, sz, kind in cols:
        seen[nm] += 1
        final.append((nm if seen[nm] == 1 else '%s@%d' % (nm, off), off, sz, kind))
    cols = final
    with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
        fh.write(','.join(['row'] + [c[0] for c in cols]) + '\n')
        for i, row in enumerate(rows):
            vals = []
            for _nm, off, sz, kind in cols:
                chunk = row[off:off + sz]
                if kind == 's':
                    txt = chunk.split(b'\0', 1)[0].decode('gbk', 'replace')
                    vals.append('"' + txt.replace('"', '""') + '"' if txt else '')
                elif kind == 'si':
                    vals.append(str(int.from_bytes(chunk, 'little', signed=True)))
                elif kind == 'i' and sz in (1, 2, 4, 8):
                    vals.append(str(int.from_bytes(chunk, 'little')))
                else:
                    vals.append(chunk.hex())
            fh.write('%d,%s\n' % (i, ','.join(vals)))
    return len(cols), len(rows)


def _unknown_cols(rows, start, end):
    """Split an un-named span into columns so nothing shows up as a giant blob."""
    span = end - start
    sample = rows[:400]
    if span <= 8:
        return [('x@%d' % start, start, span, 'x')]
    out = []
    off = start
    while off < end:
        sz = 4 if end - off >= 4 else end - off
        chunks = [r[off:off + sz] for r in sample]
        texts = [c.split(b'\0', 1)[0] for c in chunks]
        if sz == 4 and off == 0 and _looks_like_id(rows):
            out.append(('id', 0, 4, 'i'))
        elif sz >= 4 and sum(1 for t in texts if t and _printable(t)) >= 0.8 * max(1, len(texts)):
            out.append(('s@%d' % off, off, sz, 'x'))
        elif sz == 4 and all(c == b'\0' * 4 for c in chunks):
            out.append(('z@%d' % off, off, 4, 'x'))
        else:
            out.append(('w@%d' % off, off, sz, 'i' if sz in (1, 2, 4) else 'x'))
        off += sz
    return out


def _looks_like_id(rows):
    """First 4 bytes: unique, strictly increasing, small -> almost certainly a row id."""
    vals = [int.from_bytes(r[0:4], 'little') for r in rows]
    if not vals or len(set(vals)) < 0.95 * len(vals):
        return False
    if vals != sorted(vals):
        return False
    return vals[0] < 1_000_000 and vals[-1] < 5_000_000


def main():
    fm = fieldmap()
    named = {k: v for k, v in fm.items() if v}
    print('tables with recovered columns: %d / %d' % (len(named), len(fm)))
    print('columns total: %d' % sum(len(v) for v in fm.values()))
    for k in sorted(named, key=lambda t: -len(named[t]))[:12]:
        print('  %-28s %2d cols  %s' % (k, len(named[k]),
                                        ' '.join('%s@%d' % (f[3], f[0]) for f in named[k][:8])))
    outdir = os.path.join(HERE, 'out', 'zipbin_csv')
    os.makedirs(outdir, exist_ok=True)
    tot = 0
    for name in sorted(os.listdir(zipbin.CLIENT)):
        if not name.lower().endswith('.bin'):
            continue
        p = os.path.join(zipbin.CLIENT, name)
        try:
            zipbin.read(p)
        except Exception:                       # noqa: BLE001
            continue
        base = os.path.splitext(name)[0] + '.csv'
        ncol, nrow = dump_table(p, os.path.join(outdir, base), fm.get(name.lower(), []))
        tot += ncol
    import csv as _csv
    with open(os.path.join(HERE, 'out', 'zipbin_fields.csv'), 'w', newline='', encoding='utf-8') as fh:
        wr = _csv.writer(fh)
        wr.writerow(['table', 'offset', 'size', 'kind', 'field'])
        for tbl, fields in sorted(fm.items()):
            for off, sz, kind, nm in fields:
                wr.writerow([tbl, off, sz, kind, nm])
    print('csv total columns %d -> %s' % (tot, outdir))


if __name__ == '__main__':
    main()
