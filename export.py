# -*- coding: utf-8 -*-
"""Batch exporter for the 自由幻想 NPC sprites (`.gsn` / DIMG).

Modes
-----
frame   one PNG per frame:  <out>/<npcNNN>/d<dir>_<k>.png   (+ .done marker)
atlas   one PNG per file :  <out>/<npcNNN>.png  (+ <npcNNN>.json frame boxes)
plan    header/record walk only (NO pixel decoding): counts, sizes, estimate

usage
-----
    python export.py --mode plan                 # survey: frames, bytes, failures
    python export.py --out out\\exp --limit 20    # trial
    python export.py --out out\\export            # full run, one process
    python export.py --out out\\export --shard 0/6 --quiet   # full run, sharded
    python export.py --out out\\export --resume  # re-run, skip finished files
    python export.py --check                     # verify the fast decoder

Notes
-----
* `--lenient` additionally exports files whose *frame walk* is fully verified
  but whose trailing direction table does not follow the standard
  `(n,0,0)` / `sum==nFrames` convention.  Such files are marked `partial` and
  their frames are written flat as `f0000.png` (no direction split known).
* Files that still fail are written to `<out>/failed*.csv`; nothing is
  silently skipped.  `index*.csv` records one row per file.
* The sandbox blocks multiprocessing IPC (`--jobs > 1` -> WinError 5), so the
  full run is meant to be sharded instead: start N processes with
  `--shard i/N`, each into the same --out directory.
"""
import argparse
import csv
import fnmatch
import json
import mmap
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import dimg  # noqa: E402

SRC = dimg.SRC

# byte -> 8 bit, nibble replicated (matches dimg.pixel(..., alpha_high=True)):
#   byte0 = G<<4|B , byte1 = A<<4|R
T_LO = bytes(((v & 0xF) * 17) for v in range(256))
T_HI = bytes(((v >> 4) * 17) for v in range(256))

FIELDS = ['file', 'status', 'version', 'size', 'oh', 'first_px', 'frames',
          'skipped', 'dirs', 'method', 'pngs', 'px_bytes', 'png_bytes', 'err',
          'seconds']


def get_img(d, px, w, h, bpp=2):
    """RGBA image of one frame -- all bulk slices at C speed."""
    from PIL import Image
    n = w * h
    if bpp == 4:
        raw = bytes(d[px:px + 4 * n])
        ro, go, bo, ao = dimg.BPP4_ORDER
        out = bytearray(4 * n)
        out[0::4] = raw[ro::4]
        out[1::4] = raw[go::4]
        out[2::4] = raw[bo::4]
        out[3::4] = raw[ao::4]
        return Image.frombytes('RGBA', (w, h), bytes(out))
    raw = bytes(d[px:px + 2 * n])
    b0 = raw[0::2]          # G<<4 | B
    b1 = raw[1::2]          # A<<4 | R
    out = bytearray(4 * n)
    out[0::4] = b1.translate(T_LO)      # R = low nibble  of byte1
    out[1::4] = b0.translate(T_HI)      # G = high nibble of byte0
    out[2::4] = b0.translate(T_LO)      # B = low nibble  of byte0
    out[3::4] = b1.translate(T_HI)      # A = high nibble of byte1
    return Image.frombytes('RGBA', (w, h), bytes(out))


def lenient_parse(d, h):
    """Frames verified by the walk, but the dir table breaks the convention."""
    for fp, oh, tag in dimg.hints(h):
        frames, ok, why = dimg.walk(d, fp, oh, h['n_frames'])
        if not ok or not frames:
            continue
        last_pre, lw, lh, lpx, lbpp = frames[-1]
        end = last_pre + oh + (0 if lpx is None else lbpp * lw * lh)
        tail = len(d) - end
        if tail == 12 * h['n_dirs'] + (oh - 28):
            o = len(d) - 12 * h['n_dirs']
            rows = [[dimg.u32(d, o + 12 * i + 4 * j) for j in range(3)]
                    for i in range(h['n_dirs'])]
            return {'ok': True, 'header': h, 'tag': tag, 'first_px': fp,
                    'oh': oh, 'frames': frames, 'end': end, 'tail': tail,
                    'dir_counts': [], 'skipped':
                        sum(1 for f in frames if f[3] is None),
                    'raw_dirs': rows, 'method': 'lenient'}
    return None


def _open(path):
    f = open(path, 'rb')
    return f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)


def export_one(job):
    """Worker: export (or plan) a single file.  Returns the index row."""
    (name, src, out, mode, max_pixels, level, atlas_w, lenient,
     resume) = job
    path = os.path.join(src, name)
    stem = os.path.splitext(name)[0]
    res = dict.fromkeys(FIELDS, '')
    res.update(file=name, status='', pngs=0, px_bytes=0, png_bytes=0,
               seconds=0.0)
    t0 = time.time()
    f = None
    try:
        if resume:
            if mode == 'atlas' and os.path.exists(os.path.join(out, stem + '.png')):
                res['status'] = 'skip'
                return res
            if mode == 'frame' and os.path.exists(
                    os.path.join(out, stem, '.done')):
                res['status'] = 'skip'
                return res
        f, d = _open(path)
        res['size'] = len(d)
        r = dimg.parse(d)
        h = r['header']
        res['version'] = f"{h['major']}.{h['minor']}.{h['n_dirs']}"
        res['frames'] = h['n_frames']
        if not r['ok'] and lenient:
            r = lenient_parse(d, h) or r
        if not r['ok']:
            res['status'] = 'fail'
            res['err'] = ' ; '.join(r['tried'][:2])[:300]
            return res
        res.update(oh=r['oh'], first_px=r['first_px'], skipped=r['skipped'],
                   dirs='|'.join(str(x) for x in r['dir_counts']),
                   method=r['method'], status='ok',
                   px_bytes=sum(bpp * w * hh for _, w, hh, px, bpp
                                in r['frames'] if px))
        if mode == 'plan':
            return res
        if r.get('dir_note'):
            res['err'] = r['dir_note'][:300]
        if not r['dir_counts']:
            res['status'] = 'partial'
            res['err'] = (r.get('dir_note') or
                          ('walk verified; dir table ' +
                           json.dumps(r.get('raw_dirs', []))))[:300]

        fl = [(di, k, w, hh, px, bpp)
              for (pre, w, hh, px, bpp), (di, k) in zip(
                  r['frames'],
                  ((di, k) for di, c in enumerate(r['dir_counts'] or
                                                  [len(r['frames'])])
                   for k in range(c)))]
        todo = [x for x in fl if x[4] is not None and x[2] * x[3] <= max_pixels]
        if not todo and res['status'] == 'ok':
            res['status'] = 'empty'          # pure anchor table
            return res

        if mode == 'frame':
            dst = os.path.join(out, stem)
            os.makedirs(dst, exist_ok=True)
            for di, k, w, hh, px, bpp in todo:
                img = get_img(d, px, w, hh, bpp)
                fn = (f'd{di + 1}_{k:03d}.png' if r['dir_counts']
                      else f'f{k:04d}.png')
                fp_ = os.path.join(dst, fn)
                img.save(fp_, compress_level=level)
                res['pngs'] += 1
                res['png_bytes'] += os.path.getsize(fp_)
            with open(os.path.join(dst, '.done'), 'w') as fh:
                fh.write(f'{len(todo)}\n')
        else:                                # atlas
            from PIL import Image
            boxes = []
            x = y = rowh = used_w = 0
            for di, k, w, hh, px, bpp in todo:
                if x and x + w > atlas_w:      # shelf packing
                    y += rowh
                    x = rowh = 0
                boxes.append((di, k, w, hh, px, bpp, x, y))
                x += w
                used_w = max(used_w, x)
                rowh = max(rowh, hh)
            sheet = Image.new('RGBA', (max(1, used_w), max(1, y + rowh)))
            for di, k, w, hh, px, bpp, bx, by in boxes:
                sheet.paste(get_img(d, px, w, hh, bpp), (bx, by))
            fn = os.path.join(out, stem + '.png')
            sheet.save(fn, compress_level=level)
            res['png_bytes'] = os.path.getsize(fn)
            res['pngs'] = 1
            with open(os.path.join(out, stem + '.json'), 'w',
                      encoding='utf-8') as fh:
                json.dump({'file': name, 'version': res['version'],
                           'sheet': stem + '.png', 'atlas_w': atlas_w,
                           'boxes': [{'dir': b[0] + 1, 'k': b[1], 'w': b[2],
                                      'h': b[3], 'x': b[6], 'y': b[7]}
                                     for b in boxes]}, fh)
    except Exception as e:                    # noqa: BLE001
        res['status'] = 'fail'
        res['err'] = f'{type(e).__name__}: {e}'[:300]
    finally:
        if f is not None:
            try:
                f.close()
            except Exception:
                pass
    res['seconds'] = round(time.time() - t0, 3)
    return res


def check():
    """Fast decoder must agree with dimg.to_image byte for byte."""
    names = [n for n in sorted(os.listdir(SRC)) if n.endswith('.gsn')]
    tested = 0
    for name in names:
        f, d = _open(os.path.join(SRC, name))
        try:
            r = dimg.parse(d)
            if not r['ok']:
                continue
            for pre, w, h, px, bpp in r['frames']:
                if px is None or w * h > 200000:
                    continue
                assert dimg.to_image(d, px, w, h, bpp).tobytes() == \
                    get_img(d, px, w, h, bpp).tobytes(), f'{name} @{pre} mismatch'
                tested += 1
                if tested >= 40:
                    print(f'fast decoder matches dimg.to_image '
                          f'on {tested} frames')
                    return
        finally:
            f.close()
    print(f'fast decoder matches dimg.to_image on {tested} frames')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=SRC)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'export'))
    ap.add_argument('--mode', choices=['frame', 'atlas', 'plan'], default='frame')
    ap.add_argument('--jobs', type=int, default=1,
                    help='in-process workers (blocked by the sandbox: use --shard)')
    ap.add_argument('--shard', default='', help='i/N: process names[i::N] only')
    ap.add_argument('--limit', type=int, default=0, help='only first N files')
    ap.add_argument('--sample', type=int, default=0,
                    help='N files spread evenly over the size distribution')
    ap.add_argument('--glob', default='*.gsn')
    ap.add_argument('--names', default='',
                    help='text file listing the .gsn names to export')
    ap.add_argument('--max-pixels', type=int, default=4_000_000)
    ap.add_argument('--level', type=int, default=6, help='PNG compress_level 0-9')
    ap.add_argument('--atlas-width', type=int, default=2048)
    ap.add_argument('--resume', action='store_true',
                    help='skip files whose output already exists')
    ap.add_argument('--lenient', action='store_true',
                    help='also export verified-walk files with odd dir tables')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    if a.check:
        return check()

    names = sorted(n for n in os.listdir(a.src)
                   if n.endswith('.gsn') and fnmatch.fnmatch(n, a.glob))
    if a.sample:
        sized = sorted(names,
                       key=lambda n: os.path.getsize(os.path.join(a.src, n)))
        names = sized[::max(1, len(sized) // a.sample)][:a.sample]
    total = len(names)
    tag = ''
    if a.names:
        with open(a.names, encoding='utf-8-sig') as fh:
            want = []
            for ln in fh:
                ln = ln.strip()
                if ln:
                    want.append(ln if ln.endswith('.gsn') else ln + '.gsn')
        keep = set(want)
        names = [n for n in names if n in keep]
        tag = '.names'
    if a.shard:
        i, n = (int(x) for x in a.shard.split('/'))
        names = names[i::n]
        tag = f'.shard{i}'
    if a.limit:
        names = names[:a.limit]
    if not names:
        print('nothing to do')
        return
    if a.mode != 'plan':
        os.makedirs(a.out, exist_ok=True)

    jobs = [(n, a.src, a.out, a.mode, a.max_pixels, a.level, a.atlas_width,
             a.lenient, a.resume) for n in names]
    t0 = time.time()
    rows, done, counts = [], 0, {}

    def handle(res):
        nonlocal done
        done += 1
        counts[res['status']] = counts.get(res['status'], 0) + 1
        rows.append(res)
        if res['status'] not in ('ok', 'empty', 'skip') or not a.quiet:
            if res['status'] not in ('ok',):
                print(f'[{done}/{len(jobs)}] {res["file"]:22s} '
                      f'{res["status"]:7s} v{res["version"]:8s} '
                      f'frames={res["frames"]} {res["err"]}', flush=True)
        elif done % 200 == 0:
            el = time.time() - t0
            print(f'[{done}/{len(jobs)}] {done/el:.1f} files/s eta '
                  f'{(len(jobs)-done)/(done/el)/60:.1f} min', flush=True)

    pool = None
    if a.jobs > 1:
        try:
            pool = Pool(a.jobs)
        except Exception as e:                # noqa: BLE001
            print(f'pool unavailable ({e}); running serially')
            pool = None
    if pool is not None:
        it = pool.imap_unordered(export_one, jobs, chunksize=1)
        try:
            while True:
                try:
                    res = next(it)
                except StopIteration:
                    break
                handle(res)
        except Exception as e:                # noqa: BLE001
            print(f'pool failed ({type(e).__name__}: {e}); serial for the rest',
                  flush=True)
            for j in jobs[done:]:
                handle(export_one(j))
        finally:
            try:
                pool.close()
                pool.join()
            except Exception:
                pass
    else:
        for j in jobs:
            handle(export_one(j))

    el = time.time() - t0
    ok = [r for r in rows if r['status'] in ('ok', 'empty', 'partial')]
    bad = [r for r in rows if r['status'] == 'fail']
    frames = sum(int(r['frames'] or 0) for r in ok)
    px = sum(r['px_bytes'] for r in ok)
    pngs = sum(r['pngs'] for r in ok)
    pngb = sum(r['png_bytes'] for r in ok)
    print(f'\n=== shard{tag or "-"} {len(rows)}/{total} files in {el:.1f}s '
          f'({len(rows)/el:.1f}/s)')
    for k in sorted(counts):
        print(f'    {k:8s} {counts[k]}')
    print(f'frames={frames} raw={px/2**30:.2f} GiB attempted={pngs} '
          f'png={pngb/2**30:.2f} GiB'
          + (f' ratio={pngb/px:.2f}' if px else ''))
    print(f'projected whole corpus for this mode/level: '
          f'{el/len(rows)*19828/60:.0f} min of wall clock (all shards together)')

    p = os.path.join(a.out if a.mode != 'plan' else os.path.join(HERE, 'out'),
                     ('plan' if a.mode == 'plan' else 'index') + tag + '.csv')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r['file']))
    print(f'wrote {p}')
    if bad:
        p = os.path.join(os.path.dirname(p), 'failed' + tag + '.csv')
        with open(p, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(sorted(bad, key=lambda r: r['file']))
        print(f'wrote {p} ({len(bad)} failing files)')


if __name__ == '__main__':
    main()
