"""Analyze the whole object\\ tree (34 sub-folders, 19,160 .gso).

    python obj.py census [--csv out\\obj.csv] [--limit N]
    python obj.py png    out\\object [--step 8] [--limit N]
    python obj.py sheet  out\\object_sheet.png [--step 8] [--per-page 96]
    python obj.py mask   [--show N]

object\\ holds scenery / building / tree pieces.  Every image file is a DIMG
container (.gso), and most of them are accompanied by a tiny .mask side file.
"""
import collections
import os
import sys

import dimg
import gso
import paths

ROOT = paths.sub('data/official/object')


def all_image_files(root=ROOT):
    out = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if os.path.splitext(f)[1].lower() in ('.gso', '.gsn'):
                out.append(os.path.join(dp, f))
    return sorted(out)


def all_files(root, ext):
    out = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if os.path.splitext(f)[1].lower() == ext:
                out.append(os.path.join(dp, f))
    return sorted(out)


def census(csv_path=None, limit=None):
    fs = all_image_files()
    if limit:
        fs = fs[:limit]
    print('files %d' % len(fs), flush=True)
    rows = []
    ok = 0
    bad = []
    notdimg = []
    vers = collections.Counter()
    ohs = collections.Counter()
    methods = collections.Counter()
    frames_total = 0
    empty_total = 0
    px_total = 0
    dirs_hist = collections.Counter()
    sizes = collections.Counter()
    per = collections.Counter()
    per_frames = collections.Counter()
    biggest = []
    t0 = __import__('time').time()
    for i, p in enumerate(fs):
        try:
            with open(p, 'rb') as fh:
                d = fh.read()
        except OSError as e:
            bad.append((p, 'read: %s' % e))
            continue
        try:
            r = dimg.parse(d, brute=False)
            if not r['ok']:
                r = dimg.parse(d, brute=True)
        except Exception as e:                       # noqa: BLE001 - survey
            r = {'ok': False, 'err': '%s: %s' % (type(e).__name__, e)}
        sub = os.path.relpath(os.path.dirname(p), ROOT)
        per[sub] += 1
        if d[:8] != b'QQF\x1aDIMG':
            # DX\DX_DFYW_0301.gso carries a .mask style payload, not DIMG.
            notdimg.append((os.path.relpath(p, ROOT), len(d)))
            rows.append(dict(file=os.path.relpath(p, ROOT), sub=sub, size=len(d),
                             ok=0, method='not-dimg', tag='', oh=0, first_px=0,
                             frames=0, dirs='', extra=0, bpp=0, px_bytes=0,
                             err='no DIMG signature (mask payload)'))
            continue
        if not r['ok']:
            bad.append((p, r.get('err', '?')))
            rows.append(dict(file=os.path.relpath(p, ROOT), sub=sub, size=len(d),
                             ok=0, method='', tag='', oh=0, first_px=0,
                             frames=0, dirs='', extra=0, bpp=0,
                             px_bytes=0, err=r.get('err', '?')))
            continue
        ok += 1
        h = r['header']
        vers['%d.%d' % (h['major'], h['minor'])] += 1
        ohs[r['oh']] += 1
        methods[r['method']] += 1
        frames_total += len(r['frames'])
        per_frames[sub] += len(r['frames'])
        empty_total += r['skipped']
        px_total += r['px_bytes']
        dc = r['dir_counts']
        dirs_hist[(len(dc), dc[0] if dc and len(set(dc)) == 1 else -1)] += 1
        for f in r['frames']:
            if f[3] is not None:
                sizes[(f[1], f[2])] += 1
        biggest.append((len(d), os.path.relpath(p, ROOT)))
        rows.append(dict(file=os.path.relpath(p, ROOT), sub=sub, size=len(d),
                         ok=1, method=r['method'], tag=r['tag'], oh=r['oh'],
                         first_px=r['first_px'], frames=len(r['frames']),
                         dirs=' '.join(str(x) for x in dc), extra=r['extra'],
                         bpp=r['bpp'], px_bytes=r['px_bytes'], err=''))
        if (i + 1) % 2000 == 0:
            print('  %d/%d  %.0fs' % (i + 1, len(fs), __import__('time').time() - t0),
                  flush=True)
    print('ok %d  fail %d  not-dimg %d  frames %d  empty %d  pixels %.1f MB  %.0fs'
          % (ok, len(bad), len(notdimg), frames_total, empty_total,
             px_total / 1048576, __import__('time').time() - t0))
    print('versions', dict(vers.most_common()))
    print('oh', dict(sorted(ohs.items())))
    print('methods', dict(methods.most_common()))
    print('dirs (n_dirs, uniform) -> files', dict(dirs_hist.most_common(10)))
    print('per subdir files', dict(per.most_common()))
    print('per subdir frames', dict(per_frames.most_common()))
    print('sprite sizes top', sizes.most_common(10))
    print('biggest', [(n, s) for s, n in sorted(biggest)[-5:][::-1]])
    if bad:
        print('failures:')
        for p, e in bad[:20]:
            print('  ', os.path.relpath(p, ROOT), '|', e)
    if notdimg:
        print('not-DIMG containers:', notdimg[:10])
    if csv_path:
        gso.write_csv(csv_path, rows)
        print('csv', csv_path)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    cmd = a[0]
    opt = {}
    rest = []
    i = 1
    valued = ('--csv', '--step', '--limit', '--per-page', '--cols', '--show')
    while i < len(a):
        t = a[i]
        if t.startswith('--'):
            if t in valued and i + 1 < len(a):
                opt[t] = a[i + 1]
                i += 2
            else:
                opt[t] = True
                i += 1
        else:
            rest.append(t)
            i += 1
    if cmd == 'census':
        census(opt.get('--csv'), int(opt['--limit']) if '--limit' in opt else None)
    elif cmd == 'png':
        outdir = rest[0] if rest else os.path.join('out', 'object')
        gso.pngs(ROOT, outdir, step=int(opt.get('--step', 1)),
                 limit=int(opt['--limit']) if '--limit' in opt else None,
                 recursive=True)
    elif cmd == 'sheet':
        out = rest[0] if rest else os.path.join('out', 'object_sheet.png')
        gso.sheet(ROOT, out, cols=int(opt.get('--cols', 12)),
                  per_page=int(opt.get('--per-page', 96)),
                  step=int(opt.get('--step', 1)), recursive=True)
    elif cmd == 'mask':
        show_masks(int(opt.get('--show', 6)))
    else:
        print(__doc__)


def show_masks(n):
    ms = all_files(ROOT, '.mask')
    print('mask files', len(ms))
    sizes = collections.Counter(os.path.getsize(p) for p in ms)
    print('sizes top', sizes.most_common(8), 'distinct', len(sizes))
    # parse as: 8B header, then n int32 values, then tail of 0x80
    for p in ms[:n]:
        d = open(p, 'rb').read()
        print('==', os.path.relpath(p, ROOT), len(d))
        print('   head', d[:16].hex(' '))


if __name__ == '__main__':
    main()
