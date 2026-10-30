"""Compose one body + one head into a single character image, using the calibrated rule.

  python mix.py [--n 24] [--heads head0101,head2151,head0251,head1151] [--dir 1]

Rule (from the five calibrated reference views):
  * paint order: body first, then the head on top;
  * the head sprite is placed so that its pivot sits 8 px below the top edge of the
    body sprite, horizontally centred on the body's top contour.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'
OUT = os.path.join(HERE, 'out')
DST = os.path.join(OUT, 'mix')
PIVOT_DROP = 8          # head pivot, measured down from the body sprite's top edge
XSHIFT = 4              # residual of the shoulder-line fit (see top_center)


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def read_preamble(d):
    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    return dict(W=pw[3], H=pw[4], cx=pw[5], cy=pw[6])


def body_frame(path, frame=0):
    d = open(path, 'rb').read()
    r = dimg.parse(d)
    if not r.get('ok'):
        return None
    pre, w, h, px, bpp = r['frames'][frame]
    if px is None:
        return None
    im = dimg.to_image(d, px, w, h, bpp).convert('RGBA')
    return dict(img=im, nframes=len(r['frames']), geo=read_preamble(d))


def head_pic(path, dirno=1):
    d = open(path, 'rb').read()
    recs, extra, k = headtool.segment(d)
    if not recs:
        return None
    single = len(recs) <= 5
    idx = (dirno - 1) if single else 2 * (dirno - 1)
    if idx >= len(recs):
        idx = 0
    p, w, h, s, f = recs[idx]
    im = dimg.to_image(d, p + 16, w, h, s // w).convert('RGBA')
    return dict(img=im, geo=read_preamble(d), nrec=len(recs))


def top_center(img):
    """Neck x of a body sprite: centre of the widest row in the upper part.

    Fitted against the five pixel-exact ground truths of npc1000101 + head2151:
    the shoulder line is the steadiest anchor (mean |err| 4.3 px, max 7 px),
    clearly better than the topmost row (mean 6.7, max 15) because hair tips,
    weapons and raised arms stick out above the shoulders.  XSHIFT is the
    constant residual of that fit (+4 px puts the head back over the neck).
    """
    a = np.asarray(img)[:, :, 3] > 128
    ys = np.nonzero(a.any(axis=1))[0]
    if not len(ys):
        return img.width / 2.0 + XSHIFT
    y0 = int(ys[0])
    y1 = min(a.shape[0], y0 + max(1, int(round(a.shape[0] * 0.4))) + 1)
    best = None
    for y in range(y0, y1):
        xs = np.nonzero(a[y])[0]
        if not len(xs):
            continue
        w = int(xs.max()) - int(xs.min()) + 1
        if best is None or w > best[0]:
            best = (w, (float(xs.min()) + float(xs.max()) + 1.0) / 2.0)
    if best is None:
        return img.width / 2.0 + XSHIFT
    return best[1] + XSHIFT


def top_run_center(img):
    """Centre of the topmost opaque run (the neck stub of a humanoid)."""
    a = np.asarray(img)[:, :, 3] > 128
    ys = np.nonzero(a.any(axis=1))[0]
    if not len(ys):
        return img.width / 2.0
    xs = np.nonzero(a[ys[0]])[0]
    return (float(xs.min()) + float(xs.max()) + 1.0) / 2.0


def compose(body, head):
    himg = head['img']
    hgeo = head['geo']
    bx, by = 0, 0
    bw, bh = body.width, body.height
    tx = top_center(body)
    hx0 = int(round(tx - hgeo['cx']))
    hy = int(PIVOT_DROP - hgeo['cy'])
    # guarantee vertical contact: the head must reach into the body, else it
    # floats above a sprite whose opaque area starts lower than expected
    ha = np.asarray(himg)[:, :, 3] > 128
    ba = np.asarray(body)[:, :, 3] > 128
    if ha.any() and ba.any():
        htop = int(np.nonzero(ha.any(axis=1))[0][0])
        hbot = int(np.nonzero(ha.any(axis=1))[0][-1])
        btop = int(np.nonzero(ba.any(axis=1))[0][0])
        if hy + hbot < btop + 2:
            hy = btop + 2 - hbot
    hx = hx0
    if ha.any() and ba.any() and hy + hbot >= btop:
        def overlap(cand):
            ov = 0
            for yy in range(max(0, hy), min(ba.shape[0], hy + ha.shape[0])):
                xs = np.nonzero(ha[yy - hy])[0]
                if not len(xs):
                    continue
                bx0 = xs + cand
                ok = (bx0 >= 0) & (bx0 < ba.shape[1])
                if ok.any():
                    ov += int(ba[yy, bx0[ok]].sum())
            return ov

        # the shoulder fit is only overruled when it leaves the head hanging in
        # empty space (no contact at all) -- then slide over the body and take
        # the place with the most overlap
        if overlap(hx0) < 3:
            best = None
            for cand in range(hx0 - 24, hx0 + 25):
                ov = overlap(cand)
                if best is None or ov > best[0] or (ov == best[0]
                                                    and abs(cand - hx0) < abs(best[1] - hx0)):
                    best = (ov, cand)
            if best and best[0] > 0:
                hx = best[1]
    x0 = min(0, hx)
    y0 = min(0, hy)
    x1 = max(bw, hx + himg.width)
    y1 = max(bh, hy + himg.height)
    pad = 2
    out = Image.new('RGBA', (x1 - x0 + pad * 2, y1 - y0 + pad * 2), (0, 0, 0, 0))
    out.alpha_composite(body, (bx - x0 + pad, by - y0 + pad))
    out.alpha_composite(himg, (hx - x0 + pad, hy - y0 + pad))
    return out, (hx - bx, hy - by)


def top_width(img):
    """Width of the sprite's topmost opaque run (the neck stub, for a person)."""
    a = np.asarray(img)[:, :, 3] > 128
    ys = np.nonzero(a.any(axis=1))[0]
    if not len(ys):
        return 10 ** 6
    xs = np.nonzero(a[ys[0]])[0]
    return int(xs.max()) - int(xs.min()) + 1


def pick_bodies(n):
    """Pick humanoid bodies: a narrow neck stub and a sane sprite size.

    Monsters, props (chests, trees, statues) and scenery start wide or are very
    large, so they make no sense as a head target.  We sample the npc folder
    with an even stride and keep the first n bodies that pass the shape test.
    """
    d = os.path.join(SRC, 'npc')
    names = sorted(f[:-4] for f in os.listdir(d) if f.endswith('.gsn'))
    step = max(1, len(names) // max(1, n * 6))
    cand = names[::step]
    keep = []
    for nm in cand:
        if len(keep) >= n:
            break
        try:
            b = body_frame(os.path.join(d, nm + '.gsn'), 0)
        except Exception:                      # noqa: BLE001
            continue
        if not b:
            continue
        im = b['img']
        if not (24 <= im.height <= 260 and 16 <= im.width <= 200):
            continue
        if top_width(im) > 24:
            continue
        # props and monsters are wide; humanoids are clearly taller than wide
        if im.height < 1.25 * im.width:
            continue
        keep.append((nm, b))
    print('picked %d bodies from %d candidates' % (len(keep), len(cand)))
    return keep


def main():
    a = sys.argv[1:]
    def opt(k, dflt):
        return a[a.index(k) + 1] if k in a else dflt
    n = int(opt('--n', '24'))
    heads = opt('--heads', 'head0101,head2151,head0251,head1151').split(',')
    only = [x.strip() for x in opt('--bodies', '').split(',') if x.strip()]
    dno = int(opt('--dir', '1'))
    os.makedirs(DST, exist_ok=True)
    if only:
        bodies = []
        for nm in only:
            b = body_frame(os.path.join(SRC, 'npc', nm + '.gsn'), 0)
            if b:
                bodies.append((nm, b))
        print('using %d explicit bodies' % len(bodies))
    else:
        bodies = pick_bodies(n)
    hp = [os.path.join(SRC, 'head', h.strip() + '.gsn') for h in heads]
    hp = [p for p in hp if os.path.exists(p)]
    tiles = []
    for bn, b in bodies:
        for p in hp:
            h = head_pic(p, dno)
            if not h:
                continue
            im, dxy = compose(b['img'], h)
            name = '%s_%s_d%d.png' % (bn, os.path.basename(p)[:-4], dno)
            im.save(os.path.join(DST, name))
            tiles.append((name, im, dxy))
            print('%-46s body %2dx%-2d + head %2dx%-2d  head offset (%+d,%+d)'
                  % (name, b['img'].width, b['img'].height, h['img'].width, h['img'].height, dxy[0], dxy[1]))
    if not tiles:
        print('nothing produced')
        return
    cols, rows_per_page = 12, 8
    cw, ch = 132, 176          # fixed cell, sprite scaled to fit
    per_page = cols * rows_per_page
    pages = (len(tiles) + per_page - 1) // per_page
    made = []
    for pg in range(pages):
        chunk = tiles[pg * per_page:(pg + 1) * per_page]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * cw, rows * ch), (26, 27, 32))
        dr = ImageDraw.Draw(sheet)
        for i, (name, im, dxy) in enumerate(chunk):
            cx = (i % cols) * cw
            cy = (i // cols) * ch
            box_w, box_h = cw - 8, ch - 26
            sc = min(box_w / im.width, box_h / im.height, 4.0)
            tw, th = max(1, int(im.width * sc)), max(1, int(im.height * sc))
            cell = Image.new('RGB', (tw, th), (40, 42, 49))
            cell.paste(im.convert('RGB'), (0, 0), im)
            sheet.paste(cell, (cx + (cw - tw) // 2, cy + 18 + (box_h - th) // 2))
            dr.text((cx + 3, cy + 3), name[:-4][:22], fill=(190, 197, 210))
        dst = os.path.join(OUT, 'mix_sheet-%d.png' % (pg + 1))
        sheet.save(dst)
        made.append((dst, sheet.size))
    for dst, size in made:
        print('sheet %s (%dx%d)' % (esc(dst), size[0], size[1]))
    print('tiles %d -> %s   %d sheet page(s)'
          % (len(tiles), esc(DST), len(made)))


if __name__ == '__main__':
    main()
