# -*- coding: utf-8 -*-
"""逐记录打印 24B 前缀 + 16B 签名 + 全局 u32 视图。

python trec.py <file> [--oh N] [--fp N]
"""
import sys, os, struct
import dimg


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def main():
    p = sys.argv[1]
    oh = int(sys.argv[sys.argv.index('--oh') + 1]) if '--oh' in sys.argv else None
    fp = int(sys.argv[sys.argv.index('--fp') + 1]) if '--fp' in sys.argv else None
    if not os.path.isabs(p):
        p = os.path.join(dimg.SRC, p)
    d = open(p, 'rb').read()
    h = dimg.head(d)
    ver = f"{h['major']}.{h['minor']}"
    if oh is None:
        oh = 4 * dimg.GET_MULTI[ver]
    if fp is None:
        fp = 24 + 4 * dimg.GET_START[ver]
    frames, ok, why = dimg.walk(d, fp, oh, h['n_frames'])
    print(f'{os.path.basename(p)} size={len(d)} ver={ver} oh={oh} fp={fp} '
          f'walk_ok={ok} {why} nfr={h["n_frames"]} ndirs={h["n_dirs"]}')
    for i, (pre, w, hh, px, bpp) in enumerate(frames):
        sig = pre + 24
        print(f' rec{i:3d} pre={pre:9d} sig={sig:9d} '
              f'prefix={d[pre:pre+24].hex(" ")} sigw={d[sig:sig+16].hex(" ")}')
    last = frames[-1]
    end = last[0] + oh + (0 if last[3] is None else last[4] * last[1] * last[2])
    print(f' end={end} size-end={len(d)-end}')
    print(' u32 view of the gap:')
    o = end - ((end - (len(d) - 64)) % 4)
    o = max(end - 64, 0)
    o -= o % 4
    while o + 4 <= len(d):
        mark = ' <' if o == end else ('  <' if o >= len(d) - 12 * h['n_dirs'] else '   ')
        print(f'   @{o:9d} {u32(d, o):10d} 0x{u32(d, o):08x}{mark}')
        o += 4


main()
