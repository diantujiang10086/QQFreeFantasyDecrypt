"""Analyse the official\\tile directory: `.til` terrain patches + `tileimg*.dat` tile atlases.

Formats (verified on all 140 files):

  .til        magic "ELIT" | u32 @4 = 12 | u32 @8 = version (4097/4098/4099) |
              u32 @12 = entry count | optional tables | entries
              each entry = 128x128 RGBA (65,536 B), memory order B,G,R,A
  tileimgNN.dat magic "QQ  TILE" | u32 @8 = 0x10000 | @12/@20 = 64 | @16 = 128 |
              @24 = 1 | @28 = entry count | 64-byte header | entries
              each entry = 64x64 RGBA (16,384 B)

Usage:
    python tile.py census --csv out/tile.csv
    python tile.py png out/tile [--step N]
    python tile.py sheet out/tile_sheet.png [--step N] [--per-page 96] [--cols 12]
    python tile.py show <index> [--entry K] [--save out/x.png]
"""
import argparse
import csv
import glob
import os
import re
import struct

from PIL import Image, ImageDraw

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\tile'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

TIL_ENTRY = 128 * 128 * 4
IMG_ENTRY = 64 * 64 * 4


# ---------------------------------------------------------------- containers
def rgba(d, off, w, h):
    n = w * h
    raw = d[off:off + 4 * n]
    out = bytearray(4 * n)
    out[0::4] = raw[2::4]
    out[1::4] = raw[1::4]
    out[2::4] = raw[0::4]
    out[3::4] = raw[3::4]
    return Image.frombytes('RGBA', (w, h), bytes(out))


def til(path):
    return til_data(open(path, 'rb').read(), path)


def til_data(d, path=''):
    n = struct.unpack_from('<I', d, 12)[0]
    ver = struct.unpack_from('<I', d, 8)[0]
    hdr = len(d) - n * TIL_ENTRY
    return {'path': path, 'n': n, 'ver': ver, 'hdr': hdr, 'size': len(d), 'd': d,
            'entries': [rgba(d, hdr + k * TIL_ENTRY, 128, 128) for k in range(n)]}


def tileimg(path):
    return tileimg_data(open(path, 'rb').read(), path)


def tileimg_data(d, path=''):
    n = struct.unpack_from('<I', d, 28)[0]
    return {'path': path, 'n': n, 'ver': struct.unpack_from('<I', d, 8)[0], 'hdr': 64,
            'size': len(d), 'd': d,
            'entries': [rgba(d, 64 + k * IMG_ENTRY, 64, 64) for k in range(n)]}


# ---------------------------------------------------------------- ini tables
def ini_tile_names():
    """tile.ini is UTF-16LE: lines 'NNNN  name'."""
    p = os.path.join(ROOT, 'tile.ini')
    t = open(p, 'rb').read().decode('utf-16')
    out = {}
    for line in t.splitlines():
        m = re.match(r'\s*(\d{3,4})\s+(\S+)', line)
        if m:
            out[m.group(2)] = int(m.group(1))
    return out


def ini_kv(name):
    p = os.path.join(ROOT, name)
    if not os.path.exists(p):
        return None
    return open(p, 'rb').read().decode('gbk', 'replace')


def til_files():
    return sorted(glob.glob(os.path.join(ROOT, '*.til')))


def img_files():
    return sorted(glob.glob(os.path.join(ROOT, 'tileimg*.dat')))


def ascii_name(s):
    return s.encode('unicode_escape').decode('ascii')


def rows_cache(csv_path=None):
    """file -> {id, entries, hdr, ver, kind} for every container."""
    names = ini_tile_names()
    out = []
    for p in til_files():
        stem = os.path.basename(p)[:-4]
        d = open(p, 'rb').read(16)
        n = struct.unpack_from('<I', d, 12)[0]
        out.append({'kind': 'til', 'file': stem, 'id': names.get(stem, 0),
                    'entries': n, 'ver': struct.unpack_from('<I', d, 8)[0],
                    'hdr': os.path.getsize(p) - n * TIL_ENTRY,
                    'size': os.path.getsize(p), 'w': 128, 'h': 128})
    for p in img_files():
        stem = os.path.basename(p)[:-4]
        d = open(p, 'rb').read(32)
        n = struct.unpack_from('<I', d, 28)[0]
        out.append({'kind': 'img', 'file': stem, 'id': 0,
                    'entries': n, 'ver': struct.unpack_from('<I', d, 8)[0],
                    'hdr': os.path.getsize(p) - n * IMG_ENTRY,
                    'size': os.path.getsize(p), 'w': 64, 'h': 64})
    return out


# ---------------------------------------------------------------- commands
def census(csv_path=None):
    rows = rows_cache()
    tils = [r for r in rows if r['kind'] == 'til']
    imgs = [r for r in rows if r['kind'] == 'img']
    print('til files %d  entries %d  bytes %d'
          % (len(tils), sum(r['entries'] for r in tils), sum(r['size'] for r in tils)))
    print('img files %d  entries %d  bytes %d'
          % (len(imgs), sum(r['entries'] for r in imgs), sum(r['size'] for r in imgs)))
    from collections import Counter
    print('til versions', dict(Counter(r['ver'] for r in tils)))
    print('til header sizes', dict(Counter(r['hdr'] for r in tils)))
    print('til entry counts', dict(sorted(Counter(r['entries'] for r in tils).items())))
    print('img entry counts', {r['file']: r['entries'] for r in imgs})
    named = sum(1 for r in tils if r['id'])
    print('til matched to tile.ini ids: %d / %d' % (named, len(tils)))
    if csv_path:
        os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
        with open(csv_path, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['kind', 'file', 'id', 'entries', 'ver', 'hdr', 'size', 'w', 'h'])
            for r in rows:
                w.writerow([r['kind'], ascii_name(r['file']), r['id'], r['entries'],
                            r['ver'], r['hdr'], r['size'], r['w'], r['h']])
        print('csv ->', csv_path)


def export(outdir, step=1):
    os.makedirs(outdir, exist_ok=True)
    total = 0
    for r in rows_cache():
        if r['kind'] == 'til':
            base = 'til_%04d' % r['id'] if r['id'] else 'til_x_' + ascii_name(r['file']).replace('\\', '')[:40]
        else:
            base = 'img_' + r['file']
        p = os.path.join(ROOT, r['file'] + ('.til' if r['kind'] == 'til' else '.dat'))
        d = open(p, 'rb').read()
        sub = os.path.join(outdir, base)
        os.makedirs(sub, exist_ok=True)
        if r['kind'] == 'til':
            for k in range(r['n'] if 'n' in r else r['entries']):
                rgba(d, r['hdr'] + k * TIL_ENTRY, 128, 128).save(os.path.join(sub, 'e%02d.png' % k))
                total += 1
        else:
            for k in range(r['entries']):
                rgba(d, 64 + k * IMG_ENTRY, 64, 64).save(os.path.join(sub, 'e%04d.png' % k))
                total += 1
        if r['kind'] == 'til':
            print('  %-28s %3d entries -> %s' % (ascii_name(r['file']), r['entries'], base))
    print('png total', total)


def sheet(outpath, step=1, per_page=96, cols=12):
    pics = []
    for r in rows_cache():
        if r['kind'] != 'til':
            continue
        p = os.path.join(ROOT, r['file'] + '.til')
        d = open(p, 'rb').read()
        base = 'til_%04d' % r['id'] if r['id'] else 'x'
        for k in range(0, r['entries'], max(1, step)):
            pics.append((base, k, rgba(d, r['hdr'] + k * TIL_ENTRY, 128, 128)))
            if len(pics) > 6000:
                break
    print('picked', len(pics))
    cw, ch = 96, 112
    pages = (len(pics) + per_page - 1) // per_page
    for page in range(pages):
        chunk = pics[page * per_page:(page + 1) * per_page]
        rows = (len(chunk) + cols - 1) // cols
        sheet_im = Image.new('RGBA', (cols * cw, rows * ch), (28, 30, 36, 255))
        dr = ImageDraw.Draw(sheet_im)
        for i, (base, k, im) in enumerate(chunk):
            sc = min((cw - 6) / im.width, (ch - 20) / im.height)
            t = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
            bg = Image.new('RGBA', t.size, (20, 22, 26, 255))
            bg.alpha_composite(t)
            x = (i % cols) * cw + 3
            y = (i // cols) * ch + 3
            sheet_im.paste(bg, (x, y))
            dr.text((x, y + t.height + 3), '%s/%d' % (base, k), fill=(200, 200, 210, 255))
        out = outpath if page == 0 else outpath[:-4] + '-%d.png' % (page + 1)
        sheet_im.save(out)
        print('  ->', out, sheet_im.size)


def show(index, entry=0, save=None):
    tils = til_files()
    p = tils[index]
    r = til(p)
    print('file #%d  entries %d  ver %d  hdr %d  size %d'
          % (index, r['n'], r['ver'], r['hdr'], r['size']))
    im = r['entries'][entry]
    if save:
        im.save(save)
        print('saved', save)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['census', 'png', 'sheet', 'show'])
    ap.add_argument('path', nargs='?')
    ap.add_argument('--csv')
    ap.add_argument('--step', type=int, default=1)
    ap.add_argument('--per-page', type=int, default=96)
    ap.add_argument('--cols', type=int, default=12)
    a = ap.parse_args()
    if a.cmd == 'census':
        census(a.csv or a.path)
    elif a.cmd == 'png':
        export(a.path or os.path.join(OUT, 'tile'), a.step)
    elif a.cmd == 'sheet':
        sheet(a.path or os.path.join(OUT, 'tile_sheet.png'), a.step, a.per_page, a.cols)
    else:
        show(int(a.path), int(a.csv) if a.csv else 0)


if __name__ == '__main__':
    main()
