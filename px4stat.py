# -*- coding: utf-8 -*-
"""4 字节像素通道序的统计检验：对全部 bpp=4 文件的第一帧，
统计不透明像素在三通道上的均值，比较 BGRA / RGBA 两种取序下 R-B 的符号。

判据（启发式）：这批 NPC 是人物/坐骑立绘，肤色、木色、暖光居多，
正确取序应当让不透明像素整体偏暖（mean R > mean B）。
"""
import os
import sys
import numpy as np
import dimg

HERE = os.path.dirname(os.path.abspath(__file__))


def stats(name):
    p = os.path.join(dimg.SRC, name)
    d = open(p, 'rb').read()
    r = dimg.parse(d)
    if not r['ok'] or r['bpp'] != 4:
        return None
    pre, w, h, px, bpp = next(f for f in r['frames'] if f[3] is not None)
    raw = np.frombuffer(d, dtype=np.uint8, count=4 * w * h, offset=px)
    raw = raw.reshape(h, w, 4)
    a = raw[:, :, 3]
    op = raw[a > 200][:, :3]
    if not len(op):
        return None
    bgra = op[:, [2, 1, 0]].mean(axis=0)      # (r, g, b) when memory is B,G,R
    rgba = op[:, [0, 1, 2]].mean(axis=0)
    half = op[(a[a > 200] > 8) & (a[a > 200] < 250)] if False else None
    return dict(w=w, h=h, n=len(op),
                bgra=bgra, rgba=rgba, half=half)


def main():
    names = sys.argv[1:]
    if not names:
        # 4 字节像素文件 = A 类 34 个（fail34.txt 去掉 5 个方向表异常的 B 类）
        skip = {'npc191405.gsn', 'npc304403.gsn', 'npc42102.gsn',
                'npc488903.gsn', 'npc61903.gsn'}
        with open(os.path.join(HERE, 'out', 'fail34.txt'),
                  encoding='utf-8-sig') as fh:
            names = [ln.strip() for ln in fh
                     if ln.strip() and ln.strip() not in skip]
    rows = []
    for n in names:
        try:
            s = stats(n)
        except Exception as e:                 # noqa: BLE001
            print(f'  {n}: {type(e).__name__}: {e}')
            continue
        if s:
            rows.append((n, s))
    print(f'bpp=4 files with pixels: {len(rows)}')
    pos = neg = 0
    tot_b = tot_r = 0.0
    for n, s in rows:
        d = s['bgra'][0] - s['bgra'][2]        # R - B under BGRA reading
        pos += d > 0
        neg += d < 0
        tot_b += s['bgra'][0]
        tot_r += s['bgra'][2]
        print(f'  {n:20s} {s["w"]:4d}x{s["h"]:<4d} n={s["n"]:6d} '
              f'BGRA r/g/b={s["bgra"][0]:6.1f}/{s["bgra"][1]:6.1f}/{s["bgra"][2]:6.1f} '
              f'R-B={d:+6.1f}')
    print(f'\nBGRA reading: R>B in {pos}/{len(rows)} files, R<B in {neg}')
    if rows:
        print(f'mean of per-file means: R={tot_b / len(rows):.1f} '
              f'B={tot_r / len(rows):.1f}')


main()
