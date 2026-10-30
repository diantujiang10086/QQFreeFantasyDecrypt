"""Print canvas/pivot and the per-record prefix words for body and head files."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg      # noqa: E402
import headtool  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'


def show(path, kind='npc'):
    d = open(path, 'rb').read()
    pw = [dimg.u32(d, 24 + 4 * i) for i in range(9)]
    print('==', os.path.basename(path), 'preamble', pw)
    print('   canvas %dx%d pivot (%d,%d)' % (pw[3], pw[4], pw[5], pw[6]))
    if kind == 'npc':
        r = dimg.parse(d)
        print('   oh=%d first_px=%d frames=%d' % (r['oh'], r['first_px'], len(r['frames'])))
        for i, (pre, w, h, px, bpp) in enumerate(r['frames']):
            n = (r['frames'][i + 1][0] - pre) // 4 if i + 1 < len(r['frames']) else (r['oh'] - 16) // 4
            words = [dimg.u32(d, pre + 4 * j) for j in range(max(4, min(n, 20)))]
            print('   f%d %2dx%-2d prefix %d words @%d: %s' % (i, w, h, n, pre, words[:8]))
    else:
        recs, extra, k = headtool.segment(d)
        print('   records=%d  extra=%d' % (len(recs), extra))
        for i, (p, w, h, s, f) in enumerate(recs):
            pre = p - 16
            words = [dimg.u32(d, pre + 4 * j) for j in range(max(0, (16 + (p - pre - 16)) // 4))]
            words = [dimg.u32(d, pre - 4 * j) for j in range(0, 0)] or [dimg.u32(d, p - 16 + 4 * j) for j in range(4)]
            print('   rec %2d %2dx%-2d sig@%d prefix@%d: %s'
                  % (i, w, h, p, p - 16, [dimg.u32(d, p - 16 - 4 * j) for j in range(4, 0, -1)]))


if __name__ == '__main__':
    show(os.path.join(SRC, 'npc', 'npc1000101.gsn'), 'npc')
    for h in ('head2151', 'head0251', 'head0101'):
        show(os.path.join(SRC, 'head', h + '.gsn'), 'head')
