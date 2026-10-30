"""Validate the mix rule against the 5 pixel-perfect ground truths.

Ground truth (reference images, 96-97% exact reproduction):
    前   body f4 + head2151 d5 -> (dx,dy) = (+3, -20)
    后   body f3 + head2151 d4 -> (+9, -18)
    左   body f1 + head2151 d2 -> (+4, -19)
    左上 body f2 + head2151 d3 -> (+16, -18)
    左下 body f0 + head2151 d1 -> (+11, -22)
Here we ignore the per-frame canvas offsets and ask the plain rule
(hx = top-centre - pivot.x, hy = 8 - pivot.y) what it would produce.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mix   # noqa: E402

TRUTH = [('前', 4, 5, 3, -20), ('后', 3, 4, 9, -18), ('左', 1, 2, 4, -19),
         ('左上', 2, 3, 16, -18), ('左下', 0, 1, 11, -22)]


def main():
    bp = os.path.join(mix.SRC, 'npc', 'npc1000101.gsn')
    hp = os.path.join(mix.SRC, 'head', 'head2151.gsn')
    print('%-6s %-6s %-14s %-14s %s' % ('view', 'frame', 'rule(dx,dy)', 'truth(dx,dy)', 'delta'))
    for name, fr, dr, tx, ty in TRUTH:
        b = mix.body_frame(bp, fr)
        h = mix.head_pic(hp, dr)
        _im, (rx, ry) = mix.compose(b['img'], h)
        print('%-6s %-6d (%+d,%+d)%8s (%+d,%+d)%8s (%+d,%+d)'
              % (name, fr, rx, ry, '', tx, ty, '', rx - tx, ry - ty))


if __name__ == '__main__':
    main()
