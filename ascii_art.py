"""Text rendering of a sprite's alpha mask, so shapes can be reasoned about without images.

    python ascii_art.py body:out\\npc\\npc1000101_0.png head:out\\head\\head0101\\d1_c.png
    python ascii_art.py --width 60 file.png
"""
import sys

from PIL import Image

CH = ' .:-=+*#%@'


def render(path, width=48, label=None, luma=False):
    im = Image.open(path).convert('RGBA')
    a = im.split()[3]
    sx = max(1, im.width / width)
    sy = sx * 2.1                      # chars are ~2x taller than wide
    h = max(1, int(im.height / sy))
    print('== %s  %dx%d  -> %dx%d chars  mode=%s' % (label or path, im.width, im.height, width, h,
                                                     'luma' if luma else 'alpha'))
    px = im.load()
    rows = []
    for cy in range(h):
        line = []
        for cx in range(width):
            x0, x1 = int(cx * im.width / width), max(int(cx * im.width / width) + 1, int((cx + 1) * im.width / width))
            y0, y1 = int(cy * im.height / h), max(int(cy * im.height / h) + 1, int((cy + 1) * im.height / h))
            tot = n = 0
            for y in range(y0, min(y1, im.height)):
                for x in range(x0, min(x1, im.width)):
                    r, g, b, al = px[x, y]
                    if luma:
                        if al < 40:
                            continue
                        tot += 0.299 * r + 0.587 * g + 0.114 * b
                    else:
                        tot += al
                    n += 1
            if luma and n == 0:
                line.append(' ')
                continue
            line.append(CH[min(len(CH) - 1, int((tot / max(1, n)) / 256.0 * len(CH)))])
        rows.append(''.join(line))
    for i, r in enumerate(rows):
        print('%3d|%s' % (i, r))
    # also per-row opaque extent at full resolution
    w, hh = im.size
    print('   full-res row profile (y: x0..x1 count):')
    for y in range(0, hh, max(1, hh // 24)):
        xs = [x for x in range(w) if px[x, y][3] > 8]
        if xs:
            print('     y=%3d  %3d..%3d  n=%3d' % (y, min(xs), max(xs), len(xs)))
        else:
            print('     y=%3d  (empty)' % y)


width = 48
luma = '--luma' in sys.argv[1:]
argv = [a for a in sys.argv[1:] if a != '--luma']
if '--luma' in argv:
    argv.remove('--luma')
if '--width' in argv:
    i = argv.index('--width')
    width = int(argv[i + 1])
    del argv[i:i + 2]
for a in argv:
    if ':' in a and not a[1:2] == ':':
        label, path = a.split(':', 1)
    else:
        label, path = None, a
    render(path, width, label, luma)
