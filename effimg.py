"""Render .eff effect descriptors into a single composited image (in memory).

Same geometry rules as `effrender.py`, but the sprites are fetched through a
callable so the caller can read them from `objects*.pkg` instead of disk.

    from effimg import render, duration
    im, n = render(text, t=None, pct=0.4, provider=lambda stem: src_bytes('magic/' + stem))
"""
import math

from PIL import Image, ImageChops

import dimg
import eff
from effrender import lerp_keyframes

_SPR = {}


def _stem(name):
    stem = name
    if stem.startswith('magic'):
        digits = ''.join(ch for ch in stem if ch.isdigit())
        try:
            stem = 'magic%04d' % int(digits or 0)
        except ValueError:
            pass
    return stem


def sprite_geo(stem, provider, frame=0):
    """(image, pivot_x, pivot_y, additive?) of one magic sprite frame.

    The sprite carries its own canvas + pivot in the DIMG preamble
    (`W, H, cx, cy` at word 3..6).  Effects are anchored at that pivot, not at
    the image centre, so the pivot has to travel with the image.
    """
    key = (stem, frame)
    if key in _SPR:
        return _SPR[key]
    out = None
    try:
        d = provider(stem + '.gso')
    except Exception:
        d = None
    if d:
        try:
            r = dimg.parse(d, brute=True)
        except Exception:
            r = None
        if r and r.get('ok'):
            frames = [f for f in r['frames'] if f[3] is not None]
            if frames:
                f = frames[min(frame, len(frames) - 1)]
                try:
                    im = dimg.to_image(d, f[3], f[1], f[2], f[4])
                except Exception:
                    im = None
                if im is not None:
                    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
                    W, H, cx, cy = pw[3], pw[4], pw[5], pw[6]
                    # The sprite is only a piece of its canvas: the record
                    # prefix tells where it sits inside it (12-byte prefix,
                    # oh=28 -> (bx, by, 0)).  Pivot is in canvas coordinates.
                    pre_len = int(r.get('oh') or 0) - 16
                    bx = by = 0
                    try:
                        if pre_len == 12:
                            bx, by = dimg.u32(d, f[0]), dimg.u32(d, f[0] + 4)
                        elif pre_len == 80:
                            bx, by = dimg.u32(d, f[0] + 4), dimg.u32(d, f[0] + 8)
                    except Exception:
                        bx = by = 0
                    if 0 <= bx < 4096 and 0 <= by < 4096 and (bx or by):
                        cw = max(W, im.width + bx)
                        ch = max(H, im.height + by)
                        if 0 < cw <= 4096 and 0 < ch <= 4096:
                            canvas = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
                            canvas.alpha_composite(im, (bx, by))
                            im = canvas
                    # Anchor of the sprite inside its own canvas, normalised:
                    # x = centre of the image, y = 0 at the top edge and 1 at the
                    # bottom edge (cy / H, y growing downwards).
                    nx = 0.5
                    ny = (cy / float(H)) if H else 0.5
                    ny = min(1.0, max(0.0, ny))
                    out = (im, float(nx), float(ny), _black_frac(im) >= 0.35)
    _SPR[key] = out
    return out


def sprite(stem, provider, frame=0):
    """Backwards compatible: (image, additive?) without the pivot."""
    g = sprite_geo(stem, provider, frame)
    if g is None:
        return None
    return g[0], g[3]


_ADD = {}


def _black_frac(im):
    """Fraction of opaque pixels that are (near) black."""
    a = im.getchannel('A')
    rgb = im.convert('RGB')
    hist_a = a.histogram()
    opaque = sum(hist_a[250:])
    if opaque < 16:
        return 0.0
    black = 0
    for (rr, gg, bb), aa in zip(rgb.getdata(), a.getdata()):
        if aa >= 250 and rr < 12 and gg < 12 and bb < 12:
            black += 1
    return black / float(opaque)


def duration(text):
    """Longest keyframe time in ms (0 if unknown)."""
    tree = eff.parse(text)
    if tree is None:
        return 0
    times = []
    for _head, _name, kfs in eff.layers(tree):
        for k in kfs:
            if isinstance(k, list) and k and isinstance(k[0], (int, float)):
                times.append(k[0])
    return int(max(times)) if times else 0


def _layers(text):
    tree = eff.parse(text)
    if tree is None:
        return None
    return eff.layers(tree)

def readSprite(name, provider, imgs):
    if name in imgs:
        return imgs[name]
    g = sprite_geo(_stem(name), provider, 0)
    imgs[name] = g
    return g

def _items(layers, t, provider, max_layers=24, pivots=None):
    """Placed layer images: (image, x, y, anchor_x, anchor_y, additive).

    `pivots[i]` is the layer anchor in *normalised* coordinates: (0,0) is the
    top-left of the sprite image, (1,1) the bottom-right (value from the
    trailing list of the .eff descriptor).
    """
    items = []
    loadimgs = {}
    for idx, (head, name, kfs) in enumerate(layers[:max_layers]):
        g = readSprite(name, provider, loadimgs)
        if g is None:
            continue
        im0, _cx, _cy, additive = g
        # layer anchor, normalised: (0,0) = top-left of the image, (1,1) = bottom-right
        px_n, py_n = 0.5, 0.5
        if pivots and idx < len(pivots):
            pv = pivots[idx]
            if isinstance(pv, (list, tuple)) and len(pv) >= 2:
                try:
                    px_n, py_n = float(pv[0]), float(pv[1])
                except (TypeError, ValueError):
                    px_n, py_n = 0.5, 0.5
        ax0 = px_n * im0.width
        ay0 = py_n * im0.height
        # per-layer offset "(dx,dy)" is the 6th element of the layer head
        ox, oy = 0.0, 0.0
        if isinstance(head, list) and len(head) >= 6:
            cand = head[5]
            if isinstance(cand, list) and len(cand) >= 2:
                ox, oy = float(cand[0]), float(cand[1])
        body = lerp_keyframes(kfs, t) or [[0, 0, 0], [1, 1], 0, [255, 255, 255], 1]
        pos = body[0] if isinstance(body[0], list) else [0, 0, 0]
        scl = body[1] if isinstance(body[1], list) else [1, 1]
        rot = float(body[2]) if len(body) > 2 else 0.0
        col = body[3] if len(body) > 3 and isinstance(body[3], list) else [255, 255, 255]
        alpha = float(body[4]) if len(body) > 4 else 1.0

        sx = max(0.02, float(scl[0]))
        sy = max(0.02, float(scl[1]))
        w = max(1, int(round(im0.width * sx)))
        h = max(1, int(round(im0.height * sy)))
        im2 = im0.resize((w, h), Image.NEAREST)
        # anchor = canvas centre, scaled together with the image
        ax = ax0 * sx
        ay = ay0 * sy
        if abs(rot) > 0.01:
            # pad first so rotating about the anchor cannot clip the sprite
            m = int(abs(w * math.sin(math.radians(rot)))
                    + abs(h * math.cos(math.radians(rot))) + 4)
            pad = Image.new('RGBA', (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
            pad.alpha_composite(im2, (m, m))
            ax += m
            ay += m
            im2 = pad.rotate(-rot, resample=Image.BICUBIC, center=(ax, ay))
        r, g_, b = [int(c) for c in (list(col) + [255, 255, 255])[:3]]
        a = im2.getchannel('A').point(
            lambda v: int(v * max(0.0, min(1.0, alpha))))
        rgb = ImageChops.multiply(im2.convert('RGB'),
                                  Image.new('RGB', im2.size, (r, g_, b)))
        im2 = rgb.convert('RGBA')
        im2.putalpha(a)
        # pos = (x, y, z)：z 轴向上为正，屏幕 y 向下增长，所以取负号
        item = (im2, float(pos[0]) + ox, oy - float(pos[2]), ax, ay, additive)
        items.append(item)
    return items


def _box(items, pad=4):
    if not items:
        return None
    x0 = min(i[1] - i[3] for i in items)
    x1 = max(i[1] - i[3] + i[0].width for i in items)
    y0 = min(i[2] - i[4] for i in items)
    y1 = max(i[2] - i[4] + i[0].height for i in items)
    return (x0 - pad, y0 - pad, int(round(x1 - x0)) + pad * 2, int(round(y1 - y0)) + pad * 2)


_BOX = {}


def effect_box(text, provider, key=None, max_layers=24,
               fracs=(0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)):
    """Union of the frames' bounds, so every frame shares one canvas.

    Without a shared canvas each frame gets cropped to its own content, which
    cancels out the motion: everything looks frozen in the middle.
    """
    if key is not None and key in _BOX:
        return _BOX[key]
    layers = _layers(text)
    if not layers:
        return None
    pivots = _pivots(text, provider, max_layers)
    dur = duration(text)
    boxes = []
    for f in fracs:
        b = _box(_items(layers, dur * f, provider, max_layers, pivots))
        if b:
            boxes.append(b)
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    box = (x0, y0, int(round(x1 - x0)), int(round(y1 - y0)))
    if box[2] > 4000 or box[3] > 4000:
        box = None
    if key is not None:
        _BOX[key] = box
    return box

def _norm_pivot(x):
    """Tail entry -> normalised anchor y: 0 = centre of the top edge, 1 = bottom."""
    if isinstance(x, (list, tuple)):
        x = x[0] if x else 0
    try:
        v = float(x)
    except (TypeError, ValueError):
        v = 0.0
    return (v + 1.0) / 2.0


def _pivots(text, provider=None, max_layers=24):
    """Normalised anchor per layer, taken from the .eff tail list.

    x is always the horizontal centre; y comes from the tail entry, mapped so
    that 0 is the centre of the image's top edge and 1 the centre of its bottom
    edge.
    """
    tree = eff.parse(text)
    if tree is None:
        return []
    treeEnd = tree[-1]
    out = []
    for layerIndex in range(len(tree[1])):
        try:
            val = treeEnd[layerIndex]
        except Exception:
            val = treeEnd[-1] if treeEnd else 0
        out.append((0.5, _norm_pivot(val)))
    return out


def render(text, t=None, pct=0.4, provider=None, max_layers=24, box=None, pivots=None):
    if provider is None:
        return None, 0
    layers = _layers(text)
    if pivots is None:
        pivots = _pivots(text, provider, max_layers)
    if layers is None:
        return None, 0
    if t is None:
        t = duration(text) * pct
    items = _items(layers, t, provider, max_layers, pivots)
    if not items:
        return None, 0
    if box is None:
        box = _box(items)
    if box is None:
        return None, 0
    x0, y0, W, H = box
    if W > 4000 or H > 4000 or W < 1 or H < 1:
        return None, 0
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for im, px, py, ax, ay, additive in items:
        ox = int(round(px - ax - x0))
        oy = int(round(py - ay - y0))
        if not additive:
            out.alpha_composite(im, (ox, oy))
            continue
        # additive (glow) layer: black adds nothing, so no black box appears.
        # The layer's own alpha is meaningless here (glow textures are fully
        # opaque with black baked in); derive alpha from the light it adds.
        tmp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        tmp.alpha_composite(im, (ox, oy))
        a = tmp.getchannel('A')
        rgb = ImageChops.multiply(tmp.convert('RGB'), Image.merge('RGB', (a, a, a)))
        rgb = rgb.point(lambda v: min(255, v * 3 // 2))
        light = rgb.convert('L').point(lambda v: min(255, v * 2))
        out = Image.merge('RGBA', (
            ImageChops.add(out.getchannel('R'), rgb.getchannel('R')),
            ImageChops.add(out.getchannel('G'), rgb.getchannel('G')),
            ImageChops.add(out.getchannel('B'), rgb.getchannel('B')),
            ImageChops.add(out.getchannel('A'), light)))
    return out, len(items)


# how many time samples the viewer shows for one .eff
FRACS = (0.10, 0.25, 0.40, 0.55, 0.70, 0.85)


def blank(im, thr=0.002, min_px=64):
    """True if the image has (almost) no visible pixel at all.

    画布大小随锚点/包围盒变化很大，所以同时用「绝对像素数」兜底：只有可见
    像素少于 `min_px` 个、且占比也很低时，才算空。
    """
    if im is None:
        return True
    h = im.getchannel('A').histogram()
    total = float(im.width * im.height) or 1.0
    visible = sum(h[8:])
    return visible < min_px and (visible / total) < thr
