"""内存占用分段测量：导入 / pkg 索引 / 特效包围盒 / 一次缩略图。"""
import os
import sys
import time

import psutil


def rss(tag):
    m = psutil.Process().memory_info().rss / 1048576.0
    print('%-28s %6.1f MB' % (tag, m), flush=True)
    return m


rss('start (python)')
import PIL.Image            # noqa: E402
rss('after PIL')
import dimg                 # noqa: E402
rss('after dimg')
import pkg                  # noqa: E402
rss('after pkg import')
import viewer2              # noqa: E402
rss('after viewer2 import')
t0 = time.time()
idx = viewer2.pkg_index()
rss('after pkg_index (%d entries, %.1fs)' % (len(idx), time.time() - t0))
b = viewer2.eff_boxes()
rss('after eff_boxes (%s)' % (len(b) if b else 0))
viewer2.img_bytes('effect/01.eff', 0, 120)
rss('after 1 eff thumb')
for i in range(50):
    try:
        viewer2.img_bytes('effect/tfx%03d_30.eff' % i, 0, 120)
    except Exception:
        pass
rss('after 50 eff thumbs')
