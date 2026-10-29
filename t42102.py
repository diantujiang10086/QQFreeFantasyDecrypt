# -*- coding: utf-8 -*-
"""npc42102.gsn 方向表专项诊断：打印记录、两种对齐下的 12B 表项、以及尾部 hex。"""
import sys, os, struct
import dimg

SRC = dimg.SRC


def u16(d, o):
    return struct.unpack_from('<H', d, o)[0]


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def dump(name, nshow=24):
    p = name if os.path.isabs(name) else os.path.join(SRC, name)
    d = open(p, 'rb').read()
    h = dimg.head(d)
    print('=' * 78)
    ver = f'{h["major"]}.{h["minor"]}'
    print(f'{os.path.basename(p)}  size={len(d)}  ver={ver}  '
          f'nfr={h["n_frames"]} ndirs={h["n_dirs"]} multi={dimg.GET_MULTI.get(ver)}')
    print('  preamble@24 :', [u32(d, 24 + 4 * i) for i in range(9)])
    # 用版本表走一遍（不校验方向表，看记录与 end）
    oh = 4 * dimg.GET_MULTI[ver]
    fp = 24 + 4 * dimg.GET_START[ver]
    fr, wok, wwhy = dimg.walk(d, fp, oh, h['n_frames'])
    print(f'  walk ok={wok} why={wwhy!r}')
    for i, (pre, w, hh, px, bpp) in enumerate(fr):
        print(f'  rec{i:3d} pre={pre:9d} sig@ {pre+16 if i == 0 else pre} '
              f'w={w:4d} h={hh:4d} px={px} bpp={bpp}')
    last = fr[-1]
    end = last[0] + oh + (0 if last[3] is None else last[4] * last[1] * last[2])
    print(f'  oh={oh} fp={fp} walk_end={end}  size-end={len(d)-end}')
    need = 12 * h['n_dirs']
    print(f'  n_dirs={h["n_dirs"]} dirbytes={need}')
    for label, base in (('tail-aligned', len(d) - need), ('walk-end', end)):
        vals = [(u32(d, base + 12 * i), u32(d, base + 12 * i + 4), u32(d, base + 12 * i + 8))
                for i in range(max(1, h['n_dirs']))]
        print(f'  [{label}] base={base} entries={vals}  '
              f'u16triples={[[u16(d, base + 12 * i + 2 * k) for k in range(6)] for i in range(h["n_dirs"])]}')
    n = min(len(d), 96)
    print(f'  last 96B: {d[len(d)-n:].hex(" ")}')
    print(f'  gap region walk_end..size hex: {d[end:].hex(" ")}')


for a in (sys.argv[1:] or ['npc42102.gsn', 'npc61903.gsn', 'npc191405.gsn']):
    dump(a)
