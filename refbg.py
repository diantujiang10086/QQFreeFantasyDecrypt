"""Remove the flat-ish background of the reference renders and report the silhouette.

  python refbg.py            # writes out/ref_clean/*.png and prints bbox + ascii
"""
import os
import sys
from collections import deque

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'out', 'ref')
OUT = os.path.join(HERE, 'out', 'ref_clean')
RAMP = ' .:-=+*#%@'


def esc(s):
    return s.encode('unicode_escape').decode('ascii')


def near(a, b, tol):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol and abs(a[2] - b[2]) <= tol


def strip_bg(im, tol=20):
    w, h = im.size
    px = im.load()
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    refs = [px[x, y][:3] for x, y in seeds]
    seen = [[False] * h for _ in range(w)]
    q = deque()
    for x, y in seeds:
        if not seen[x][y]:
            seen[x][y] = True
            q.append((x, y))
    bg = set()
    while q:
        x, y = q.popleft()
        c = px[x, y]
        if not any(near(c, r, tol) for r in refs):
            continue
        bg.add((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[nx][ny]:
                seen[nx][ny] = True
                q.append((nx, ny))
    out = im.copy()
    op = out.load()
    for (x, y) in bg:
        op[x, y] = (0, 0, 0, 0)
    return out, len(bg)


def ascii_art(im, width=40):
    bbox = im.getbbox()
    if not bbox:
        return '(empty)'
    im = im.crop(bbox)
    if im.width > width:
        im = im.resize((width, max(1, round(im.height * width / im.width))), Image.NEAREST)
    a = im.split()[3].load()
    lines = []
    for y in range(im.height):
        lines.append(''.join(RAMP[min(9, a[x, y] * 10 // 256)] for x in range(im.width)))
    return '\n'.join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    for n in sorted(os.listdir(REF)):
        im = Image.open(os.path.join(REF, n)).convert('RGBA')
        clean, nbg = strip_bg(im)
        p = os.path.join(OUT, os.path.splitext(n)[0] + '.png')
        clean.save(p)
        bbox = clean.getbbox()
        print('%s size=%s bgpx=%d(%d%%) bbox=%s' % (esc(n), im.size, nbg, 100 * nbg // (im.size[0] * im.size[1]), bbox))
        if n.startswith('\u524d'):      # 前
            print(ascii_art(clean, 44))


if __name__ == '__main__':
    main()
