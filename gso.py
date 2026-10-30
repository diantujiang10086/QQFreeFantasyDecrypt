"""Census / export / contact sheet for arbitrary DIMG folders outside avatar\\.

    python gso.py census                      # item\\item, item\\itempic, magic\\magic
    python gso.py census "D:\\some\\dir"       # any directory
    python gso.py png    "…\\item\\item" out\\item
    python gso.py sheet  "…\\item\\item" out\\item_sheet.png [--step N] [--cols N]

Files are the same DIMG container as .gsn, only the extension differs (.gso).
"""
import collections
import csv
import os
import sys

import dimg

OFFICIAL = r'F:\WG自由幻想\自由幻想\data\data\official'
DEF = [os.path.join(OFFICIAL, 'item', 'item'),
       os.path.join(OFFICIAL, 'item', 'itempic'),
       os.path.join(OFFICIAL, 'magic', 'magic')]
HERE = os.path.dirname(os.path.abspath(__file__))


def files_of(root, exts=('.gso', '.gsn')):
    return sorted(f for f in os.listdir(root) if os.path.splitext(f)[1].lower() in exts)


def walk_files(root, exts=('.gso', '.gsn'), recursive=False):
    """Absolute paths of every image file, honouring `recursive`."""
    if not recursive:
        return [os.path.join(root, n) for n in files_of(root, exts)]
    out = []
    for dp, dn, fn in os.walk(root):
        for f in sorted(fn):
            if os.path.splitext(f)[1].lower() in exts:
                out.append(os.path.join(dp, f))
    return out


def write_csv(path, rows):
    p = path if os.path.isabs(path) else os.path.join(HERE, path)
    os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    with open(p, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return p


def census(roots, csv_path=None):
    rows = []
    for root in roots:
        names = files_of(root)
        print('=== %s: %d files' % (root, len(names)), flush=True)
        stat = collections.Counter()
        vers = collections.Counter()
        ohs = collections.Counter()
        pats = collections.Counter()
        sizes = collections.Counter()
        frames = skips = pxb = nbytes = 0
        bad = []
        for i, n in enumerate(names):
            p = os.path.join(root, n)
            with open(p, 'rb') as fh:
                d = fh.read()
            nbytes += len(d)
            h = dimg.head(d)
            r = dimg.parse(d, brute=False)
            tag = 'version-table'
            if not r['ok']:
                r = dimg.parse(d, brute=True)
                tag = 'brute'
            stat[tag if r['ok'] else 'FAIL'] += 1
            vers['%d.%d' % (h['major'], h['minor'])] += 1
            if r['ok']:
                ohs[r['oh']] += 1
                pats['|'.join(str(x) for x in (r.get('dir_counts') or []))] += 1
                frames += len(r['frames'])
                skips += r.get('skipped', 0)
                pxb += r.get('px_bytes', 0)
                for f in r['frames']:
                    if f[3] is not None:
                        sizes[(f[1], f[2])] += 1
                rows.append(dict(file=n, folder=os.path.basename(root), size=len(d),
                                 ok=1, method=tag, tag='%d.%d' % (h['major'], h['minor']),
                                 oh=r['oh'], first_px=r['first_px'],
                                 frames=len(r['frames']),
                                 dirs='|'.join(str(x) for x in (r.get('dir_counts') or [])),
                                 extra=r.get('extra'), bpp=r.get('bpp'), err=''))
            else:
                bad.append((n, r.get('err')))
                rows.append(dict(file=n, folder=os.path.basename(root), size=len(d),
                                 ok=0, method='-', tag='%d.%d' % (h['major'], h['minor']),
                                 oh='', first_px='', frames='', dirs='', extra='', bpp='',
                                 err=r.get('err')))
            if (i + 1) % 1000 == 0:
                print('  ...%d/%d' % (i + 1, len(names)), flush=True)
        print('  methods:', dict(stat))
        print('  versions:', dict(vers))
        print('  oh:', dict(ohs))
        print('  dir patterns (%d):' % len(pats))
        for k, v in pats.most_common(20):
            print('    %-28s %d' % (k, v))
        print('  frames %d  empty %d  pixel bytes %d (%.1f MB)  raw %.1f MB'
              % (frames, skips, pxb, pxb / 1048576, nbytes / 1048576))
        print('  sprite sizes (top 10):', sizes.most_common(10))
        if bad:
            print('  FAIL %d:' % len(bad))
            for n, e in bad[:10]:
                print('    ', n, (e or '')[:100])
    if csv_path:
        p = os.path.join(HERE, csv_path)
        os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
        with open(p, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print('csv ->', p)


def pngs(root, outdir, step=1, limit=None, recursive=False):
    files = walk_files(root, recursive=recursive)[::max(1, step)]
    if limit:
        files = files[:limit]
    os.makedirs(outdir, exist_ok=True)
    total = 0
    for i, p in enumerate(files):
        with open(p, 'rb') as fh:
            d = fh.read()
        r = dimg.parse(d, brute=True)
        if not r['ok']:
            print('FAIL', os.path.basename(p), r.get('err'))
            continue
        stem = os.path.splitext(os.path.relpath(p, root))[0]
        stem = stem.replace(os.sep, '_')
        sub = os.path.join(outdir, stem)
        os.makedirs(sub, exist_ok=True)
        dirs = r.get('dir_counts') or []
        k = 0
        if dirs:
            for di, count in enumerate(dirs, 1):
                for j in range(count):
                    f = r['frames'][k]
                    k += 1
                    if f[3] is None:
                        continue
                    im = dimg.to_image(d, f[3], f[1], f[2], f[4])
                    im.save(os.path.join(sub, 'd%d_%03d.png' % (di, j + 1)))
                    total += 1
        else:
            for j, f in enumerate(r['frames']):
                if f[3] is None:
                    continue
                im = dimg.to_image(d, f[3], f[1], f[2], f[4])
                im.save(os.path.join(sub, 'f%04d.png' % j))
                total += 1
        if (i + 1) % 200 == 0:
            print('  ...%d/%d files, %d png' % (i + 1, len(files), total), flush=True)
    print('%d files, %d png -> %s' % (len(files), total, outdir))


def sheet(root, outpath, cols=12, cw=132, ch=176, per_page=96, step=1, picks=3,
          recursive=False):
    """Contact sheet: for each file, `picks` frames laid side by side in one cell."""
    from PIL import Image, ImageDraw
    files = walk_files(root, recursive=recursive)[::max(1, step)]
    tiles = []
    for p in files:
        with open(p, 'rb') as fh:
            d = fh.read()
        r = dimg.parse(d, brute=True)
        if not r['ok']:
            continue
        ims = []
        picked = collections.defaultdict(int)
        for f in r['frames']:
            if f[3] is None:
                continue
            key = (f[1], f[2])
            if picked[key] >= picks:
                continue
            picked[key] += 1
            ims.append(dimg.to_image(d, f[3], f[1], f[2], f[4]))
            if len(ims) >= 4:
                break
        if ims:
            label = os.path.splitext(os.path.relpath(p, root))[0].replace(os.sep, '_')
            tiles.append((label, ims))
    per_page = per_page or 96
    pages = [tiles[i:i + per_page] for i in range(0, len(tiles), per_page)]
    for pi, page in enumerate(pages, 1):
        rows = (len(page) + cols - 1) // cols
        W, H = cols * cw, rows * ch
        sheet_im = Image.new('RGBA', (W, H), (40, 42, 49, 255))
        dr = ImageDraw.Draw(sheet_im)
        for idx, (stem, ims) in enumerate(page):
            cx0 = (idx % cols) * cw
            cy0 = (idx // cols) * ch
            # lay the picked frames out horizontally, then scale the group to fit
            gw = sum(i.width for i in ims) + 4 * (len(ims) - 1)
            gh = max(i.height for i in ims)
            sc = min((cw - 8) / max(1, gw), (ch - 26) / max(1, gh), 4.0)
            x = cx0 + (cw - gw * sc) / 2
            y = cy0 + 4 + (ch - 22 - gh * sc) / 2
            for im in ims:
                w2, h2 = max(1, int(round(im.width * sc))), max(1, int(round(im.height * sc)))
                sheet_im.alpha_composite(im.resize((w2, h2), Image.NEAREST), (int(x), int(y)))
                x += w2 + 4 * sc
            dr.text((cx0 + 4, cy0 + ch - 18), stem[:18], fill=(210, 214, 220, 255))
        out = outpath if len(pages) == 1 else '%s-%d.png' % (os.path.splitext(outpath)[0], pi)
        sheet_im.convert('RGB').save(out)
        print('sheet %s %dx%d %d cells' % (out, W, H, len(page)), flush=True)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    opt = {}
    for i, a in enumerate(args):
        if not a.startswith('--'):
            continue
        nxt = args[i + 1] if i + 1 < len(args) else ''
        if nxt and not nxt.startswith('--'):
            opt[a] = nxt
        else:
            opt[a] = True                    # bare flag such as --recursive
    used = set(opt.values())
    rest = [a for a in args[1:] if not a.startswith('--') and a not in used]
    step = int(opt.get('--step', '1'))
    if cmd == 'census':
        roots = rest or DEF
        census(roots, opt.get('--csv'))
    elif cmd == 'png':
        pngs(rest[0], rest[1] if len(rest) > 1 else os.path.join(HERE, 'out', 'gso'), step=step,
             limit=int(opt['--limit']) if '--limit' in opt else None,
             recursive='--recursive' in opt)
    elif cmd == 'sheet':
        sheet(rest[0], rest[1] if len(rest) > 1 else os.path.join(HERE, 'out', 'gso_sheet.png'),
              step=step, cols=int(opt.get('--cols', '12')),
              per_page=int(opt.get('--per-page', '96')),
              picks=int(opt.get('--picks', '3')),
              recursive='--recursive' in opt)
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
