"""Inspect the reference screenshots in out/<reference> and report geometry.

Names are handled as unicode; printed escaped so the console codepage cannot mangle them.
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'out', 'ref')   # copy of out/参考图 (local permissions)


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def main():
    names = sorted(os.listdir(REF))
    print('dir', esc(REF), 'files', len(names))
    for n in names:
        p = os.path.join(REF, n)
        im = Image.open(p)
        print('%-14s mode=%-5s size=%s' % (esc(n), im.mode, im.size))
        im = im.convert('RGBA')
        w, h = im.size
        px = im.load()
        corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
        a = im.split()[3]
        print('    corners=%s alpha=%s bbox=%s' % (corners, a.getextrema(), im.getbbox()))
        cols = im.getcolors(maxcolors=1 << 20)
        print('    distinct colors=%s' % (len(cols) if cols else '>1M'))
        if cols:
            top = sorted(cols, reverse=True)[:4]
            print('    top colors=%s' % [(c, v) for v, c in top])


if __name__ == '__main__':
    main()
