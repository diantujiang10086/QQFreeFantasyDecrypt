"""启动阶段内存细查：tracemalloc 前 12 大分配 + RSS。"""
import tracemalloc

import psutil


def rss(tag):
    print('%-30s %.1f MB' % (tag, psutil.Process().memory_info().rss / 1048576.0), flush=True)


rss('import 前')
tracemalloc.start(5)
import viewer2                       # noqa: E402

rss('import viewer2')
viewer2.pkg_index()
rss('pkg_index')
viewer2.cats()
rss('cats')
viewer2.eff_boxes()
rss('eff_boxes')
for i in range(20):
    try:
        viewer2.img_bytes('effect/tfx%03d_30.eff' % i, 0, 120)
    except Exception:
        pass
rss('20 thumbs')

snap = tracemalloc.take_snapshot()
print('\n=== top allocations ===')
for st in snap.statistics('lineno')[:12]:
    print('%8.1f MB  %s' % (st.size / 1048576.0, st.traceback[0]))
