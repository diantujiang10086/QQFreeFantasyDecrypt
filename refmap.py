"""Print a coarse colour-index map of a reference image so its layout can be read as text.

  python refmap.py [name]      # name defaults to the front view
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'out', 'ref')
SYM = '@#%*+=-:.oO0123456789abcdefghij'


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def main():
    names = [n for n in sorted(os.listdir(REF)) if n.endswith('.png')]
    if len(sys.argv) > 1:
        tgt = sys.argv[1]
        names = [n for n in names if tgt in esc(n)] or names[:1]
    n = names[0]
    im = Image.open(os.path.join(REF, n)).convert('RGB')
    w, h = im.size
    print('file', esc(n), im.size)
    q = im.quantize(colors=12, method=Image.MEDIANCUT)
    pal = q.getpalette()[:36]
    counts = sorted(q.getcolors(), reverse=True)
    idx = {}
    print('palette:')
    for i, (cnt, k) in enumerate(counts):
        rgb = tuple(pal[k * 3:k * 3 + 3])
        idx[k] = i
        print('  %2d %-22s %6d px (%.1f%%)' % (i, str(rgb), cnt, 100.0 * cnt / (w * h)))
    data = q.load()
    step = int(os.environ.get('STEP', '2'))
    print('map (%dx%d, step %d):' % (w // step, h // step, step))
    for y in range(0, h, step):
        row = []
        for x in range(0, w, step):
            row.append(SYM[idx.get(data[x, y], 0)] if idx.get(data[x, y], 0) < len(SYM) else '?')
        print('%3d %s' % (y, ''.join(row)))


if __name__ == '__main__':
    main()
