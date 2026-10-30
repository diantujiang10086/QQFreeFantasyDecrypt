"""Decode candidate layouts of tile\\*.til entries and tileimg*.dat entries to PNG for eyeballing."""
import os
import struct

from PIL import Image

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\tile'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tile_try')

BGRA = (2, 1, 0, 3)


def rgba(d, off, w, h, order=BGRA):
    n = w * h
    raw = d[off:off + 4 * n]
    out = bytearray(4 * n)
    r, g, b, a = order
    out[0::4] = raw[r::4]
    out[1::4] = raw[g::4]
    out[2::4] = raw[b::4]
    out[3::4] = raw[a::4]
    return Image.frombytes('RGBA', (w, h), bytes(out))


def main():
    os.makedirs(OUT, exist_ok=True)
    # ---- .til: header 316..324, then 128x128 RGBA entries
    til = os.path.join(ROOT, '万兽旱地.til')
    d = open(til, 'rb').read()
    print('til', len(d), 'u32@0..8', struct.unpack_from('<8I', d, 0))
    for i, hdr in enumerate((316, 324)):
        for k in range(3):
            im = rgba(d, hdr + k * 65536, 128, 128)
            p = os.path.join(OUT, 'til_h%d_%d.png' % (hdr, k))
            im.save(p)
            # also the 4 quadrants
            q = Image.new('RGBA', (128, 128))
            for qy in range(2):
                for qx in range(2):
                    sub = im.crop((qx * 64, qy * 64, qx * 64 + 64, qy * 64 + 64))
                    q.paste(sub, (qx * 64, qy * 64))
            q.save(os.path.join(OUT, 'til_h%d_%d_q.png' % (hdr, k)))
    # ---- tileimg: 64 byte header, 64x64 RGBA entries?
    dat = os.path.join(ROOT, 'tileimg.dat')
    t = open(dat, 'rb').read()
    print('tileimg', len(t), 'u32@0..12', struct.unpack_from('<12I', t, 0))
    for k in range(3):
        rgba(t, 64 + k * 16384, 64, 64).save(os.path.join(OUT, 'img64_%d.png' % k))
        rgba(t, 64 + k * 16384, 128, 64).save(os.path.join(OUT, 'img128x64_%d.png' % k))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
