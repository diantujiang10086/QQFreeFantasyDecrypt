# -*- coding: utf-8 -*-
"""DIMG (.gsn) parser -- reconstructed layout, v2 (auto-detected overhead).

Structure (byte offsets):

    0   8   magic "QQF\\x1aDIMG"
    8   u16 major                (1,2,4,5 ...)
    10  u16 ?                    (0)
    12  u16 minor                (24 or 36)
    14  u16 ?                    (0)
    16  u16 nFrames
    18  u16 ?                    (0)
    20  u16 nDirs                (1,2,4,5 ...)  <- also "patch" in main.py
    22  u16 ?                    (0)
    24  ..  prefix of frame 0 (variable size, holds sprite info)
    P0  ..  frame 0 signature:  u32 w, u32 h, u32 2*w, u32 1
    P0+16   frame 0 pixels: w*h pixels, 2 bytes each
    then per frame: <oh-16 bytes prefix> <16 byte signature> <pixels>
    finally: [extra bytes] nDirs * 12 bytes, one (nFramesThatDir, 0, 0) each

A record whose four signature words are all zero carries no pixel data at
all (an animation "reuse the previous frame" entry).  It still counts as a
frame for nFrames and for the direction table; only its pixel block is
missing.  Example: npc540201.gsn has 115 records of which 8 are empty, so
only 107 signatures exist in the file.

`oh` (record overhead = signature-to-signature spacing minus 2*w*h) is
constant inside a file but is NOT determined by the version string:
measured values are 28, 40, 48, 80, 96.  So (first_px, oh) are
auto-detected and validated:

  * every one of the nFrames signatures must sit exactly where the walk
    predicts,
  * the last nDirs*12 bytes must be nDirs records of the form
    (n, 0, 0) whose first fields sum to nFrames.

Pixel: byte0 = G<<4 | B, byte1 = A<<4 | R (4 bit per channel, nibble
replicated to 8 bit -> value*17).

usage:
    python dimg.py [--png DIR] [--csv FILE] [--quiet] [--dump] [file ...]
"""
import os
import struct
import sys

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')

# version (major.minor[.patch]) -> int32 words, from main.py
# GetStartOffset / GetMultiOffset.  Used only as a fast-path hint.
GET_START = {'1.36': 17, '2.36': 17, '4.36.5': 29, '5.36': 19, '4.36': 19,
             '1.24': 14}
GET_MULTI = {'2.36': 24, '4.36.5': 24, '5.36': 10, '4.36': 10, '1.36': 7,
             '1.24': 7}
DEF_MULTI = 24
MAX_OH = 256


def u16(d, o):
    return struct.unpack_from('<H', d, o)[0]


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def head(d):
    return {
        'major': u16(d, 8), 'minor': u16(d, 12),
        'n_frames': u16(d, 16), 'n_dirs': u16(d, 20),
        'u10': u16(d, 10), 'u14': u16(d, 14), 'u18': u16(d, 18),
        'u22': u16(d, 22),
        # first three words of the 9-word preamble at @24.  Word 0 gates an
        # extra 8*word1 bytes of per-record overhead (see hints); word 2 is 0.
        'w0': u32(d, 24), 'w1': u32(d, 28), 'w2': u32(d, 32),
    }


def sig_at(d, p):
    """(w, h, bpp) if a frame signature starts at p, else None.

    The four signature words are (w, h, stride, flag).  `flag` is
    bytes-per-pixel / 2: 1 => 2 bytes per pixel (packed 4-bit channels),
    2 => 4 bytes per pixel (8-bit channels, see BPP4_ORDER).  The stride
    in bytes is 2 * flag * w in both cases.
    """
    if p < 0 or p + 16 > len(d):
        return None
    w, h, s, f = u32(d, p), u32(d, p + 4), u32(d, p + 8), u32(d, p + 12)
    if 1 <= w <= 8192 and 1 <= h <= 8192 and f in (1, 2) and s == 2 * f * w:
        return w, h, 2 * f
    return None


def hints(h):
    """(first_px, oh, tag) guesses from the header.

    Two independent hints, both only guesses: every candidate is validated
    end-to-end by `finish`, and the brute-force scan still runs if none of
    them holds.

      * the 9-word preamble at @24 starts with (w0, w1, 0).  w0 == 1 means
        every record carries 8*w1 extra bytes (measured on 19,658 library
        files: oh == 4*GET_MULTI + 8*w1 whenever w0 == 1, else
        4*GET_MULTI; w1 is unrelated to nDirs),
      * the version table from main.py (GetStartOffset / GetMultiOffset).
    """
    ver = f"{h['major']}.{h['minor']}"
    ver5 = f"{ver}.{h['n_dirs']}"
    out = []
    if h['w0'] == 1 and ver in GET_START and ver in GET_MULTI:
        oh = 4 * GET_MULTI[ver] + 8 * h['w1']
        out.append((24 + 4 * GET_START[ver], oh,
                    f'preamble w0=1 w1={h["w1"]}->{GET_START[ver]}/'
                    f'{GET_MULTI[ver]}+{2 * h["w1"]}'))
    for key in (ver5, ver):
        if key in GET_START:
            out.append((24 + 4 * GET_START[key], 4 * GET_MULTI[key],
                        f'{key}->{GET_START[key]}/{GET_MULTI[key]}'))
    if not out:
        out.append((24 + 4 * 17, 4 * DEF_MULTI, 'default->17/24'))
    if h['major'] == 4 and h['minor'] == 36:
        out.append((24 + 4 * 19, 4 * 10, '4.36.x/IMG_VERSTION=1->19/10'))
    return out


def walk(d, first_px, oh, n_frames):
    """Return (frames, ok, why).

    frames = [(prefix_start, w, h, px_start or None, bpp)]
    A record whose four signature words are all zero carries NO pixel data
    (the animation reuses the previous frame); it still counts as a frame.
    """
    frames = []
    p = first_px - 16
    for i in range(n_frames):
        if p + 16 > len(d):
            return frames, False, f'frame {i}: record starts past EOF'
        w, hh, s, f = u32(d, p), u32(d, p + 4), u32(d, p + 8), u32(d, p + 12)
        if w == 0 and hh == 0 and s == 0 and f == 0:
            frames.append((p - (oh - 16), 0, 0, None, 0))
            p += oh
            continue
        sig = sig_at(d, p)
        if sig is None:
            return frames, False, f'frame {i}: no signature at {p}'
        w, hh, bpp = sig
        px = p + 16
        if px + bpp * w * hh > len(d):
            return frames, False, f'frame {i}: pixels run past EOF'
        frames.append((p - (oh - 16), w, hh, px, bpp))
        p = px + bpp * w * hh + (oh - 16)
    return frames, True, ''


def dir_table(d, n_dirs, n_frames):
    """Validate the n_dirs 12-byte records at EOF.  Return (ok, [n...])."""
    if n_dirs <= 0 or len(d) < 12 * n_dirs:
        return False, []
    o = len(d) - 12 * n_dirs
    counts = []
    for i in range(n_dirs):
        n, a, b = u32(d, o), u32(d, o + 4), u32(d, o + 8)
        if a or b or not (0 < n <= 65535):
            return False, []
        counts.append(n)
        o += 12
    return sum(counts) == n_frames, counts


def finish(d, h, first_px, oh, tag):
    frames, ok, why = walk(d, first_px, oh, h['n_frames'])
    if not ok and h['n_frames'] > 1:
        # A few writers put the last (pixel-less) frame in the file-end pad
        # slot instead of a real record: 12 bytes of (w, h, 0) right before
        # the direction table (weaponr37261/37152/37257).  Parse the shorter
        # grid, then account for the trailing frame.
        f2, ok2, _ = walk(d, first_px, oh, h['n_frames'] - 1)
        if ok2:
            last_pre, lw, lh, lpx, lbpp = f2[-1]
            endx = last_pre + oh + (0 if lpx is None else lbpp * lw * lh)
            if endx + 12 == len(d) - 12 * h['n_dirs']:
                w, hh, s = u32(d, endx), u32(d, endx + 4), u32(d, endx + 8)
                if 0 < w <= 8192 and 0 < hh <= 8192 and s == 0:
                    frames = f2 + [(endx - oh, 0, 0, None, 0)]
                    ok = True
    if not ok:
        return None, f'{tag}: {why}'
    skipped = sum(1 for f in frames if f[3] is None)
    last_pre, lw, lh, lpx, lbpp = frames[-1]
    end = last_pre + oh + (0 if lpx is None else lbpp * lw * lh)
    tail = len(d) - end
    # measured rule (29/29 files, oh in 28..96):
    #   tail == 12*nDirs + (oh - 28)
    want_tail = 12 * h['n_dirs'] + (oh - 28)
    if tail != want_tail:
        return None, f'{tag}: tail {tail} != {want_tail} ' \
                     f'(12*{h["n_dirs"]}+{oh - 28})'
    d_ok, counts = dir_table(d, h['n_dirs'], h['n_frames'])
    note = ''
    if not d_ok:
        # Trailing no-pixel records can be padding that the direction table
        # does not count (npc191405 / npc304403 / npc488903 / npc61903).
        # Interior no-pixel records DO count: npc540201 has 8 of them in the
        # middle of its 115 frames and its table sums to all 115.
        trail = 0
        for f in reversed(frames):
            if f[3] is not None:
                break
            trail += 1
        if trail:
            d_ok, counts = dir_table(d, h['n_dirs'],
                                     h['n_frames'] - trail)
            if d_ok:
                note = (f'{trail} trailing no-pixel record(s) treated as '
                        f'padding (dir table sums to '
                        f'{h["n_frames"] - trail})')
    if not d_ok:
        # A few files carry an all-zero direction table (npc42102.gsn): the
        # slot exists but the writer never filled it in.  Accept those with an
        # empty mapping: the frames are still exact, we just lose the
        # frame -> direction assignment, so exporters fall back to flat names.
        o = len(d) - 12 * h['n_dirs']
        if o >= 0 and d[o:] == b'\0' * (12 * h['n_dirs']):
            d_ok, counts = True, []
            note = (f'dir table region ({12 * h["n_dirs"]} bytes) is all '
                    f'zeros: no frame->direction map, exported ungrouped')
    if not d_ok:
        return None, (f'{tag}: dir table bad (tail {tail} '
                      f'for {h["n_dirs"]} dirs)')
    bpps = sorted({f[4] for f in frames if f[3] is not None})
    return {
        'ok': True, 'header': h, 'tag': tag, 'first_px': first_px, 'oh': oh,
        'frames': frames, 'end': end, 'tail': tail, 'dir_note': note,
        'extra': tail - 12 * h['n_dirs'], 'dir_counts': counts,
        'skipped': skipped, 'bpps': bpps, 'bpp': bpps[0] if len(bpps) == 1 else 0,
        'px_bytes': sum(f[4] * f[1] * f[2] for f in frames if f[3] is not None),
    }, ''


def empty_file(d, h):
    """Whole-file parser for the "not a single pixel" variant.

    Some placeholders carry no image data at all: every record is a prefix
    slot plus a 16-byte slot that never holds a valid signature, the records
    are fixed size, and the file closes exactly on
    `start + n_frames*oh + 12*n_dirs`.  Measured on the 14 `face*`
    placeholders (320 B each = 60 + 5*40 + 60) and on the `npc` anchor
    tables (e.g. npc573201t.gsn 2532 = 100 + 60*40 + 72).
    """
    n, nd = h['n_frames'], h['n_dirs']
    if n <= 0 or nd <= 0:
        return None
    for start in (60, 76, 84, 88, 92, 100, 108, 124, 132, 140):
        for oh in (28, 32, 36, 40, 44, 48, 56, 64, 80, 96):
            if start + n * oh + 12 * nd != len(d):
                continue
            frames = []
            bad = False
            for i in range(n):
                pre = start + i * oh
                if sig_at(d, pre + oh - 16) or sig_at(d, pre + 16):
                    bad = True
                    break
                frames.append((pre, 0, 0, None, 0))
            if bad:
                continue
            # The size identity leaves literally no room for pixels, but only
            # trust it when the record region carries no signature at all
            # (cheap for the small placeholder files this variant consists of).
            if len(d) <= 20000:
                stop = len(d) - 12 * nd
                q = start
                while q + 16 <= stop:
                    if sig_at(d, q):
                        bad = True
                        break
                    q += 2
                if bad:
                    continue
            d_ok, counts = dir_table(d, nd, n)
            note = ('no pixel data in the whole file: %d record(s) at %d-byte '
                    'stride, all of them empty' % (n, oh))
            if not d_ok:
                counts = []
                note += '; direction table did not validate'
            tail = len(d) - (start + n * oh)
            return {
                'ok': True, 'header': h, 'tag': 'empty-records',
                'first_px': start, 'oh': oh, 'frames': frames,
                'end': start + n * oh, 'tail': tail, 'dir_note': note,
                'extra': tail - 12 * nd, 'dir_counts': counts,
                'skipped': n, 'bpps': [], 'bpp': 0, 'px_bytes': 0,
                'method': 'empty-records',
            }
    return None


def parse(d, brute=True):
    """Auto-detect layout.  Returns dict with ok / tried."""
    h = head(d)
    tried = []
    r = empty_file(d, h)
    if r:
        return r
    for first_px, oh, tag in hints(h):
        r, why = finish(d, h, first_px, oh, tag)
        if r:
            r['method'] = 'version-table'
            return r
        tried.append(why)

    if not brute:
        return {'ok': False, 'header': h, 'tried': tried}

    # Scan candidate first signatures, derive oh from the gap to the next
    # signature, and keep whatever validates end-to-end.
    n = h['n_frames']
    hits = []
    sigs = []
    p = 24
    limit = min(len(d), 24 + 4 * 260)
    while p + 16 <= limit:
        s = sig_at(d, p)
        if s:
            sigs.append((p, s[0], s[1]))
        p += 2
    for p0, w0, h0 in sigs:
        first_px = p0 + 16
        for oh in range(24, MAX_OH + 1, 4):
            r, why = finish(d, h, first_px, oh, f'brute p0={p0} oh={oh}')
            if r:
                r['method'] = 'brute'
                hits.append(r)
                break
    if not hits:
        return {'ok': False, 'header': h, 'tried': tried + ['brute: no hit']}
    hits.sort(key=lambda r: (r['oh'], r['first_px']))
    return hits[0]


def prefix_words(d, start, n):
    return [u32(d, start + 4 * i) for i in range(n)]


def pixel(d, o, alpha_high=True):
    b0, b1 = d[o], d[o + 1]
    if alpha_high:
        g, b, a, r = b0 >> 4, b0 & 15, b1 >> 4, b1 & 15
    else:
        g, b, a, r = b0 >> 4, b0 & 15, b1 & 15, b1 >> 4
    return (r * 17, g * 17, b * 17, a * 17)


# Channel layout of the 4-byte-per-pixel variant (sig flag == 2), as offsets
# into the pixel: the alpha byte is the fourth one (see DIMG-format.md).
BPP4_ORDER = (2, 1, 0, 3)          # (r, g, b, a) == BGRA in memory order


def pixel4(d, o, order=BPP4_ORDER):
    """4-byte pixel -> RGBA, 8 bit per channel."""
    r, g, b, a = order
    return (d[o + r], d[o + g], d[o + b], d[o + a])


def to_image(d, px_start, w, h, bpp=2, alpha_high=True):
    from PIL import Image
    img = Image.new('RGBA', (w, h))
    if bpp == 4:
        img.putdata([pixel4(d, px_start + 4 * i) for i in range(w * h)])
    else:
        img.putdata([pixel(d, px_start + 2 * i, alpha_high)
                     for i in range(w * h)])
    return img


def stats(d, px_start, w, h, bpp=2):
    n = w * h
    opaque = 0
    minx, miny, maxx, maxy = w, h, -1, -1
    for i in range(n):
        px = pixel4(d, px_start + 4 * i) if bpp == 4 else pixel(d, px_start + 2 * i)
        if px[3] > 0:
            opaque += 1
            x, y = i % w, i // w
            minx, maxx = min(minx, x), max(maxx, x)
            miny, maxy = min(miny, y), max(maxy, y)
    return opaque, (minx, miny, maxx, maxy)


def run(names, png_dir=None, csv_path=None, quiet=False, dump=False):
    good = bad = 0
    csv_rows = []
    for name in names:
        p = os.path.join(SRC, name)
        if not os.path.isfile(p):
            print(f'{name:22s} MISSING')
            bad += 1
            continue
        d = open(p, 'rb').read()
        r = parse(d)
        h = r['header']
        ver = f"{h['major']}.{h['minor']}.{h['n_dirs']}"
        if not r['ok']:
            print(f'{name:22s} FAIL v{ver} size={len(d)} '
                  f'frames={h["n_frames"]} dirs={h["n_dirs"]} | '
                  + ' ; '.join(r['tried'][:3]))
            bad += 1
            continue
        good += 1
        sizes = [(w, hh) for _, w, hh, _, _ in r['frames']]
        line = (f'{name:22s} OK   v{ver} size={len(d):>9} oh={r["oh"]:>3} '
                f'first_px={r["first_px"]:>4} tail={r["tail"]:>5} '
                f'extra={r["extra"]:>4} skip={r["skipped"]:>3} '
                f'bpp={r["bpp"]} dirs={r["dir_counts"]} frames={len(sizes)} '
                f'[{r["method"]}]')
        if not quiet:
            line += ' sizes=' + ','.join(f'{w}x{hh}' for w, hh in sizes[:6])
            if len(sizes) > 6:
                line += f'...(+{len(sizes)-6})'
        print(line)
        if dump:
            for i, (pre, w, hh, px, bpp) in enumerate(r['frames'][:8]):
                nw = (r['oh'] - 16) // 4
                print(f'{"":22s}   f{i}: prefix@{pre} '
                      f'{prefix_words(d, pre, nw)} sig@({w},{hh}) px@{px} bpp={bpp}')
        if csv_path is not None:
            for i, (pre, w, hh, px, bpp) in enumerate(r['frames']):
                csv_rows.append((name, i, w, hh, pre, r['oh'], px, bpp))
        if png_dir:
            os.makedirs(png_dir, exist_ok=True)
            stem = os.path.splitext(name)[0]
            for i, (_, w, hh, px, bpp) in enumerate(r['frames']):
                if px is None or w * hh > 4_000_000:
                    continue
                img = to_image(d, px, w, hh, bpp)
                img.save(os.path.join(png_dir, f'{stem}_{i}.png'))
            f0 = r['frames'][0]
            if f0[3] is not None:
                op, bbox = stats(d, f0[3], f0[1], f0[2], f0[4])
                print(f'{"":22s}      frame0: opaque={op}/{f0[1]*f0[2]} '
                      f'bbox={bbox}')
    if csv_path is not None:
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('file,index,w,h,prefix,oh,px,bpp\n')
            for row in csv_rows:
                f.write(','.join(str(x) for x in row) + '\n')
        print(f'wrote {len(csv_rows)} rows to {csv_path}')
    print(f'\n{good} ok, {bad} failed')
    return good, bad


def main():
    argv = sys.argv[1:]
    png = csv_path = None
    quiet = dump = False
    names = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--png':
            i += 1
            png = argv[i]
        elif a == '--csv':
            i += 1
            csv_path = argv[i]
        elif a == '--quiet':
            quiet = True
        elif a == '--dump':
            dump = True
        else:
            names.append(a)
        i += 1
    if not names:
        names = sorted(f for f in os.listdir(SRC) if f.endswith('.gsn'))[:25]
    run(names, png, csv_path, quiet, dump)


if __name__ == '__main__':
    main()
