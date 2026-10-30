"""地图资源：sketchmap 底图 + .msk 碰撞格 + .lst 怪物点 + .npc NPC 点。

格式（据私服 `server/map60.py` 与实测）：
  .gsm  magic 'Tencent QQShowChat Map File'，@68 u32 world_w, world_h
  .msk  magic 'QQF\\x1aMASK'，@16 u32 cells_w, cells_h, @24 u32 sx, sy；
        数据 32 起，`cells[y*cells_w+x] & 1` 为 1 表示有碰撞
  .lst  文本：`id N` / `index N` / `init_pos x y` / `init_dir N` 分组 —— 怪物刷新点
  .npc  ini 风格 [Npc] 段：ID/Index/Name/Script/Init_Pos/Init_Dir
  sketchmap/*.gsa  整张地图的示意图（就是地图界面里看到的那张）
"""
import glob
import json
import os
import re
import struct

from PIL import Image, ImageDraw

import gsa
import pkg

MASK_MAGIC = b'QQF\x1aMASK'
GSM_MAGIC = b'Tencent QQShowChat Map File'

_NAME_CACHE = None
_ALIGN_CACHE = None


def _read(key):
    try:
        return pkg.read(key)
    except Exception:          # noqa: BLE001
        return None


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def _load_json(name, default=None):
    p = os.path.join(DATA_DIR, name)
    try:
        with open(p, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:                            # noqa: BLE001
        return default if default is not None else {}


def names():
    """地图 file -> 名字。运行期只读本地 data/map_names.json（由 dumpdata.py 一次性生成）。"""
    global _NAME_CACHE
    if _NAME_CACHE is None:
        _NAME_CACHE = _load_json('map_names.json')
    return _NAME_CACHE


def _parse_def(txt, acc):
    cur = {}
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith(';'):
            continue
        if s.startswith('['):
            f, n = cur.get('file'), cur.get('name')
            if f and n and f.lower() not in acc:
                acc[f.lower()] = n
            cur = {}
            continue
        if '=' not in s:
            continue
        kk, vv = s.split('=', 1)
        kk, vv = kk.strip().lower(), vv.strip()
        if kk == 'file':
            cur['file'] = vv
        elif kk == 'name':
            cur['name'] = vv
    f, n = cur.get('file'), cur.get('name')
    if f and n and f.lower() not in acc:
        acc[f.lower()] = n
    return acc


def display_name(name):
    return names().get(name.lower()) or name


def _align():
    """底图相对碰撞网格的平移（由 mapalign.py 预先算好，像素单位按 240 宽）。"""
    global _ALIGN_CACHE
    if _ALIGN_CACHE is None:
        _ALIGN_CACHE = {}
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'map_align.json')
        try:
            import json
            raw = json.load(open(p, encoding='utf-8'))
            for k, v in raw.items():
                # 只有峰明显高于零位移时才采用，避免误配
                if v.get('peak', 0) > v.get('base', 0) * 1.15 and (v.get('dx') or v.get('dy')):
                    _ALIGN_CACHE[k] = (v['dx'], v['dy'], v['size'])
        except Exception:                                  # noqa: BLE001
            pass
    return _ALIGN_CACHE


def align_shift(name, size):
    """把 _align 里的 (dx,dy)（240 宽基准）换算到目标尺寸。"""
    v = _align().get(name.lower())
    if not v:
        return (0, 0)
    dx, dy, sz = v
    W, H = size
    return (int(round(dx * W / sz[0])), int(round(dy * H / sz[1])))


def stems():
    """有 .gsm 的地图名（小写，如 qw0001）。"""
    out = set()
    for _path, _ver, k, _err in pkg.catalog():
        for j in range(k.count):
            key = k.key_at(j)
            if key.startswith('map/') and key.endswith('.gsm'):
                out.add(key.rsplit('/', 1)[-1][:-4])
    return sorted(out)


def stems_with_sketch():
    """同时有示意图（res/sketchmap/*.gsa）的地图名。"""
    sk = set()
    for _path, _ver, k, _err in pkg.catalog():
        for j in range(k.count):
            key = k.key_at(j)
            if key.startswith('res/sketchmap/'):
                sk.add(key.rsplit('/', 1)[-1][:-4])
    return [n for n in stems() if n in sk]


def world(name):
    d = _read('map/%s.gsm' % name)
    if not d or not d.startswith(GSM_MAGIC) or len(d) < 76:
        return None
    w, h = struct.unpack_from('<II', d, 68)
    return (w, h) if w and h else None


def mask(name):
    d = _read('map/%s.msk' % name)
    if not d or not d.startswith(MASK_MAGIC) or len(d) < 32:
        return None
    w, h, sx, sy = struct.unpack_from('<IIII', d, 16)
    if not (w and h and sx and sy) or len(d) < 32 + w * h:
        return None
    return {'w': w, 'h': h, 'sx': sx, 'sy': sy, 'cells': d[32:32 + w * h]}


def sketch(name):
    d = _read('res/sketchmap/%s.gsa' % name)
    if not d:
        return None
    try:
        h = gsa.parse(d)
        frames = gsa.frames(d, h)
    except Exception:          # noqa: BLE001
        return None
    return frames[0] if frames else None


_POS_RE = re.compile(r'init_pos\s*(-?\d+)\s*[,\s]\s*(-?\d+)')


_MON_NAMES = None


PALETTE = (
    (255, 200, 0), (255, 96, 64), (96, 200, 255), (170, 120, 255), (120, 230, 120),
    (255, 140, 220), (255, 255, 120), (120, 255, 220), (200, 160, 96), (150, 200, 60),
    (240, 100, 160), (100, 160, 255), (255, 160, 60), (160, 255, 160), (220, 220, 220),
)


def monster_names():
    """怪物 id -> 名字。运行期只读本地 data/monster_names.json。"""
    global _MON_NAMES
    if _MON_NAMES is None:
        raw = _load_json('monster_names.json')
        out = {}
        for k, v in raw.items():
            try:
                out[int(k)] = v
            except (TypeError, ValueError):
                continue
        _MON_NAMES = out
    return _MON_NAMES


def monster_color(idx):
    try:
        return PALETTE[int(idx) % len(PALETTE)]
    except (TypeError, ValueError):
        return PALETTE[0]


def monsters(name):
    d = _read('map/%s.lst' % name)
    if not d:
        return []
    text = d.decode('gbk', 'replace')
    out, cur = [], {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        if s.lower().startswith('id '):
            cur = {'id': s.split()[1]}
        elif s.lower().startswith('index '):
            raw = s.split(None, 1)[1].strip()
            ids = [p.strip() for p in raw.split(',') if p.strip()]
            if ids:
                cur['index'] = ids[0]
                cur['ids'] = ids
        elif s.lower().startswith('init_pos'):
            m = _POS_RE.search(s)
            if m and 'index' in cur:
                cur['x'], cur['y'] = int(m.group(1)), int(m.group(2))
                out.append(cur)
                cur = {}
    nm = monster_names()
    for it in out:
        ids = it.get('ids') or [it.get('index')]
        names, key = [], None
        for i, sid in enumerate(ids):
            try:
                k = int(sid)
            except (TypeError, ValueError):
                k = None
            if i == 0:
                key = k
            got = nm.get(k) if k is not None else None
            if got:
                names.append(got)
        it['names'] = names
        it['name'] = (names[0] if names else None) or ('怪物 %s' % (it.get('index') or '?'))
        it['color'] = monster_color(key if key is not None else 0)
    return out


def npcs(name):
    d = _read('map/%s.npc' % name)
    if not d:
        return []
    text = d.decode('gbk', 'replace')
    out, cur, in_sec = [], None, False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('['):
            if cur and 'x' in cur:
                out.append(cur)
            in_sec = s.lower().startswith('[npc')
            cur = {} if in_sec else None
            continue
        if cur is None or '=' not in s:
            continue
        k, _, v = s.partition('=')
        k, v = k.strip().lower(), v.strip()
        if k == 'init_pos':
            m = _POS_RE.search('init_pos ' + v)
            if m:
                cur['x'], cur['y'] = int(m.group(1)), int(m.group(2))
        elif k in ('id', 'index', 'name', 'script'):
            cur[k] = v
    if cur and 'x' in cur:
        out.append(cur)
    return out


def info(name):
    w = world(name)
    m = mask(name)
    sk = sketch(name)
    return {
        'n': name,
        'w': w[0] if w else 0,
        'h': w[1] if w else 0,
        'cells': (m['w'] * m['h']) if m else 0,
        'cell': (m['sx'], m['sy']) if m else None,
        'sketch': sk.size if sk else None,
        'monsters': len(monsters(name)),
        'npcs': len(npcs(name)),
    }


def walkable_bbox(name):
    """可走区域在 world 坐标里的包围盒（.msk 网格 × cell 尺寸）。"""
    m = mask(name)
    if not m:
        return None
    w, h, sx, sy = m['w'], m['h'], m['sx'], m['sy']
    cells = m['cells']
    if len(cells) != w * h:
        return None
    x0 = y0 = None
    x1 = y1 = -1
    for y in range(h):
        row = cells[y * w:(y + 1) * w]
        if not any(not (v & 1) for v in row):
            continue
        if y0 is None:
            y0 = y
        y1 = y
        for x in range(w):
            if not (row[x] & 1):
                if x0 is None or x < x0:
                    x0 = x
                if x > x1:
                    x1 = x
    if x0 is None:
        return None
    return (x0 * sx, y0 * sy, (x1 + 1) * sx, (y1 + 1) * sy)


def collision_overlay(name, size, base=None, use_bbox=False):
    """把碰撞网格铺到底图上：优先按「可走区域 bbox ↔ 底图不透明 bbox」对齐。

    底图四周可能留了空白/美术外扩，直接拉伸会有系统性错位；用 bbox 对齐能吸收
    这部分偏移与轻微缩放。失败时回退到整幅拉伸。
    """
    m = mask(name)
    if not m:
        return None
    cells = m['cells']
    if len(cells) != m['w'] * m['h']:
        return None
    src = Image.frombytes('L', (m['w'], m['h']),
                          bytes(255 if v & 1 else 0 for v in cells))
    W, H = size
    dist = Image.new('L', (W, H), 0)
    wb = walkable_bbox(name) if (use_bbox and base is not None) else None
    ab = base.getbbox() if (use_bbox and base is not None) else None
    if wb and ab:
        x0, y0, x1, y1 = wb
        ax0, ay0, ax1, ay1 = ab
        # world 坐标 → 底图像素；只取可走 bbox 那一块，贴到 alpha bbox
        sx = (ax1 - ax0) / max(1, (x1 - x0))
        sy = (ay1 - ay0) / max(1, (y1 - y0))
        cw = int(round((x1 - x0) / m['sx']))
        ch = int(round((y1 - y0) / m['sy']))
        if cw >= 1 and ch >= 1:
            box = (int(wb[0] // m['sx']), int(wb[1] // m['sy']),
                   int(wb[0] // m['sx']) + cw, int(wb[1] // m['sy']) + ch)
            part = src.crop(box).resize((max(1, ax1 - ax0), max(1, ay1 - ay0)), Image.NEAREST)
            dist.paste(part, (ax0, ay0))
            a = dist.point(lambda v: v * 110 // 255)
            layer = Image.new('RGBA', (W, H), (255, 32, 32, 255))
            layer.putalpha(a)
            return layer
    part = src.resize((W, H), Image.NEAREST)
    a = part.point(lambda v: v * 110 // 255)
    layer = Image.new('RGBA', (W, H), (255, 32, 32, 255))
    layer.putalpha(a)
    return layer


_FIT_CACHE = None


def fit(name):
    """底图与碰撞网格的吻合度。运行期只读本地 data/map_fit.json。"""
    global _FIT_CACHE
    if _FIT_CACHE is None:
        _FIT_CACHE = _load_json('map_fit.json')
    return _FIT_CACHE.get(name.lower())


def mask_image(name, width=900, bg=(24, 26, 30)):
    """俯视碰撞图：红=不可走、绿=可走（不叠底图，位置绝对可靠）。"""
    m = mask(name)
    if not m or len(m['cells']) != m['w'] * m['h']:
        return None
    cells = m['cells']
    blocked = Image.frombytes('L', (m['w'], m['h']),
                              bytes(255 if v & 1 else 0 for v in cells))
    h = max(1, int(round(m['h'] * width / m['w'])))
    big = blocked.resize((width, h), Image.NEAREST)
    img = Image.new('RGBA', (width, h), bg + (255,))
    red = Image.new('RGBA', (width, h), (255, 48, 48, 255))
    red.putalpha(big.point(lambda v: 220 if v > 127 else 0))
    green = Image.new('RGBA', (width, h), (40, 210, 90, 255))
    green.putalpha(big.point(lambda v: 0 if v > 127 else 150))
    img.alpha_composite(red)
    img.alpha_composite(green)
    return img


def collision_image(name, size):
    """把 .msk 变成 size 大小的红色半透明覆盖层（NEAREST 缩放，C 速度）。"""
    m = mask(name)
    if not m:
        return None
    cells = m['cells']
    blocked = Image.frombytes('L', (m['w'], m['h']),
                              bytes(255 if v & 1 else 0 for v in cells)) \
        if len(cells) == m['w'] * m['h'] else None
    if blocked is None:
        return None
    a = blocked.resize(size, Image.NEAREST).point(lambda v: v * 110 // 255)
    layer = Image.new('RGBA', size, (255, 32, 32, 255))
    layer.putalpha(a)
    return layer


def monster_groups(name):
    """按怪物种类聚合：[{'index','name','color','count'}]，按数量降序。"""
    groups = {}
    for it in monsters(name):
        k = it.get('index', '?')
        g = groups.get(k)
        if g is None:
            groups[k] = g = {'index': k, 'name': it.get('name'), 'color': it.get('color'), 'count': 0}
        g['count'] += 1
    return sorted(groups.values(), key=lambda g: (-g['count'], str(g['index'])))


def render(name, width=720, collision=True, mon=True, npc_pts=True, bg=(40, 44, 52)):
    """底图 + 半透明红色碰撞格 + 怪物/NPC 点（画在不透明深色底上，便于看清）。"""
    base = sketch(name)
    if base is None:
        return None
    if width and width != base.width:
        h = max(1, int(round(base.height * width / base.width)))
        base = base.convert('RGBA').resize((width, h), Image.NEAREST)
    base = base.convert('RGBA')
    W, H = base.size
    img = Image.new('RGBA', (W, H), bg + (255,))
    img.alpha_composite(base)

    if collision:
        layer = collision_overlay(name, (W, H), base=base)
        if layer is not None:
            img.alpha_composite(layer)

    d = ImageDraw.Draw(img)
    r = max(3, W // 320)          # 标记大小随图宽缩放，缩略图上也能看见
    if mon:
        w = world(name) or (W, H)
        for it in monsters(name):
            x = it['x'] * W // max(1, w[0])
            y = it['y'] * H // max(1, w[1])
            if 0 <= x < W and 0 <= y < H:
                c = it.get('color') or (255, 200, 0)
                d.ellipse((x - r, y - r, x + r, y + r), fill=c + (255,), outline=(0, 0, 0, 255))
    if npc_pts:
        w = world(name) or (W, H)
        for it in npcs(name):
            x = it['x'] * W // max(1, w[0])
            y = it['y'] * H // max(1, w[1])
            if 0 <= x < W and 0 <= y < H:
                d.rectangle((x - r, y - r, x + r, y + r), fill=(80, 255, 120, 255), outline=(0, 0, 0, 255))
    return img


if __name__ == '__main__':
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else 'qw0001'
    print(info(name))
    im = render(name, width=1440)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', '_map_%s.png' % name)
    if im:
        im.save(out)
        print('saved', out, im.size)
