"""Decoder for `official\\res\\*.gsa` (`QQF\\x1aIANI` container).

Layout
------
0..7    magic b'QQF\\x1aIANI'
8..47   10 u32: ver(65536), hdrsize(36), aw, ah, bw, bh, frames, cw, ch, stride
48..51  u32 f48: < 2 -> 2 bytes/px (A4R4G4B4), >= 2 -> 4 bytes/px (B,G,R,A)
52..    tiles of cw*ch*bpp bytes; every tile after the first is preceded by a
        16 byte tile header (cw, ch, stride, f48)

A file's tile count is taken from its size (52 + n*tile + (n-1)*16 == size),
so no grid arithmetic is needed.  Tiles are laid out row-major: the first
`frames` are frames when nx*ny == 1; otherwise each frame is a nx*ny grid.

CLI
---
    python gsa.py census [--csv out/gsa.csv]
    python gsa.py png  <outdir> [--step N] [--limit N] [--sub DIR]
    python gsa.py sheet <outpng> [--step N] [--per-page 96] [--cols 12]
    python gsa.py show <file.gsa> [frame]
"""
import collections
import os

import pkg
import struct
import sys

from PIL import Image

_BASE = pkg.PKG_ROOT
ROOT = os.path.join(_BASE, 'data', 'official', 'res')
MAGIC = b'QQF\x1aIANI'
HEAD = 52
TH = 16


# ---------------------------------------------------------------- discovery
def all_files(root=ROOT, sub=None):
    base = os.path.join(root, sub) if sub else root
    out = []
    for dp, dn, fn in os.walk(base):
        for f in sorted(fn):
            if f.lower().endswith('.gsa'):
                out.append(os.path.join(dp, f))
    return sorted(out)


# ---------------------------------------------------------------- header
def parse(d):
    if len(d) < HEAD or d[:8] != MAGIC:
        return None
    ver, hdrsize, aw, ah, bw, bh, frames, cw, ch, stride = struct.unpack_from('<10I', d, 8)
    f48 = struct.unpack_from('<I', d, 48)[0]
    bpp = 4 if f48 >= 2 else 2
    if not (cw and ch and frames):
        return None
    tile = cw * ch * bpp
    n = (len(d) - HEAD + TH) // (tile + TH)
    if HEAD + n * tile + (n - 1) * TH != len(d):
        return None
    return dict(ver=ver, hdrsize=hdrsize, aw=aw, ah=ah, bw=bw, bh=bh, frames=frames,
                cw=cw, ch=ch, stride=stride, bpp=bpp, f48=f48, tile=tile, n_tiles=n)


def tiles(d, h):
    """Yield (w, h, bpp, offset) for every tile."""
    pos = HEAD
    out = []
    for i in range(h['n_tiles']):
        w, hh, stride, f48 = h['cw'], h['ch'], h['stride'], h['f48']
        if i:
            w, hh, stride, f48 = struct.unpack_from('<4I', d, pos)
            pos += TH
        out.append((w, hh, 4 if f48 >= 2 else 2, pos))
        pos += h['tile']
    return out


# ---------------------------------------------------------------- pixels
def px4(raw, w, hh):
    """4 bytes/px, memory order B,G,R,A -> RGBA bytes."""
    out = bytearray(w * hh * 4)
    out[0::4] = raw[2::4]
    out[1::4] = raw[1::4]
    out[2::4] = raw[0::4]
    out[3::4] = raw[3::4]
    return bytes(out)


T_LO = bytes((v & 0xF) * 17 for v in range(256))
T_HI = bytes((v >> 4) * 17 for v in range(256))


def px2(raw, w, hh):
    """2 bytes/px, byte0 = G<<4|B, byte1 = A<<4|R -> RGBA bytes."""
    b0 = raw[0::2]
    b1 = raw[1::2]
    out = bytearray(w * hh * 4)
    out[0::4] = b1.translate(T_LO)
    out[1::4] = b0.translate(T_HI)
    out[2::4] = b0.translate(T_LO)
    out[3::4] = b1.translate(T_HI)
    return bytes(out)


def to_image(d, entry):
    w, hh, bpp, off = entry
    raw = d[off:off + w * hh * bpp]
    rgba = px4(raw, w, hh) if bpp == 4 else px2(raw, w, hh)
    return Image.frombytes('RGBA', (w, hh), rgba)


def frames(d, h):
    """Assemble the frame images (one per animation frame)."""
    ts = tiles(d, h)
    nx = max(1, -(-h['bw'] // h['cw']))
    ny = max(1, -(-h['bh'] // h['ch']))
    per = nx * ny
    out = []
    for fi in range(h['frames']):
        chunk = ts[fi * per:(fi + 1) * per]
        if not chunk:
            break
        if per == 1:
            out.append(to_image(d, chunk[0]))
            continue
        cw, ch = h['cw'], h['ch']
        canvas = Image.new('RGBA', (nx * cw, ny * ch), (0, 0, 0, 0))
        for i, e in enumerate(chunk):
            canvas.alpha_composite(to_image(d, e), ((i % nx) * cw, (i // nx) * ch))
        out.append(canvas.crop((0, 0, min(h['bw'], nx * cw), min(h['bh'], ny * ch))))
    return out


def size_of(im):
    return im.size


# ---------------------------------------------------------------- commands
def census(root=ROOT, csv_path=None, sub=None):
    fs = all_files(root, sub)
    ok = bad = 0
    tot_frames = 0
    f48s = collections.Counter()
    vers = collections.Counter()
    dims = collections.Counter()
    biggest = []
    rows = []
    for p in fs:
        d = open(p, 'rb').read()
        h = parse(d)
        if h is None:
            bad += 1
            rows.append((os.path.relpath(p, root), len(d), 'fail', '', '', '', '', ''))
            continue
        ok += 1
        tot_frames += h['frames']
        f48s[h['f48']] += 1
        vers[(h['ver'] >> 16, h['hdrsize'])] += 1
        dims[(h['bw'], h['bh'])] += 1
        biggest.append((len(d), os.path.relpath(p, root), h['bw'], h['bh'], h['frames']))
        rows.append((os.path.relpath(p, root), len(d), 'ok', h['bw'], h['bh'],
                     h['frames'], h['bpp'], h['n_tiles']))
    biggest.sort(reverse=True)
    print('files %d  ok %d  fail %d' % (len(fs), ok, bad))
    print('total frames', tot_frames, ' tiles', sum(r[7] for r in rows if r[2] == 'ok'))
    print('f48 ->', f48s.most_common())
    print('(ver,hdrsize) ->', vers.most_common())
    print('top sizes ->', dims.most_common(10))
    print('largest ->')
    for b in biggest[:10]:
        print('   %-46s %9d B  %dx%d  %d frames' % (b[1], b[0], b[2], b[3], b[4]))
    if csv_path:
        with open(csv_path, 'w', encoding='utf-8', newline='') as fh:
            fh.write('file,size,status,w,h,frames,bpp,tiles\n')
            for r in rows:
                fh.write(','.join(str(x) for x in r) + '\n')
        print('csv ->', csv_path)


def pngs(root, outdir, step=1, limit=None, sub=None):
    fs = all_files(root, sub)
    if step > 1:
        fs = fs[::step]
    if limit:
        fs = fs[:limit]
    made = 0
    bytes_ = 0
    fails = []
    for i, p in enumerate(fs, 1):
        d = open(p, 'rb').read()
        h = parse(d)
        if h is None:
            fails.append(os.path.relpath(p, root))
            continue
        rel = os.path.relpath(p, root)
        stem = os.path.splitext(rel)[0].replace(os.sep, '__')
        dst = os.path.join(outdir, stem)
        os.makedirs(dst, exist_ok=True)
        try:
            ims = frames(d, h)
        except Exception as e:  # noqa: BLE001
            fails.append('%s: %s' % (rel, e))
            continue
        for k, im in enumerate(ims):
            f = os.path.join(dst, 'f%03d.png' % k)
            im.save(f)
            made += 1
            bytes_ += os.path.getsize(f)
        if i % 200 == 0:
            print('  %d/%d  %d png' % (i, len(fs), made), flush=True)
    print('files %d  png %d  %.1f MB  fails %d' % (len(fs), made, bytes_ / 1048576, len(fails)))
    for f in fails[:10]:
        print('   fail', f)


def sheet(root, outpng, step=1, per_page=96, cols=12, sub=None):
    from PIL import ImageDraw
    fs = all_files(root, sub)
    if step > 1:
        fs = fs[::step]
    picks = []
    for p in fs:
        d = open(p, 'rb').read()
        h = parse(d)
        if h is None:
            continue
        try:
            im = frames(d, h)[0]
        except Exception:  # noqa: BLE001
            continue
        picks.append((os.path.relpath(p, root), im))
    print('picked', len(picks))
    cw, chh = 132, 176
    pages = -(-len(picks) // per_page)
    base, ext = os.path.splitext(outpng)
    for pg in range(pages):
        batch = picks[pg * per_page:(pg + 1) * per_page]
        rows = -(-len(batch) // cols)
        sheet_im = Image.new('RGBA', (cols * cw, rows * chh), (40, 42, 49, 255))
        dr = ImageDraw.Draw(sheet_im)
        for i, (name, im) in enumerate(batch):
            w, hh = im.size
            sc = min((cw - 8) / w, (chh - 26) / hh, 4.0)
            nw, nh = max(1, int(w * sc)), max(1, int(hh * sc))
            tile = im.resize((nw, nh), Image.NEAREST)
            x = (i % cols) * cw + (cw - nw) // 2
            y = (i // cols) * chh + 4 + (chh - 26 - nh) // 2
            sheet_im.alpha_composite(tile, (x, y))
            dr.text((i % cols * cw + 4, (i // cols) * chh + chh - 20), name[-24:], fill=(220, 220, 220, 255))
        path = outpng if pg == 0 else '%s-%d%s' % (base, pg + 1, ext)
        sheet_im.convert('RGB').save(path)
        print('  ->', path, sheet_im.size)


def show(path, frame=0):
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    d = open(p, 'rb').read()
    h = parse(d)
    print(p, len(d))
    print(' ', h)
    ims = frames(d, h)
    print('  frames', len(ims), [im.size for im in ims[:8]])
    im = ims[frame]
    print('  frame', frame, im.size, 'bbox', im.getbbox())
    return im


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    rest = [a for a in args[1:] if not a.startswith('--')]
    opt = {}
    for i, a in enumerate(args[1:]):
        if a.startswith('--'):
            nxt = args[i + 2] if i + 2 < len(args) else ''
            opt[a] = nxt if (nxt and not nxt.startswith('--')) else True
    step = int(opt.get('--step', 1) or 1)
    limit = opt.get('--limit')
    sub = opt.get('--sub') if isinstance(opt.get('--sub'), str) else None
    if cmd == 'census':
        csv_path = opt.get('--csv') if isinstance(opt.get('--csv'), str) else None
        census(csv_path=csv_path, sub=sub)
    elif cmd == 'png':
        outdir = rest[0] if rest else 'out/gsa'
        pngs(ROOT, outdir, step, int(limit) if limit else None, sub)
    elif cmd == 'sheet':
        outpng = rest[0] if rest else 'out/gsa_sheet.png'
        per = int(opt.get('--per-page', 96) or 96)
        cols = int(opt.get('--cols', 12) or 12)
        sheet(ROOT, outpng, step, per, cols, sub)
    elif cmd == 'show':
        show(rest[0], int(rest[1]) if len(rest) > 1 else 0)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
