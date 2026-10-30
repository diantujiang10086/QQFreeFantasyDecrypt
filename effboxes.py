"""预计算每条 .eff 的共享画布（并集包围盒），写 out/eff_box.json。

    python effboxes.py [--limit N]

查看器启动后读取这个文件，缩略图就不用每次都跑 8 个采样点的包围盒计算
（实测单条 30–800 ms，冷却时占缩略图耗时的大头）。
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'eff_box.json')


def main():
    limit = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    import viewer2

    rels = ['effect/' + n for n, _s in sorted(viewer2._iter_files('effect'))
            if n.lower().endswith(('.eff', '.eff_'))]
    if limit:
        rels = rels[:limit]
    boxes = viewer2.eff_boxes()
    t0 = time.time()
    done = 0
    for k, rel in enumerate(rels, 1):
        if rel in boxes:
            done += 1
            continue
        try:
            txt = viewer2.src_bytes(rel).decode('gbk', 'replace')
            box = viewer2.effimg.effect_box(txt, viewer2.magic_bytes, key=None)
        except Exception as exc:     # noqa: BLE001
            print('skip', rel, type(exc).__name__, exc, flush=True)
            continue
        if box:
            boxes[rel] = [round(v, 2) for v in box]
            done += 1
        if k % 100 == 0:
            print('%d/%d  %.0fs' % (k, len(rels), time.time() - t0), flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(boxes, fh, ensure_ascii=False)
    print('done: %d/%d boxes -> %s (%.1fs)'
          % (done, len(rels), OUT, time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
