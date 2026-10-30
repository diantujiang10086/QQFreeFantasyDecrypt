"""Background removal + silhouette of the reference renders.

  python refgrid.py [--ref 0] [--zoom 4]

The reference backgrounds are a beige UI texture; every pixel that came out of a .gsn
sprite is on the 4-bit colour grid (each channel a multiple of 17), so
`(r % 17 == 0) and (g % 17 == 0) and (b % 17 == 0)` isolates the character without any
tolerance guessing.  Writes ref | mask | cut-out side by side.
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'out', 'ref')
ALL = sorted(n for n in os.listdir(REF) if n.endswith('.png'))


def esc(x):
    return x.encode('unicode_escape').decode('ascii')


def main():
    a = sys.argv[1:]
    idx = int(a[a.index('--ref') + 1]) if '--ref' in a else 0
    zoom = int(a[a.index('--zoom') + 1]) if '--zoom' in a else 4
    im = Image.open(os.path.join(REF, ALL[idx])).convert('RGB')
    arr = np.asarray(im).astype(int)
    mask = (arr % 17 == 0).all(axis=2)
    ys, xs = np.where(mask)
    print('ref', esc(ALL[idx]), '%dx%d' % im.size, 'mask px', int(mask.sum()),
          'bbox x %d..%d y %d..%d (%dx%d)' % (xs.min(), xs.max(), ys.min(), ys.max(),
                                              xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))
    m = Image.fromarray((mask * 255).astype(np.uint8)).convert('RGB')
    cut = Image.new('RGBA', im.size, (0, 0, 0, 0))
    cut.paste(im.convert('RGBA'), (0, 0), Image.fromarray((mask * 255).astype(np.uint8)))
    flat = Image.new('RGB', im.size, (24, 26, 30))
    flat.paste(cut, (0, 0), cut)
    sheet = Image.new('RGB', (im.width * 3 + 16, im.height), (40, 40, 46))
    sheet.paste(im, (0, 0))
    sheet.paste(m, (im.width + 8, 0))
    sheet.paste(flat, (im.width * 2 + 16, 0))
    dst = os.path.join(HERE, 'out', 'refmask_%s.png' % esc(ALL[idx]).replace('.png', '').replace('\\u', 'u'))
    sheet.resize((sheet.width * zoom, sheet.height * zoom), Image.NEAREST).save(dst)
    print('wrote', esc(dst), '(ref | 17-grid mask | cut-out)')


if __name__ == '__main__':
    main()
