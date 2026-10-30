"""Export / sheet for any avatar subfolder (cap, face, weaponl, weaponr ...).

    python avaexport.py --png out\\cap cap
    python avaexport.py --sheet out\\cap_sheet cap
    python avaexport.py --stats cap

Frame naming follows the direction table when it validates
(`d<dir>_<frame>.png`, dir 1-based), else flat `f0000.png`.
"""
import os
import sys
import csv
import math
import collections

import dimg
import paths

SRCROOT = paths.sub('data/official/avatar')
HERE = os.path.dirname(os.path.abspath(__file__))


def load(folder):
    d = os.path.join(SRCROOT, folder)
    names = sorted(f for f in os.listdir(d) if f.lower().endswith('.gsn'))
    return d, names


def frame_plan(r):
    """[(dirno, k, frame)] or None when the direction table is unusable."""
    counts = r.get('dir_counts') or []
    frames = r['frames']
    if counts and sum(counts) == len(frames):
        out = []
        i = 0
        for dirno, n in enumerate(counts, 1):
            for k in range(n):
                out.append((dirno, k, frames[i]))
                i += 1
        return out
    return None


def export(folder, outdir, limit=None, step=1):
    d, names = load(folder)
    names = names[::max(1, step)]
    n_png = 0
    n_frame = 0
    rows = []
    for idx, nm in enumerate(names):
        if limit and idx >= limit:
            break
        p = os.path.join(d, nm)
        data = open(p, 'rb').read()
        r = dimg.parse(data)
        stem = nm[:-4]
        if not r['ok']:
            rows.append(dict(file=nm, status='fail', frames='', pngs=0, err=r.get('err', '')))
            continue
        plan = frame_plan(r)
        sub = os.path.join(outdir, stem)
        made = 0
        for j, f in enumerate(r['frames']):
            n_frame += 1
            pre, w, h, px, bpp = f
            if px is None:
                continue
            if plan:
                dirno, k, _ = plan[j]
                fn = 'd%d_%03d.png' % (dirno, k)
            else:
                fn = 'f%04d.png' % j
            os.makedirs(sub, exist_ok=True)
            img = dimg.to_image(data, px, w, h, bpp)
            img.save(os.path.join(sub, fn))
            made += 1
            n_png += 1
        rows.append(dict(file=nm, status='ok' if made or r['skipped'] else 'ok',
                         frames=len(r['frames']), pngs=made, err=r.get('dir_note', '')))
        if (idx + 1) % 200 == 0:
            print('  %d/%d files, %d png' % (idx + 1, len(names), n_png), flush=True)
    print('%s: %d files, %d frames, %d png -> %s' % (folder, len(names), n_frame, n_png, outdir))
    return rows


def sheet(folder, outpath, cols=12, cw=132, ch=176, per_page=96, step=1):
    """Contact sheet of the first frame of direction 1 (or first available)."""
    from PIL import Image, ImageDraw
    d, names = load(folder)
    names = names[::max(1, step)]
    cells = []
    for nm in names:
        p = os.path.join(d, nm)
        data = open(p, 'rb').read()
        r = dimg.parse(data)
        if not r['ok']:
            continue
        plan = frame_plan(r)
        pick = None
        if plan:
            for dirno, k, f in plan:
                if dirno == 1 and f[3] is not None:
                    pick = f
                    break
        if pick is None:
            for f in r['frames']:
                if f[3] is not None:
                    pick = f
                    break
        if pick is None:
            continue
        pre, w, h, px, bpp = pick
        cells.append((nm, dimg.to_image(data, px, w, h, bpp), w, h))
    pages = max(1, math.ceil(len(cells) / per_page))
    outs = []
    for pg in range(pages):
        chunk = cells[pg * per_page:(pg + 1) * per_page]
        rows = math.ceil(len(chunk) / cols)
        img = Image.new('RGBA', (cols * cw, rows * ch), (40, 42, 49, 255))
        dr = ImageDraw.Draw(img)
        for i, (nm, im, w, h) in enumerate(chunk):
            cx, cy = i % cols, i // cols
            sc = min((cw - 8) / w, (ch - 26) / h, 4.0)
            nw, nh = max(1, int(w * sc)), max(1, int(h * sc))
            tile = im.resize((nw, nh), Image.LANCZOS)
            ox = cx * cw + (cw - nw) // 2
            oy = cy * ch + (ch - 26 - nh) // 2
            img.alpha_composite(tile, (ox, oy))
            dr.text((cx * cw + 4, cy * ch + ch - 18), nm[:-4], fill=(210, 214, 222, 255))
        path = outpath if pages == 1 else outpath.replace('.png', '-%d.png' % (pg + 1))
        img.save(path)
        outs.append(path)
        print('sheet', path, img.size, len(chunk), 'cells', flush=True)
    return outs


def stats(folder):
    d, names = load(folder)
    sizes = collections.Counter()
    per = collections.Counter()
    pat = collections.Counter()
    piv = []
    for nm in names:
        data = open(os.path.join(d, nm), 'rb').read()
        r = dimg.parse(data)
        if not r['ok']:
            continue
        h = r['header']
        pw = [dimg.u32(data, 24 + 4 * i) for i in range(9)]
        piv.append((nm, pw[3], pw[4], pw[5], pw[6], len(r['frames'])))
        pat[tuple(r.get('dir_counts') or [])] += 1
        for f in r['frames']:
            if f[3] is not None:
                sizes[(f[1], f[2])] += 1
    print('files', len(names), 'parsed', len(piv))
    print('dir patterns:', len(pat))
    for k, v in pat.most_common(10):
        print('  ', k, v)
    print('sprite sizes (top 8):', sizes.most_common(8))
    big = sorted(piv, key=lambda t: -(t[1] * t[2]))[:5]
    print('largest canvases:', [(b[0][:-4], b[1], b[2]) for b in big])
    out = [p for p in piv if p[4] > p[2] or p[4] < 0]
    print('pivot cy outside [0,H]: %d / %d' % (len(out), len(piv)))
    for p in out[:6]:
        print('   %s canvas %dx%d pivot (%d,%d) frames %d' % (p[0][:-4], p[1], p[2], p[3], p[4], p[5]))


def main():
    args = sys.argv[1:]
    opt = {}
    takes_value = ('--png', '--sheet', '--step', '--limit')
    for i, a in enumerate(args):
        if a in takes_value and i + 1 < len(args) and not args[i + 1].startswith('--'):
            opt[a] = args[i + 1]
    folder = [a for a in args if not a.startswith('--') and a not in opt.values()]
    folder = [a for a in folder if not a.endswith('.csv')]
    if not folder:
        print(__doc__)
        return
    folder = folder[-1]
    if '--png' in opt:
        outdir = opt['--png']
        outdir = outdir if os.path.isabs(outdir) else os.path.join(HERE, outdir)
        step = int(opt.get('--step', '1'))
        limit = int(opt['--limit']) if '--limit' in opt else None
        rows = export(folder, outdir, limit=limit, step=step)
        csvp = os.path.join(HERE, 'out', 'export_%s.csv' % folder)
        with open(csvp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print('csv ->', csvp)
    elif '--sheet' in opt:
        step = int(opt.get('--step', '1'))
        sheet(folder, os.path.join(HERE, 'out', '%s_sheet.png' % folder), step=step)
    else:
        stats(folder)


if __name__ == '__main__':
    main()
