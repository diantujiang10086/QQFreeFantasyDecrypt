"""把服务端与地图解码相关的模块复制成可读的纯 ASCII 摘要（避免控制台 GBK 报错）。"""
import os
import sys

ROOT = r'D:\ffo\FFO7.3\packages\剑客符咒\服务器'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'srv')


def dump(rel, out_name=None, limit=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print('missing', rel)
        return
    t = open(p, 'r', encoding='utf-8', errors='ignore').read()
    if limit:
        t = t[:limit]
    os.makedirs(OUT, exist_ok=True)
    q = os.path.join(OUT, out_name or os.path.basename(rel))
    open(q, 'w', encoding='utf-8').write(t)
    print('%8d  %s -> %s' % (len(t), rel, q))


if __name__ == '__main__':
    for rel in sys.argv[1:]:
        dump(rel)
