"""内存直读查看器：不落盘解码，HTTP 上按需从原始资源文件解码并返回 PNG / 表格 JSON。

启动：python viewer2.py [--port 8794]
页面：http://127.0.0.1:8794/
"""
import argparse
import csv
import io
import json
import os
import posixpath
import struct
import threading
import time
import urllib.parse
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image

import dimg
import effimg
import gsa
import headtool
import maps
import pkg
import tile
import zipbin
import zipbinnames

DATA = r'F:\WG自由幻想\自由幻想\data'
HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS_CSV = os.path.join(HERE, 'out', 'zipbin_fields.csv')

IMAGE_EXT = {'.gsn', '.gso', '.gsa', '.til', '.dat', '.tga', '.bmp', '.png', '.jpg', '.jpeg', '.eff', '.map'}
TABLE_EXT = {'.bin'}


# ---------------------------------------------------------------- 文件与路径
def safe(rel):
    rel = rel.replace('\\', '/').strip('/')
    p = os.path.normpath(os.path.join(DATA, rel))
    if not p.startswith(os.path.normpath(DATA)):
        raise ValueError('path escape')
    return p


def listdir(rel):
    p = safe(rel)
    dirs, files = [], []
    if os.path.isdir(p):
        with os.scandir(p) as it:
            for e in it:
                if e.is_dir():
                    dirs.append(e.name)
                else:
                    files.append({'n': e.name, 's': e.stat().st_size})
    # pkg 里的资源（key 是相对 official\ 的路径）
    key = pkg_key(rel)
    if key is not None:
        prefix = (key + '/') if key else ''
        pd, pf = set(), []
        for k, (pp, e) in pkg_index().items():
            if not k.startswith(prefix):
                continue
            rest = k[len(prefix):]
            if not rest:
                continue
            if '/' in rest:
                pd.add(rest.split('/', 1)[0])
            else:
                pf.append({'n': rest, 's': e['raw'], 'p': 1})
        dirs = sorted(set(dirs) | pd, key=str.lower)
        files += pf
    if not dirs and not files:
        raise FileNotFoundError(rel)
    dirs.sort(key=lambda s: s.lower())
    files.sort(key=lambda d: d['n'].lower())
    return {'path': rel, 'dirs': dirs, 'files': files}


# ---------------------------------------------------------------- pkg 内存索引
_PKG_IDX = None
_PKG_PATHS = []
_PKG_LOCK = threading.Lock()


def pkg_index():
    global _PKG_IDX
    if _PKG_IDX is None:
        with _PKG_LOCK:
            if _PKG_IDX is None:
                idx = {}
                paths = []
                for path, ver, k, err in pkg.catalog():
                    paths.append(path)
                    pi = len(paths) - 1
                    for j in range(k.count):
                        idx[k.key_at(j)] = (pi, j)
                _PKG_PATHS[:] = paths
                _PKG_IDX = idx
    return _PKG_IDX


def pkg_key(rel):
    """official/avatar/head/x.gsn -> avatar/head/x.gsn；也接受已是 pkg 相对的路径。"""
    r = rel.replace('\\', '/').strip('/').lower()
    if r == 'official':
        return ''
    if r.startswith('official/'):
        return r[9:]
    return r


def pkg_hit(rel):
    key = pkg_key(rel)
    if key is None:
        return None
    hit = pkg_index().get(key)
    if not hit:
        return None
    pi, j = hit
    path = _PKG_PATHS[pi]
    try:
        return (path, j)
    except Exception:            # noqa: BLE001
        return None


def src_bytes(rel):
    """读原始字节：磁盘优先，其次 pkg（都在内存里）。"""
    p = safe(rel)
    if os.path.isfile(p):
        with open(p, 'rb') as f:
            return f.read()
    hit = pkg_hit(rel)
    if hit is None:
        raise FileNotFoundError(rel)
    return pkg.pkg(hit[0]).read_entry(hit[1])


_MAGIC = OrderedDict()
_MAGIC_MAX = 96          # 只缓存最近用到的精灵字节，避免把整库 magic 读进内存


def magic_bytes(fname):
    """.eff 里引用的精灵（`magic144` → pkg `magic/magic0144.gso`）的字节。"""
    hit = _MAGIC.get(fname)
    if hit is not None:
        _MAGIC.move_to_end(fname)
        return hit
    d = None
    for rel in ('magic/' + fname, 'magic/magic/' + fname):
        try:
            d = src_bytes(rel)
            break
        except Exception:
            continue
    if d is None:
        try:
            hit = pkg.find(fname)
            if hit:
                d = pkg.pkg(hit[0]).read_at(hit[1])
        except Exception:
            d = None
    _MAGIC[fname] = d
    while len(_MAGIC) > _MAGIC_MAX:
        _MAGIC.popitem(last=False)
    return d


# ---------------------------------------------------------------- 分类 / 分页
_CATS = None


def cats():
    """顶层分类：avatar 下按部件（backpack/cap/...），其余按 official 子目录。"""
    global _CATS
    if _CATS is None:
        agg = {}
        for k in pkg_index():
            parts = k.split('/')
            if parts[0] == 'avatar' and len(parts) > 1:
                key = 'avatar/' + parts[1]
            elif parts[0]:
                key = parts[0]
            else:
                continue
            agg[key] = agg.get(key, 0) + 1
        _CATS = [{'k': k, 'n': k.split('/')[-1], 'c': v} for k, v in sorted(agg.items())]
        # map 目录里的 .gsm/.msk/.npc 不是图片，改成「地图」虚拟分类：
        # 用 res/sketchmap 的示意图做底图，叠 .msk 碰撞格与 .lst 怪物点。
        n_map = len(maps.stems_with_sketch())
        _CATS = [{'k': 'map!', 'n': 'map', 'c': n_map}] + [c for c in _CATS if c['k'] != 'map']
    return _CATS


def _iter_files(rel):
    """(相对路径, 字节数)：pkg 索引 + 磁盘目录。"""
    if rel.startswith('map!'):
        for name in maps.stems_with_sketch():
            yield name + '.map', 0
        return
    key = pkg_key(rel)
    if key is not None:
        prefix = (key + '/') if key else ''
        ent = pkg_index()
        for k, hit in ent.items():
            if k.startswith(prefix):
                sub = k[len(prefix):]
                if not sub:
                    continue
                try:
                    sz = pkg.pkg(_PKG_PATHS[hit[0]]).raw_at(hit[1])
                except Exception:        # noqa: BLE001
                    sz = 0
                yield sub, sz
    p = safe(rel)
    if os.path.isdir(p):
        for dirpath, _dn, filenames in os.walk(p):
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                sub = os.path.relpath(fp, p).replace('\\', '/')
                try:
                    sz = os.path.getsize(fp)
                except OSError:
                    sz = 0
                yield sub, sz


def full_path(rel, name):
    """列表条目 → 可直接传给 /api/img / /api/info 的相对路径。"""
    if not rel:
        return name
    if rel.endswith('!'):            # 虚拟分类：条目名不带前缀，补上 rel 本身（如 map!qw0001.map）
        return rel + name
    return rel.rstrip('/') + '/' + name


def files_page(rel, kind='img', page=0, size=200, q=''):
    allowed = IMAGE_EXT if kind == 'img' else (TABLE_EXT if kind == 'bin' else None)
    rows, seen = [], set()
    ql = q.lower()
    bl = eff_blank_set() if 'effect' in (pkg_key(rel) or rel) else set()
    for sub, sz in _iter_files(rel):
        if sub in seen:
            continue
        seen.add(sub)
        if allowed is not None and os.path.splitext(sub)[1].lower() not in allowed:
            continue
        if bl and sub in bl:
            continue
        if ql:
            title = maps.display_name(sub[:-4]).lower() if rel == 'map!' else ''
            if ql not in sub.lower() and ql not in title:
                continue
        row = {'n': sub, 's': sz, 'p': full_path(rel, sub)}
        if rel == 'map!':
            row['t'] = maps.display_name(sub[:-4])
        rows.append(row)
    rows.sort(key=lambda d: d['n'].lower())
    total = len(rows)
    pages = max(1, (total + size - 1) // size)
    page = max(0, min(page, pages - 1))
    return {'path': rel, 'kind': kind, 'total': total, 'pages': pages, 'page': page,
            'size': size, 'files': rows[page * size:(page + 1) * size]}


_PAGE_HTML = None


def page_html():
    global _PAGE_HTML
    if _PAGE_HTML is None:
        f = os.path.join(HERE, 'page2.html')
        if os.path.isfile(f):
            with open(f, encoding='utf-8') as fh:
                _PAGE_HTML = fh.read()
        else:
            _PAGE_HTML = PAGE
    return _PAGE_HTML


# ---------------------------------------------------------------- 各容器解码
def _png(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


_IMG_CACHE = OrderedDict()
_IMG_CACHE_MAX = 240
_IMG_CACHE_BYTES = 0
_IMG_CACHE_BUDGET = 96 * 1024 * 1024      # 96 MB 上限，防止大图把内存吃光
_IMG_CACHE_ITEM_MAX = 2 * 1024 * 1024     # 单张超过 2 MB 不缓存
_EFF_THUMBS = {}          # (rel, i, max) -> PNG bytes，特效缩略图专用、不淘汰
_MAP_IMG = OrderedDict()  # (name, w, col, mon, npc) -> 地图大图 PNG
_INFO_CACHE = OrderedDict()

_EFF_BLANK = {}          # rel -> True/False（整条特效在采样时刻是否全透明）
_EFF_PROBE = (0.25, 0.50, 0.75)
_EFF_BLANK_SET = None


def eff_blank_set():
    """out/eff_blank.json 里预计算出的「全空特效」文件名集合（effscan.py 生成）。"""
    global _EFF_BLANK_SET
    if _EFF_BLANK_SET is None:
        p = os.path.join(HERE, 'out', 'eff_blank.json')
        s = set()
        try:
            with open(p, encoding='utf-8') as fh:
                s = set(json.load(fh).get('blank') or [])
        except Exception:       # noqa: BLE001
            s = set()
        _EFF_BLANK_SET = s
    return _EFF_BLANK_SET


_EFF_BOX_FILE = os.path.join(HERE, 'out', 'eff_box.json')
_EFF_BOXES = None
_FULL_FRACS = (0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)
_CHEAP_FRACS = (0.0, 0.35, 0.7, 1.0)


def eff_boxes():
    """out/eff_box.json：每条特效的共享画布（effboxes.py 预计算）。"""
    global _EFF_BOXES
    if _EFF_BOXES is None:
        try:
            with open(_EFF_BOX_FILE, encoding='utf-8') as fh:
                _EFF_BOXES = json.load(fh)
        except Exception:       # noqa: BLE001
            _EFF_BOXES = {}
    return _EFF_BOXES


def eff_box_of(rel, txt, cheap=False):
    """特效的共享画布：内存缓存 → out/eff_box.json → 现算（缩略图用少量采样）。"""
    mem = effimg._BOX
    if rel in mem:
        return mem[rel]
    hit = eff_boxes().get(rel)
    if hit:
        box = tuple(hit)
        mem[rel] = box
        return box
    fr = _CHEAP_FRACS if cheap else _FULL_FRACS
    return effimg.effect_box(txt, magic_bytes, key=rel, fracs=fr)


def eff_blank(rel):
    """整条 .eff 在采样时刻是否完全没有可见像素（用于「空特效不显示」）。"""
    hit = _EFF_BLANK.get(rel)
    if hit is not None:
        return hit
    txt = src_bytes(rel).decode('gbk', 'replace')
    ms = effimg.duration(txt)
    blank = True
    for frac in _EFF_PROBE:
        try:
            im, _n = effimg.render(txt, t=ms * frac, provider=magic_bytes)
        except Exception:       # noqa: BLE001
            im = None
        if im is not None and not effimg.blank(im):
            blank = False
            break
    _EFF_BLANK[rel] = blank
    return blank


def map_name(rel):
    """`map!qw0001.map` -> `qw0001`。"""
    return rel[4:].rsplit('.', 1)[0] if rel.startswith('map!') else rel


def map_img(rel, w=1400, col=True, mon=True, npc=True):
    """地图大图：示意图 + 碰撞格 + 怪物/NPC 点（带 LRU）。"""
    name = map_name(rel)
    key = (name, int(w), bool(col), bool(mon), bool(npc))
    hit = _MAP_IMG.get(key)
    if hit is not None:
        return hit
    im = maps.render(name, width=int(w), collision=bool(col), mon=bool(mon), npc_pts=bool(npc))
    if im is None:
        raise LookupError('map has no sketch image')
    body = _png(im)
    _MAP_IMG[key] = body
    while len(_MAP_IMG) > 24:
        _MAP_IMG.popitem(last=False)
    return body


def img_bytes(rel, i, mx):
    """PNG 字节（只解第 i 帧，带 LRU 缓存）。"""
    global _IMG_CACHE_BYTES
    if rel.startswith('map!'):
        name = map_name(rel)
        key = ('mapthumb', name, mx)
        hit = _IMG_CACHE.get(key)
        if hit is not None:
            return hit
        im = maps.sketch(name)
        if im is None:
            raise LookupError('map has no sketch image')
        im = im.convert('RGBA')
        if mx > 0 and max(im.width, im.height) > mx:
            im = im.copy()
            im.thumbnail((mx, mx), Image.NEAREST)
        body = _png(im)
        _IMG_CACHE[key] = body
        _IMG_CACHE_BYTES += len(body)
        return body
    ext = _ext(rel)
    is_eff = ext in ('.eff', '.eff_')
    if is_eff and 0 < mx <= 256:
        # effect thumbnails are expensive to build and there are ~1.5k of them,
        # so keep them in a dedicated (uncapped) dict that the warm-up thread
        # can fill in the background
        key2 = (rel, i, mx)
        hit = _EFF_THUMBS.get(key2)
        if hit is not None:
            return hit
        body = _img_bytes_cached(rel, i, mx)
        _EFF_THUMBS[key2] = body
        while len(_EFF_THUMBS) > 600:
            _EFF_THUMBS.pop(next(iter(_EFF_THUMBS)))
        return body
    return _img_bytes_cached(rel, i, mx)


def _img_bytes_cached(rel, i, mx):
    key = (rel, i, mx)
    hit = _IMG_CACHE.get(key)
    if hit is not None:
        _IMG_CACHE.move_to_end(key)
        return hit
    if _ext(rel) in ('.eff', '.eff_') and eff_blank(rel):
        raise LookupError('empty effect (no visible pixel at any sampled time)')
    im = frame_image(rel, i, mx)
    if im is None:
        raise LookupError('no such frame')
    if _ext(rel) in ('.eff', '.eff_') and effimg.blank(im):
        raise LookupError('empty effect frame')
    if mx > 0 and max(im.width, im.height) > mx:
        im = im.copy()
        im.thumbnail((mx, mx), Image.NEAREST)
    body = _png(im)
    if len(body) <= _IMG_CACHE_ITEM_MAX:
        global _IMG_CACHE_BYTES
        old = _IMG_CACHE.pop(key, None)
        if old is not None:
            _IMG_CACHE_BYTES -= len(old)
        _IMG_CACHE[key] = body
        _IMG_CACHE_BYTES += len(body)
        while _IMG_CACHE and (len(_IMG_CACHE) > _IMG_CACHE_MAX
                              or _IMG_CACHE_BYTES > _IMG_CACHE_BUDGET):
            _k, _v = _IMG_CACHE.popitem(last=False)
            _IMG_CACHE_BYTES -= len(_v)
    return body


def _ext(rel):
    return os.path.splitext(rel)[1].lower()


def info_of(rel):
    """只读结构、不解像素（元数据，带 LRU 缓存）。"""
    hit = _INFO_CACHE.get(rel)
    if hit is not None:
        _INFO_CACHE.move_to_end(rel)
        return dict(hit)
    info = _info_of(rel)
    _INFO_CACHE[rel] = dict(info)
    while len(_INFO_CACHE) > 600:
        _INFO_CACHE.popitem(last=False)
    return info


def _info_of(rel):
    ext = _ext(rel)
    if rel.startswith('map!'):
        name = map_name(rel)
        mi = maps.info(name)
        return {'bytes': 0, 'ext': '.map', 'kind': 'map', 'name': name, 'frames': 1,
                'title': maps.display_name(name),
                'fit': maps.fit(name),
                'world': [mi['w'], mi['h']], 'cells': mi['cells'], 'cell': mi['cell'],
                'sketch': mi['sketch'], 'monsters': mi['monsters'], 'npcs': mi['npcs']}
    d = src_bytes(rel)
    info = {'bytes': len(d), 'ext': ext,
            'origin': 'disk' if os.path.isfile(safe(rel)) else 'pkg'}
    if ext in ('.gsn', '.gso'):
        r = dimg.parse(d, brute=True)
        if r.get('ok'):
            info.update(kind='gsn', version=f"{r['header']['major']}.{r['header']['minor']}",
                        frames=len(r['frames']), skipped=r.get('skipped'), bpp=r.get('bpp'),
                        oh=r.get('oh'), dirs=r.get('dir_counts'), method=r.get('method'))
            return info
        recs, _extra, _k = headtool.segment(d)
        if not recs:
            raise ValueError(r.get('err', 'cannot parse'))
        hh = dimg.head(d)
        info.update(kind='head', version=f"{hh['major']}.{hh['minor']}", frames=len(recs),
                    bpp=max(1, recs[0][3] // max(1, recs[0][1])), note='headtool.segment')
        return info
    if ext == '.gsa':
        hd = gsa.parse(d)
        if not hd:
            raise ValueError('bad gsa header')
        info.update(kind='gsa', frames=hd['frames'], bpp=hd['bpp'], w=hd['bw'], h=hd['bh'],
                    tiles=hd['n_tiles'])
        return info
    if ext == '.til':
        n = struct.unpack_from('<I', d, 12)[0]
        info.update(kind='til', frames=n, entries=n, version=struct.unpack_from('<I', d, 8)[0],
                    w=128, h=128)
        return info
    if ext == '.dat':
        if d[:8] != b'QQ  TILE':
            raise ValueError('not a tileimg .dat (magic %s)' % d[:8].hex())
        n = struct.unpack_from('<I', d, 28)[0]
        info.update(kind='tileimg', frames=n, entries=n, w=64, h=64)
        return info
    if ext in ('.tga', '.bmp', '.png', '.jpg', '.jpeg'):
        im = Image.open(io.BytesIO(d))
        im.load()
        info.update(kind='image', frames=1, w=im.width, h=im.height)
        return info
    if ext in ('.eff', '.eff_'):
        txt = d.decode('gbk', 'replace')
        ms = effimg.duration(txt)
        layers = 0
        try:
            import eff as _eff
            tree = _eff.parse(txt)
            layers = len(_eff.layers(tree)) if tree is not None else 0
        except Exception:
            layers = 0
        info.update(kind='eff', frames=len(effimg.FRACS), w=0, h=0,
                    duration=ms, layers=layers, blank=eff_blank(rel),
                    note='合成预览：按关键帧时间采样的 %d 帧' % len(effimg.FRACS))
        return info
    raise ValueError('unsupported ' + ext)


def frame_image(rel, i, mx=0):
    """只解第 i 帧（不构造其它帧）。"""
    ext = _ext(rel)
    d = src_bytes(rel)
    if ext in ('.gsn', '.gso'):
        r = dimg.parse(d, brute=True)
        if r.get('ok'):
            fr = r['frames']
            if not 0 <= i < len(fr):
                raise LookupError('frame')
            _pre, w, h, px, bpp = fr[i]
            return None if px is None else dimg.to_image(d, px, w, h, bpp)
        recs, _extra, _k = headtool.segment(d)
        if not recs or not 0 <= i < len(recs):
            raise LookupError('frame')
        p, w, h, stride, _flag = recs[i]
        return dimg.to_image(d, p + 16, w, h, max(1, stride // max(1, w)))
    if ext == '.gsa':
        hd = gsa.parse(d)
        if not hd:
            raise ValueError('bad gsa header')
        ts = gsa.tiles(d, hd)
        nx = max(1, -(-hd['bw'] // hd['cw']))
        ny = max(1, -(-hd['bh'] // hd['ch']))
        per = nx * ny
        chunk = ts[i * per:(i + 1) * per]
        if not chunk:
            raise LookupError('frame')
        if per == 1:
            return gsa.to_image(d, chunk[0])
        cw, ch = hd['cw'], hd['ch']
        canvas = Image.new('RGBA', (nx * cw, ny * ch), (0, 0, 0, 0))
        for k, e in enumerate(chunk):
            canvas.alpha_composite(gsa.to_image(d, e), ((k % nx) * cw, (k // nx) * ch))
        return canvas.crop((0, 0, min(hd['bw'], nx * cw), min(hd['bh'], ny * ch)))
    if ext == '.til':
        n = struct.unpack_from('<I', d, 12)[0]
        hdr = len(d) - n * tile.TIL_ENTRY
        if not 0 <= i < n:
            raise LookupError('frame')
        return tile.rgba(d, hdr + i * tile.TIL_ENTRY, 128, 128)
    if ext == '.dat':
        if d[:8] != b'QQ  TILE':
            raise ValueError('not a tileimg .dat')
        n = struct.unpack_from('<I', d, 28)[0]
        if not 0 <= i < n:
            raise LookupError('frame')
        return tile.rgba(d, 64 + i * tile.IMG_ENTRY, 64, 64)
    if ext in ('.tga', '.bmp', '.png', '.jpg', '.jpeg'):
        im = Image.open(io.BytesIO(d))
        im.load()
        return im.convert('RGBA')
    if ext in ('.eff', '.eff_'):
        txt = d.decode('gbk', 'replace')
        ms = effimg.duration(txt)
        fr = effimg.FRACS
        if not 0 <= i < len(fr):
            raise LookupError('frame')
        thumb = 0 < mx <= 256
        # all frames of one effect share a canvas, otherwise every frame is
        # re-centred on its own content and the motion disappears
        box = eff_box_of(rel, txt, cheap=thumb)
        scale = 1.0
        if thumb and box:
            # thumbnails: composite on a canvas that is roughly mx px, instead
            # of rendering the full-size effect and shrinking afterwards
            big = max(box[2], box[3]) or 1
            if big > mx * 1.6:
                scale = max(0.05, (mx * 1.6) / big)
        # a grid thumbnail of frame 0 (10% of the duration) is usually still
        # invisible, so previews are taken at 40% instead
        frac = 0.40 if (thumb and i == 0) else fr[i]
        im, _n = effimg.render(txt, t=ms * frac, provider=magic_bytes, box=box,
                               scale=scale)
        if im is None:
            raise LookupError('cannot render effect')
        if thumb:
            # 缩略图裁到可见内容：有些特效的并集包围盒极大（如 1221×1102），
            # 直接缩小后主体只剩几个像素
            bb = im.getbbox()
            if bb:
                im = im.crop(bb)
            if im.width and im.height and max(im.size) < mx * 0.9:
                # 内容太小就在缩略图里放大填满卡片（只在缩略图里这么做）
                k = mx / float(max(im.size))
                im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))),
                               Image.NEAREST)
        return im
    raise ValueError('unsupported ' + ext)


def frames_of(rel, ext):
    """返回 (frames[list[PIL]], info dict)。字节来自磁盘或 pkg 内存。"""
    d = src_bytes(rel)
    info = {'bytes': len(d), 'ext': ext, 'origin': 'disk' if os.path.isfile(safe(rel)) else 'pkg'}
    if ext in ('.gsn', '.gso'):
        r = dimg.parse(d, brute=True)
        if r.get('ok'):
            fr = r['frames']
            info.update(kind='gsn', version=f"{r['header']['major']}.{r['header']['minor']}",
                        frames=len(fr), skipped=r.get('skipped'), bpp=r.get('bpp'),
                        oh=r.get('oh'), dirs=r.get('dir_counts'), method=r.get('method'))
            imgs = []
            for pre, w, h, px, bpp in fr:
                if px is None:
                    imgs.append(None)
                else:
                    imgs.append(dimg.to_image(d, px, w, h, bpp))
            return imgs, info
        recs, extra, k = headtool.segment(d)
        if not recs:
            raise ValueError(r.get('err', 'cannot parse'))
        hh = dimg.head(d)
        info.update(kind='head', version=f"{hh['major']}.{hh['minor']}", frames=len(recs),
                    bpp=max(1, recs[0][3] // max(1, recs[0][1])), note='headtool.segment')
        imgs = []
        for p, w, h, stride, flag in recs:
            bpp = max(1, stride // max(1, w))
            imgs.append(dimg.to_image(d, p + 16, w, h, bpp))
        return imgs, info
    if ext == '.gsa':
        h = gsa.parse(d)
        if not h:
            raise ValueError('bad gsa header')
        imgs = gsa.frames(d, h)
        info.update(kind='gsa', frames=len(imgs), bpp=h['bpp'],
                    w=h['bw'], h=h['bh'], tiles=h['n_tiles'])
        return imgs, info
    if ext == '.til':
        meta = tile.til_data(d, rel)
        imgs = meta['entries']
        info.update(kind='til', frames=len(imgs), version=meta['ver'], entries=meta['n'],
                    w=128, h=128)
        return imgs, info
    if ext == '.dat':
        meta = tile.tileimg_data(d, rel)
        imgs = meta['entries']
        info.update(kind='tileimg', frames=len(imgs), entries=meta['n'], w=64, h=64)
        return imgs, info
    if ext in ('.tga', '.bmp', '.png', '.jpg', '.jpeg'):
        im = Image.open(io.BytesIO(d))
        im.load()
        info.update(kind='image', frames=1, w=im.width, h=im.height)
        return [im.convert('RGBA')], info
    raise ValueError('unsupported ' + ext)


# ---------------------------------------------------------------- 表格
_fld = None


def fields():
    """表名 -> [(offset, size, kind, field)]；优先读 out/fields_cache.json（mkfields.py 生成）。"""
    global _fld
    if _fld is None:
        cache = os.path.join(HERE, 'out', 'fields_cache.json')
        if os.path.isfile(cache):
            try:
                with open(cache, encoding='utf-8') as f:
                    fm = json.load(f)
                _fld = {os.path.basename(k.replace('\\', '/')): [tuple(x) for x in v]
                        for k, v in fm.items()}
                return _fld
            except Exception:                   # noqa: BLE001
                pass
        try:
            widths = {}
            for k, (pi, j) in pkg_index().items():
                if k.startswith('zipbin/') and k.endswith('.bin'):
                    try:
                        d = pkg.pkg(_PKG_PATHS[pi]).read_at(j)
                        widths[os.path.basename(k)] = struct.unpack_from('<I', d, 8)[0]
                    except Exception:           # noqa: BLE001
                        pass
            fm = zipbinnames.fieldmap(widths)
            _fld = {os.path.basename(k.replace('\\', '/')): v for k, v in fm.items()}
        except Exception:                       # noqa: BLE001
            _fld = {}
    return _fld


def columns_for(name, width):
    named = sorted(fields().get(name, []), key=lambda t: t[0])
    seen = {}
    cols, pos = [], 0
    for item in named:
        off, size = item[0], item[1]
        field = item[-1] or f'x{off}'
        if off < pos or off + size > width:
            continue
        if field in seen:
            field = f'{field}@{off}'
        seen[field] = off
        if off > pos:
            cols.append((pos, off - pos, f'x{pos}'))
        cols.append((off, size, field))
        pos = off + size
    if pos < width:
        step = 4 if width - pos >= 4 else 1
        while pos < width:
            n = min(step, width - pos)
            cols.append((pos, n, f'x{pos}'))
            pos += n
    return cols


def table_json(rel, limit):
    name = os.path.basename(rel)
    d = src_bytes(rel)
    if len(d) < 4 or struct.unpack_from('<I', d, 0)[0] != 0x5566:
        info = {'kind': 'raw', 'bytes': len(d), 'head': d[:32].hex(' ')}
        return {'info': info, 'columns': [], 'rows': []}
    t = zipbin.read_bytes(d, rel)
    cols = columns_for(name, t['width'])
    rows = []
    for i, row in enumerate(t['rows'][:limit]):
        out = [i]
        for off, size, field in cols:
            chunk = row[off:off + size]
            if field.startswith('s') or size > 8:
                try:
                    out.append(chunk.decode('gbk').strip('\x00').strip())
                except Exception:
                    out.append(chunk.hex())
            elif size == 1:
                out.append(chunk[0])
            elif size == 2:
                out.append(int.from_bytes(chunk, 'little'))
            elif size == 4:
                out.append(struct.unpack('<I', chunk)[0])
            else:
                out.append(chunk.hex())
        rows.append(out)
    info = {'kind': 'table', 'bytes': len(d), 'width': t['width'], 'count': t['count'],
            'named': sum(1 for c in cols if not c[2].startswith('x')),
            'limit': min(limit, t['count'])}
    return {'info': info, 'columns': ['row'] + [c[2] for c in cols], 'rows': rows}


# ---------------------------------------------------------------- HTTP
class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode('utf-8'),
                   'application/json; charset=utf-8')

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path in ('/', '/index.html'):
                return self._send(200, page_html().encode('utf-8'), 'text/html; charset=utf-8')
            if u.path == '/api/cats':
                return self._json(cats())
            if u.path == '/api/files':
                rel = q.get('p', [''])[0]
                kind = q.get('kind', ['img'])[0]
                page = int(q.get('page', ['0'])[0])
                size = max(1, min(2000, int(q.get('size', ['200'])[0])))
                return self._json(files_page(rel, kind, page, size, q.get('q', [''])[0]))
            if u.path == '/api/list':
                return self._json(listdir(q.get('p', [''])[0]))
            if u.path == '/api/info':
                rel = q.get('p', [''])[0]
                ext = os.path.splitext(rel)[1].lower()
                if ext in TABLE_EXT:
                    d = src_bytes(rel)
                    t = zipbin.read_bytes(d, rel)
                    return self._json({'kind': 'table', 'bytes': len(d),
                                       'width': t['width'], 'count': t['count'], 'ext': ext})
                return self._json(info_of(rel))
            if u.path == '/api/mapimg':
                rel = q.get('p', [''])[0]
                w = max(64, min(4096, int(q.get('w', ['1400'])[0])))
                col = q.get('col', ['1'])[0] not in ('0', '', 'false')
                mon = q.get('mon', ['1'])[0] not in ('0', '', 'false')
                npc = q.get('npc', ['1'])[0] not in ('0', '', 'false')
                try:
                    return self._send(200, map_img(rel, w, col, mon, npc), 'image/png')
                except LookupError as exc:
                    return self._send(404, str(exc).encode('utf-8'), 'text/plain')
                except Exception as exc:    # noqa: BLE001
                    return self._send(404, ('cannot render: %s: %s'
                                           % (type(exc).__name__, exc)).encode('utf-8'),
                                      'text/plain')
            if u.path == '/api/img':
                rel = q.get('p', [''])[0]
                i = int(q.get('i', ['0'])[0])
                mx = int(q.get('max', ['0'])[0])
                try:
                    body = img_bytes(rel, i, mx)
                except LookupError:
                    return self._send(404, b'no such frame', 'text/plain')
                except Exception as exc:        # noqa: BLE001
                    return self._send(404, ('cannot decode: %s: %s' % (type(exc).__name__, exc)).encode('utf-8'), 'text/plain')
                return self._send(200, body, 'image/png')
            if u.path == '/api/maplist':
                name = map_name(q.get('p', [''])[0])
                mi = maps.info(name)
                mi['title'] = maps.display_name(name)
                return self._json({'name': name, 'info': mi,
                                   'groups': maps.monster_groups(name),
                                   'monsters': maps.monsters(name),
                                   'npcs': maps.npcs(name)})
            if u.path == '/api/mapmask':
                name = map_name(q.get('p', [''])[0])
                w = max(64, min(4000, int(q.get('w', ['900'])[0])))
                try:
                    im = maps.mask_image(name, w)
                except Exception:                # noqa: BLE001
                    im = None
                if im is None:
                    return self._send(404, b'no mask', 'text/plain')
                buf = io.BytesIO()
                im.save(buf, 'PNG', optimize=False, compress_level=6)
                return self._send(200, buf.getvalue(), 'image/png')
            if u.path == '/api/table':
                rel = q.get('p', [''])[0]
                limit = int(q.get('limit', ['300'])[0])
                return self._json(table_json(rel, limit))
            if u.path == '/api/text':
                rel = q.get('p', [''])[0]
                limit = max(1, min(2000000, int(q.get('limit', ['200000'])[0])))
                d = src_bytes(rel)
                body = d[:limit]
                txt = None
                for enc_ in ('utf-8', 'gbk', 'latin-1'):
                    try:
                        txt = body.decode(enc_)
                        break
                    except UnicodeDecodeError:
                        continue
                return self._json({'kind': 'text', 'bytes': len(d), 'shown': len(body),
                                   'text': txt if txt is not None else body.hex(' ')})
            if u.path.startswith('/raw/'):
                rel = urllib.parse.unquote(u.path[5:])
                body = src_bytes(rel)
                return self._send(200, body, 'application/octet-stream')
            self._send(404, b'not found', 'text/plain')
        except Exception as e:
            self._json({'error': f'{type(e).__name__}: {e}'}, 500)


PAGE = r"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>资源内存直读查看器</title>
<style>
:root{--bg:#191b20;--fg:#dfe3ea;--dim:#8d94a3;--acc:#5aa9ff;--line:#2b2f38;--card:#22262e}
*{box-sizing:border-box}
body{margin:0;font:13px/1.5 "Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--fg);height:100vh;display:flex;flex-direction:column}
header{display:flex;gap:10px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--line)}
header b{color:var(--acc);font-weight:600}
#crumb{color:var(--dim);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
main{flex:1;display:flex;min-height:0}
#tree{width:320px;border-right:1px solid var(--line);overflow:auto;padding:4px 0}
#side{flex:1;overflow:auto;padding:10px}
.dir{padding:2px 8px;cursor:pointer;color:#cfd6e3;white-space:nowrap}
.dir:hover{background:#232833}
.dir.open{color:var(--acc)}
.file{padding:2px 8px 2px 22px;cursor:pointer;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.file:hover{background:#232833;color:var(--fg)}
.file.sel{background:#2d3a4d;color:#fff}
#thumbs{display:flex;flex-wrap:wrap;gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px;width:150px}
.card img{width:100%;image-rendering:pixelated;background:
  repeating-conic-gradient(#2a2e36 0 25%,#24272e 0 50%) 0 0/16px 16px;border-radius:3px}
.card .lbl{font-size:11px;color:var(--dim);margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#meta{padding:8px 0;color:var(--dim);font-family:ui-monospace,Consolas,monospace;font-size:12px;white-space:pre-wrap}
table{border-collapse:collapse;font-family:ui-monospace,Consolas,monospace;font-size:12px}
th,td{border:1px solid var(--line);padding:2px 6px;text-align:left;max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
th{position:sticky;top:0;background:#2a2f39;color:var(--acc);cursor:pointer}
tr:nth-child(even) td{background:#1f232b}
#zoom{position:fixed;inset:0;background:#000d;display:none;align-items:center;justify-content:center;flex-direction:column;gap:8px}
#zoom img{max-width:92vw;max-height:86vh;image-rendering:pixelated;background:
  repeating-conic-gradient(#2a2e36 0 25%,#24272e 0 50%) 0 0/16px 16px}
.err{color:#ff8f8f}
</style></head><body>
<header><b>资源直读</b><span id="crumb">/</span>
<span id="stat" style="color:#8d94a3"></span></header>
<main><div id="tree"></div><div id="side"><div id="meta">选择左侧目录或文件</div><div id="thumbs"></div></div></main>
<div id="zoom"><img id="zimg"><div id="zcap" style="color:#bbb;font-size:12px"></div></div>
<script>
const $=s=>document.querySelector(s);
let curDir='', curFile='';
const IMGEXT=new Set(['gsn','gso','gsa','til','dat','tga','bmp','png','jpg','jpeg']);

function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}

async function api(u){const r=await fetch(u);if(!r.ok)throw new Error(r.status);return r.json()}

function node(label,path,isDir,depth){
  const el=document.createElement('div');
  el.className=isDir?'dir':'file';
  el.textContent=label; el.style.paddingLeft=(8+depth*12)+'px';
  el.onclick=()=>isDir?openDir(path,el):openFile(path);
  return el;
}

let container=null;
async function openDir(path,el){
  if(container&&container.dataset.path===path&&container.dataset.open==='1'){
    container.dataset.open='0';container.querySelectorAll(':scope>div').forEach(n=>n.remove());
    el.classList.remove('open');return;
  }
  $('#thumbs').innerHTML='';$('#meta').textContent='加载中…';
  let d;try{d=await api('/api/list?p='+encodeURIComponent(path))}catch(e){$('#meta').textContent='读取失败 '+e;return}
  curDir=path; $('#crumb').textContent='/'+path;
  if(el){el.classList.add('open');}
  const host=el?el:document.createElement('div');
  if(!el){$('#tree').innerHTML='';host.className='dir';host.dataset.path='';$('#tree').appendChild(host)}
  // 清空旧子节点
  [...host.querySelectorAll(':scope>div')].forEach(n=>n.remove());
  host.dataset.path=path;host.dataset.open='1';
  container=host;
  const depth=(path.split('/').filter(Boolean).length)||0;
  d.dirs.forEach(n=>host.appendChild(node(n+'/',path?path+'/'+n:n,true,depth+1)));
  const MAXN=400;
  d.files.slice(0,MAXN).forEach(f=>host.appendChild(node(f.n,path?path+'/'+f.n:f.n,false,depth+1)));
  if(d.files.length>MAXN){
    const more=document.createElement('div');more.className='file';more.style.opacity=.55;
    more.textContent=`… 还有 ${d.files.length-MAXN} 个文件（右侧缩略图里翻）`;
    host.appendChild(more);
  }
  $('#stat').textContent=`${d.dirs.length} 目录 / ${d.files.length} 文件`;
  renderThumbs(path,d.files);
}

function renderThumbs(path,files){
  const box=$('#thumbs');box.innerHTML='';
  const imgs=files.filter(f=>IMGEXT.has(f.n.split('.').pop().toLowerCase()));
  const bins=files.filter(f=>f.n.toLowerCase().endsWith('.bin'));
  $('#meta').textContent=`图片文件 ${imgs.length} 个`+(bins.length?` · 表格 ${bins.length} 个`:'');
  let shown=0;
  const more=document.createElement('div');
  more.style.display='none';more.style.cursor='pointer';more.style.gridColumn='1/-1';
  more.style.padding='8px';more.style.background='#2b2f38';more.style.borderRadius='4px';
  more.style.textAlign='center';more.style.color='#9fb4d0';
  more.onclick=()=>fill(300);
  function card(f){
    const p=path?path+'/'+f.n:f.n;
    const c=document.createElement('div');c.className='card';
    const im=document.createElement('img');im.loading='lazy';
    im.src='/api/img?p='+encodeURIComponent(p)+'&i=0';
    im.onerror=()=>{im.style.display='none';c.querySelector('.lbl').classList.add('err')};
    im.onclick=()=>zoom(im.src,p);
    const l=document.createElement('div');l.className='lbl';l.textContent=f.n;
    l.title=f.n+'  '+(f.s|0)+' B';
    c.append(im,l);return c;
  }
  function fill(n){
    imgs.slice(shown,shown+n).forEach(f=>box.insertBefore(card(f),more));
    shown=Math.min(imgs.length,shown+n);
    more.textContent=`显示更多（还剩 ${imgs.length-shown}）`;
    more.style.display=shown<imgs.length?'block':'none';
  }
  box.appendChild(more);
  fill(300);
  bins.slice(0,200).forEach(f=>{
    const p=path?path+'/'+f.n:f.n;
    const c=document.createElement('div');c.className='card';
    const l=document.createElement('div');l.className='lbl';l.textContent='▦ '+f.n;
    c.append(l);c.onclick=()=>openFile(p);box.appendChild(c);
  });
}

async function openFile(path){
  curFile=path; $('#crumb').textContent='/'+path;
  $('#thumbs').innerHTML='';
  const ext=path.split('.').pop().toLowerCase();
  if(ext==='bin')return openTable(path);
  $('#meta').textContent='解码中…';
  let info;try{info=await api('/api/info?p='+encodeURIComponent(path))}catch(e){$('#meta').textContent='解析失败';return}
  const rows=Object.entries(info).map(([k,v])=>k+' = '+JSON.stringify(v)).join('\n');
  $('#meta').textContent=rows;
  const n=info.frames|0;const box=$('#thumbs');
  for(let i=0;i<n;i++){
    const c=document.createElement('div');c.className='card';
    const im=document.createElement('img');im.loading='lazy';
    im.src='/api/img?p='+encodeURIComponent(path)+'&i='+i;
    im.onclick=()=>zoom(im.src,path+' #'+i);
    const l=document.createElement('div');l.className='lbl';l.textContent='帧 '+i;
    c.append(im,l);box.appendChild(c);
  }
}

async function openTable(path){
  $('#meta').textContent='读取表格…';
  let t;try{t=await api('/api/table?p='+encodeURIComponent(path)+'&limit=300')}catch(e){$('#meta').textContent='读取失败';return}
  $('#meta').textContent=Object.entries(t.info).map(([k,v])=>k+' = '+JSON.stringify(v)).join('\n');
  if(!t.columns.length)return;
  const tb=document.createElement('table');
  const tr=document.createElement('tr');
  t.columns.forEach(c=>{const th=document.createElement('th');th.textContent=c;tr.appendChild(th)});
  const thead=document.createElement('thead');thead.appendChild(tr);tb.appendChild(thead);
  const body=document.createElement('tbody');
  t.rows.forEach(r=>{const x=document.createElement('tr');
    r.forEach(v=>{const td=document.createElement('td');td.textContent=v;x.appendChild(td)});body.appendChild(x)});
  tb.appendChild(body);
  const wrap=document.createElement('div');wrap.style.overflow='auto';wrap.style.maxHeight='calc(100vh - 160px)';
  wrap.appendChild(tb);$('#thumbs').appendChild(wrap);
}

function zoom(src,cap){$('#zimg').src=src;$('#zcap').textContent=cap;$('#zoom').style.display='flex'}
$('#zoom').onclick=()=>$('#zoom').style.display='none';
document.addEventListener('keydown',e=>{if(e.key==='Escape')$('#zoom').style.display='none'});
openDir('',null);
</script></body></html>"""


def warm_effect_thumbs(limit=240, workers=2):
    """后台把特效缩略图先渲染好，用户翻页时就不用等（约 1.5k 张）。"""
    try:
        rels = ['effect/' + n for n, _s in sorted(_iter_files('effect'))
                if n.lower().endswith('.eff')]
    except Exception:            # noqa: BLE001
        return
    if limit:
        rels = rels[:limit]
    t0 = time.time()

    def work(chunk, tag):
        for k, rel in enumerate(chunk, 1):
            try:
                img_bytes(rel, 0, 120)
            except Exception:    # noqa: BLE001
                pass
            if k % 200 == 0:
                print('warm %s %d/%d  %.0fs'
                      % (tag, k, len(chunk), time.time() - t0), flush=True)

    n = max(1, min(workers, len(rels)))
    chunks = [rels[i::n] for i in range(n)]
    ths = [threading.Thread(target=work, args=(c, str(i)), daemon=True)
           for i, c in enumerate(chunks)]
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    print('warm done %d in %.0fs' % (len(rels), time.time() - t0), flush=True)


def kill_stale_listeners(port):
    """Windows 允许同端口重复 bind：旧进程会继续接连接、页面不更新。开服前先清干净。"""
    try:
        import psutil
    except Exception:           # noqa: BLE001
        return 0
    me, n = os.getpid(), 0
    try:
        conns = psutil.net_connections(kind='tcp')
    except Exception:           # noqa: BLE001
        return 0
    for c in conns:
        if not c.laddr or c.laddr.port != port or c.status != 'LISTEN' or not c.pid:
            continue
        if c.pid == me:
            continue
        try:
            psutil.Process(c.pid).kill()
            n += 1
        except Exception:       # noqa: BLE001
            pass
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8794)
    ap.add_argument('--data', default=None, help='资源根目录（默认 F:\\WG自由幻想\\自由幻想\\data')
    ap.add_argument('--warm', type=int, default=0,
                    help='启动时预热多少张特效缩略图（0 = 不预热）')
    ap.add_argument('--no-warm', action='store_true', help='不预热特效缩略图')
    a = ap.parse_args()
    global DATA
    if a.data:
        DATA = a.data
    n = kill_stale_listeners(a.port)
    if n:
        print('closed %d stale listener(s) on :%d' % (n, a.port), flush=True)
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), H)
    srv.daemon_threads = True
    print(f'http://127.0.0.1:{a.port}/  root={DATA}', flush=True)
    warm = 0 if a.no_warm else a.warm
    if warm > 0:
        threading.Thread(target=warm_effect_thumbs, args=(warm,),
                         daemon=True).start()
    srv.serve_forever()


if __name__ == '__main__':
    main()
