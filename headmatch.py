"""Find NPC body files that share the same canvas as npc1000101 and compose the head
onto them in canvas space, so one rule can be checked across many samples.

Usage:
  python headmatch.py --scan                 # histogram of preamble canvases
  python headmatch.py --like npc1000101 --n 24
  python headmatch.py --sheet                # build out\canvas_sheet.png
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'
sys.path.insert(0, HERE)
import dimg  # noqa: E402
import combo  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def preamble(path):
    with open(path, 'rb') as f:
        b = f.read(108)
    if len(b) < 108:
        return None
    major, minor, ndirs, nframes = struct.unpack_from('<4H', b, 8)
    words = list(struct.unpack_from('<9I', b, 24))
    pref = list(struct.unpack_from('<4I', b, 60))
    return {'major': major, 'minor': minor, 'ndirs': ndirs, 'nf': nframes,
            'p': words, 'pref': pref, 'size': os.path.getsize(path)}


def sig_after(d, p=100):
    """First feasible 4-word signature at/after p (2B or 4B per pixel)."""
    import mmap
    n = 0
    while p + 16 <= len(d) and n < 1:
        w, hh, s, fl = struct.unpack_from('<4I', d, p)
        if fl in (1, 2) and 1 <= w <= 8192 and 1 <= hh <= 8192 and s == 2 * fl * w:
            return w, hh, 2 * fl
        p += 4
        n += 1
    return None, None, None


def scan():
    from collections import Counter
    c = Counter()
    names = sorted(x for x in os.listdir(SRC) if x.endswith('.gsn'))
    for nm in names:
        h = preamble(os.path.join(SRC, nm))
        if not h:
            continue
        W, H = h['p'][3], h['p'][4]
        c[(W, H, h['ndirs'], h['nf'])] += 1
    print('canvases (W,H,dirs,frames) -> count, top 25')
    for k, v in c.most_common(25):
        print('%5d  %s' % (v, k))
    return c


def like(name, n):
    base = preamble(os.path.join(SRC, name + '.gsn'))
    W, H = base['p'][3], base['p'][4]
    out = []
    for nm in sorted(os.listdir(SRC)):
        if not nm.endswith('.gsn') or nm == name + '.gsn':
            continue
        h = preamble(os.path.join(SRC, nm))
        if not h:
            continue
        if h['p'][3] == W and h['p'][4] == H and h['nf'] == base['nf'] and h['ndirs'] == base['ndirs']:
            out.append(nm[:-4])
    print('%d files with canvas %dx%d, %d frames, %d dirs' % (len(out), W, H, base['nf'], base['ndirs']))
    print(' '.join(out[:n]))
    return out


def main():
    a = sys.argv[1:]
    if '--scan' in a:
        scan()
    elif '--like' in a:
        like(a[a.index('--like') + 1], int(a[a.index('--n') + 1]) if '--n' in a else 30)
    elif '--sheet' in a:
        sheet(a)


def body_canvas(path, frame=0):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    if not r['ok']:
        return None
    oh = r['oh']
    h = preamble(path)
    words = h['p']
    bx, by = h['pref'][1], h['pref'][2]
    fr = r['frames'][frame]
    pre, w, hh, px, bpp = fr
    img = dimg.to_image(d, px, w, hh, bpp)
    return {'img': img, 'bx': bx, 'by': by, 'W': words[3], 'H': words[4],
            'cx': words[5], 'cy': words[6], 'w': w, 'h': hh, 'p': words}


def sheet(a):
    n = int(a[a.index('--n') + 1]) if '--n' in a else 16
    body = (a[a.index('--body') + 1] if '--body' in a else 'npc1000101')
    heads = sprite_cache = None  # noqa: F841
    hd = combo.sprite(combo.HEAD, 0)['img']
    hx_list = [int(v) for v in (a[a.index('--hx') + 1] if '--hx' in a else '12,13').split(',')]
    hy_list = [int(v) for v in (a[a.index('--hy') + 1] if '--hy' in a else '2,4,6,8').split(',')]

    names = [body] + [x for x in like(body, n + 1) if x != body][:n - 1]
    rows = []
    for nm in names:
        try:
            bc = body_canvas(os.path.join(SRC, nm + '.gsn'))
        except Exception as e:
            print('skip', nm, e)
            continue
        if not bc:
            print('skip(unparsed)', nm)
            continue
        rows.append((nm, bc))
    print('rows:', len(rows))

    zoom = 3
    cw, ch = rows[0][1]['W'] * zoom, rows[0][1]['H'] * zoom
    gx, gy = 8, 8
    cols = len(hx_list) * len(hy_list) + 1
    sheet_img = Image.new('RGBA', (6 + cols * (cw + gx), 26 + len(rows) * (ch + gy + 12)),
                          (28, 30, 34, 255))
    dr = ImageDraw.Draw(sheet_img)
    dr.text((6, 8), 'head canvas position on body canvas: hx=%s hy=%s  (col 0 = body only)'
            % (hx_list, hy_list), fill=(240, 244, 248))
    for ri, (nm, bc) in enumerate(rows):
        y = 26 + ri * (ch + gy + 12)
        # body only
        base = Image.new('RGBA', (bc['W'], bc['H']), (0, 0, 0, 0))
        base.paste(bc['img'], (bc['bx'], bc['by']), bc['img'])
        tiles = [(base, 'body')]
        for hy in hy_list:
            for hx in hx_list:
                im = base.copy()
                im.paste(hd, (hx, hy), hd)
                tiles.append((im, '%d,%d' % (hx, hy)))
        for ci, (im, lab) in enumerate(tiles):
            x = 6 + ci * (cw + gx)
            checker = Image.new('RGBA', (cw, ch), (52, 56, 62, 255))
            dc = ImageDraw.Draw(checker)
            for yy in range(0, ch, 12):
                for xx in range(0, cw, 12):
                    if ((xx // 12) + (yy // 12)) % 2:
                        dc.rectangle([xx, yy, xx + 11, yy + 11], fill=(74, 80, 88, 255))
            sheet_img.paste(checker, (x, y))
            big = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
            sheet_img.paste(big, (x, y), big)
            dr.text((x, y + ch + 1), lab, fill=(226, 232, 240))
        dr.text((6, y + ch + 1), nm, fill=(255, 210, 120))
    out = os.path.join(HERE, 'out', 'canvas_sheet.png')
    sheet_img.save(out)
    print('wrote', out, sheet_img.size)


if __name__ == '__main__':
    main()
