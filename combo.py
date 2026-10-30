"""Guess how a head sprite is attached to an npc body sprite.

Every candidate placement is derived from a field in the .gsn data (preamble words,
record prefix words) or from the alpha silhouette -- never from eyeballed numbers.
Each candidate is written as its own PNG plus one labelled contact sheet.

    python combo.py                        # body npc1000101 f0 x head0101 d1
    python combo.py --body FILE --head FILE --dir 1 --frame 0
"""
import os
import struct
import sys

from PIL import Image, ImageDraw

import dimg
import paths

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = paths.sub('data/official/avatar')
BODY = os.path.join(SRC, 'npc', 'npc1000101.gsn')
HEAD = os.path.join(SRC, 'head', 'head0101.gsn')
OUT = os.path.join(HERE, 'out', 'combo2')


def w32(d, off, n):
    return [struct.unpack_from('<i', d, off + 4 * j)[0] for j in range(n)]


def recursive_records(path):
    """Decode all frames of a file as (w, h, bpp, px_offset, rec_index)."""
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    out = []
    if r.get('ok'):
        for pre, w, hh, px, bpp in r['frames']:
            if px is None:
                continue
            out.append((w, hh, bpp, px))
        return d, out, r
    import headtool
    recs, extra, k = headtool.segment(d)
    for (p, w, hh, stride, flag) in recs:
        out.append((w, hh, stride // w, p + 16))
    return d, out, {'frames': [], 'head_family': True, 'recs': recs, 'extra': extra, 'k': k,
                    'first_px': 92, 'oh': 0, 'dir_counts': []}


def sprite(path, frame_sel=None):
    """Decode one record of a .gsn as an RGBA image + its prefix words."""
    d, recs, r = recursive_records(path)
    h = dimg.head(d)
    idx = 0 if frame_sel is None else min(frame_sel, len(recs) - 1)
    w, hh, bpp, px = recs[idx]
    img = dimg.to_image(d, px, w, hh, bpp)
    pref = w32(d, 60, 4)                      # first record's prefix follows the preamble
    pref_all = []
    if not r.get('head_family'):
        oh = r.get('oh', 0) or 0
        for i, fr in enumerate(r.get('frames') or []):
            nw = 4 if i == 0 else max(1, (oh - 16) // 4)
            pref_all.append(w32(d, fr[0], nw))
    return {
        'img': img, 'w': w, 'h': hh, 'bpp': bpp, 'dirs': r.get('dir_counts', []),
        'oh': r.get('oh', 0), 'fp': r.get('first_px', 92), 'ver': (h['major'], h['minor']),
        'preamble': w32(d, 24, 9), 'first_pref': pref, 'pref': pref, 'pref_all': pref_all,
        'nf': len(recs), 'head_family': bool(r.get('head_family')),
    }


def silhouette(img):
    """bbox + per-row extents of the opaque area."""
    px = img.load()
    xs, ys = [], []
    for y in range(img.height):
        for x in range(img.width):
            if px[x, y][3] > 8:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    rows = {}
    for x, y in zip(xs, ys):
        a, b = rows.get(y, (x, x))
        rows[y] = (min(a, x), max(b, x))
    return {'x0': min(xs), 'x1': max(xs), 'y0': min(ys), 'y1': max(ys), 'rows': rows}


def compose(body, head, head_scale=1.0, origin=None, bg='tile'):
    """Place head top-left at `origin` (float px, may be negative) over body."""
    if head_scale != 1.0:
        head = head.resize((max(1, int(round(head.width * head_scale))),
                            max(1, int(round(head.height * head_scale)))), Image.NEAREST)
    ox, oy = 0 if origin is None else origin
    dx, dy = int(round(ox)), int(round(oy))
    left = min(0, dx)
    top = min(0, dy)
    right = max(body.width, dx + head.width)
    bottom = max(body.height, dy + head.height)
    w, h = right - left, bottom - top
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    canvas.paste(body, (-left, -top), body)
    canvas.paste(head, (dx - left, dy - top), head)
    return canvas, (dx, dy, left, top)


def checker(w, h, s=10):
    img = Image.new('RGBA', (w, h), (52, 56, 62, 255))
    dr = ImageDraw.Draw(img)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if ((x // s) + (y // s)) % 2:
                dr.rectangle([x, y, x + s - 1, y + s - 1], fill=(74, 80, 88, 255))
    return img


def main():
    a = sys.argv[1:]
    body_path = a[a.index('--body') + 1] if '--body' in a else BODY
    head_path = a[a.index('--head') + 1] if '--head' in a else HEAD
    want_dir = int(a[a.index('--dir') + 1]) if '--dir' in a else 1
    b = sprite(body_path, 0)
    # head dir N colour record = 2*(N-1); the mask record follows it
    h = sprite(head_path, 2 * (want_dir - 1))
    mask = sprite(head_path, 2 * (want_dir - 1) + 1) if h['head_family'] else None
    os.makedirs(OUT, exist_ok=True)

    print('BODY %s  %dx%d  ver %d.%d  dirs=%s  oh=%d' % (os.path.basename(body_path), b['w'], b['h'],
                                                         b['ver'][0], b['ver'][1], b['dirs'], b['oh']))
    print('     preamble   %s' % (b['preamble'],))
    print('     first pref %s' % (b['first_pref'],))
    print('HEAD %s  %dx%d  ver %d.%d  dirs=%s  oh=%d' % (os.path.basename(head_path), h['w'], h['h'],
                                                         h['ver'][0], h['ver'][1], h['dirs'], h['oh']))
    print('     preamble   %s' % (h['preamble'],))
    print('     first pref %s' % (h['first_pref'],))
    if mask:
        print('     mask %dx%d pref %s' % (mask['w'], mask['h'], mask['first_pref']))

    bW, bH, bax, bay = b['preamble'][3], b['preamble'][4], b['preamble'][5], b['preamble'][6]
    hW, hH, hax, hay = h['preamble'][3], h['preamble'][4], h['preamble'][5], h['preamble'][6]
    bs, hs = silhouette(b['img']), silhouette(h['img'])
    print('     body silhouette x %d..%d y %d..%d' % (bs['x0'], bs['x1'], bs['y0'], bs['y1']))
    print('     head silhouette x %d..%d y %d..%d' % (hs['x0'], hs['x1'], hs['y0'], hs['y1']))

    bp, hp = b['first_pref'], h['first_pref']
    mp = mask['first_pref'] if mask else [0, 0, 0, 0]

    cands = []
    # 1. preamble anchor coincidence (p5,p6 of both preambles)
    cands.append(('P1 preamble-anchor', bax - hax, bay - hay, 1.0,
                  '(%d,%d)-(%d,%d)' % (bax, bay, hax, hay)))
    # 2. canvas bottom, horizontally centred
    cands.append(('C2 canvas-bottom', (bW - hW) // 2, bH - hH, 1.0,
                  '((%d-%d)/2, %d-%d)' % (bW, hW, bH, hH)))
    # 3. canvas top, horizontally centred
    cands.append(('C3 canvas-top', (bW - hW) // 2, 0, 1.0, '((%d-%d)/2, 0)' % (bW, hW)))
    # 4. first-record prefix words (w0,w1) coincidence
    cands.append(('R4 prefix-w0w1', bp[0] - hp[0], bp[1] - hp[1], 1.0,
                  '(%d,%d)-(%d,%d)' % (bp[0], bp[1], hp[0], hp[1])))
    # 5. body preamble anchor x vs head mask anchor
    cands.append(('X5 preg-x+mask-y', bax - mp[0], bay - mp[1], 1.0,
                  '(%d,%d)-(%d,%d)' % (bax, bay, mp[0], mp[1])))
    # 6. silhouette: head bottom-centre onto body top-centre
    hbx = (hs['x0'] + hs['x1']) // 2
    row0 = bs['rows'][bs['y0']]
    bcx = (row0[0] + row0[1]) // 2
    cands.append(('S6 silhouette-top', bcx - hbx, bs['y0'] - hs['y1'] - 1, 1.0,
                  'bodytop y=%d, headbottom y=%d' % (bs['y0'], hs['y1'])))
    # 7-9. same two most plausible rules with the head rescaled
    cands.append(('P1 x0.5', (bax - hax * 0.5), (bay - hay * 0.5), 0.5, 'anchor @50%'))
    cands.append(('C2 x0.5', (bW - hW * 0.5) / 2, bH - hH * 0.5, 0.5, 'canvas @50%'))
    cands.append(('P1 x2.0', (bax - hax * 2), (bay - hay * 2), 2.0, 'anchor @200%'))
    # 10. body per-frame prefix word0/word1 (x,y of that frame) as the head attach point
    pa = b.get('pref_all') or []
    if len(pa) > 1 and len(pa[1]) >= 2:
        cands.append(('F7 frame-pivot', pa[1][0] - hax, pa[1][1] - hay, 1.0,
                      'body f1 pref (%d,%d)-(%d,%d)' % (pa[1][0], pa[1][1], hax, hay)))

    zoom = 3
    tiles = []
    for name, dx, dy, sc, note in cands:
        img, used = compose(b['img'], h['img'], sc, (dx, dy))
        tiles.append((name, used, sc, note, img))
        img.save(os.path.join(OUT, '%s.png' % name.replace(' ', '_').replace('.', 'p')))
        print('  %-20s offset=(%+d,%+d) scale=%.2f  %s' % (name, used[0], used[1], sc, note))

    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    tw = max(t[4].width for t in tiles) * zoom
    th = max(t[4].height for t in tiles) * zoom
    gapx, gapy = 14, 30
    sheet = Image.new('RGBA', (12 + cols * (tw + gapx), 30 + rows * (th + gapy)), (30, 32, 36, 255))
    dr = ImageDraw.Draw(sheet)
    dr.text((10, 9), 'body %s f0  +  head %s d%d   (each tile: offset from a data field)'
            % (os.path.basename(body_path), os.path.basename(head_path), want_dir), fill=(240, 244, 248))
    for i, (name, used, sc, note, img) in enumerate(tiles):
        r, col = divmod(i, cols)
        x = 12 + col * (tw + gapx)
        y = 30 + r * (th + gapy)
        bg = checker(img.width * zoom, img.height * zoom, 10)
        sheet.paste(bg, (x, y))
        big = img.resize((img.width * zoom, img.height * zoom), Image.NEAREST)
        sheet.paste(big, (x, y), big)
        dr.text((x, y + th + 2), '%d. %s  (%+d,%+d) x%.2f' % (i + 1, name, used[0], used[1], sc),
                fill=(236, 240, 246))
        dr.text((x, y + th + 14), '%s   sprite %dx%d -> %dx%d' % (note, img.width, img.height,
                                                                 img.width, img.height), fill=(168, 176, 186))
    out = os.path.join(HERE, 'out', 'combo_sheet.png')
    sheet.save(out)
    print('wrote', out, sheet.size)


if __name__ == '__main__':
    main()
