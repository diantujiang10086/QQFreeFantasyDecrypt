"""Build a contact sheet of every entry of one .til file, addressed by index (names are GBK).

    python tilsheet.py [index] [hdr] [tw]

Writes out/tile_try/sheet_<index>_<hdr>_<tw>.png (ASCII name) and prints the file's
GBK name + header u32s to stdout as ascii-escaped text.
"""
import glob
import os
import struct
import sys

from PIL import Image, ImageDraw

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\tile'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tile_try')


def rgba(d, off, w, h):
    n = w * h
    raw = d[off:off + 4 * n]
    out = bytearray(4 * n)
    out[0::4] = raw[2::4]
    out[1::4] = raw[1::4]
    out[2::4] = raw[0::4]
    out[3::4] = raw[3::4]
    return Image.frombytes('RGBA', (w, h), bytes(out))


def main():
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hdr = int(sys.argv[2]) if len(sys.argv) > 2 else 316
    tw = int(sys.argv[3]) if len(sys.argv) > 3 else 128
    files = sorted(glob.glob(os.path.join(ROOT, '*.til')))
    p = files[idx]
    d = open(p, 'rb').read()
    print('file index %d  size %d  head %s' % (idx, len(d), struct.unpack_from('<6I', d, 0)))
    n = (len(d) - hdr) // 65536
    os.makedirs(OUT, exist_ok=True)
    cols = 6
    cw = ch = tw + 6
    rows = (n + cols - 1) // cols
    sheet = Image.new('RGBA', (cols * cw, rows * ch), (32, 34, 40, 255))
    dr = ImageDraw.Draw(sheet)
    for k in range(n):
        im = rgba(d, hdr + k * 65536, tw, tw)
        bg = Image.new('RGBA', (tw, tw), (24, 26, 30, 255))
        bg.alpha_composite(im)
        x = (k % cols) * cw + 3
        y = (k // cols) * ch + 3
        sheet.paste(bg, (x, y))
        dr.text((x + 2, y + 2), str(k), fill=(255, 220, 120, 255))
    out = os.path.join(OUT, 'sheet_%d_%d_%d.png' % (idx, hdr, tw))
    sheet.save(out)
    print('wrote', out, n, 'entries', sheet.size)


if __name__ == '__main__':
    main()
