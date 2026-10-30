"""找出「全空帧」的 .eff（任何采样时刻都没有可见像素），结果写 out/eff_blank.json。

    python effscan.py [--limit N]

viewer2.py 在 effect 分类里会把这份清单里的特效过滤掉，不在列表里显示。
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'eff_blank.json')


def main():
    limit = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    import viewer2

    # scan the directory directly (files_page would already hide the blank ones)
    names = sorted(n for n, _s in viewer2._iter_files('effect')
                   if n.lower().endswith(('.eff', '.eff_')))
    if limit:
        names = names[:limit]
    t0 = time.time()
    blank = []
    for k, n in enumerate(names, 1):
        try:
            if viewer2.eff_blank('effect/' + n):
                blank.append(n)
        except Exception as exc:      # noqa: BLE001
            print('skip', n, type(exc).__name__, exc, flush=True)
        if k % 100 == 0:
            print('%d/%d  blank=%d  %.0fs' % (k, len(names), len(blank), time.time() - t0),
                  flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump({'count': len(names), 'blank': blank}, fh, ensure_ascii=False, indent=0)
    print('done: %d/%d blank -> %s (%.1fs)'
          % (len(blank), len(names), OUT, time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
