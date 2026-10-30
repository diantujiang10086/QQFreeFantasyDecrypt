"""Overview sheets for the tileimg*.dat tile atlases (64x64 RGBA tiles)."""
import os
import sys

from PIL import Image, ImageDraw

import tile

CW, CH = 72, 88


def main(out='out/tileimg_sheet.png', step=1, per_page=96, cols=12):
    groups = []
    for p in tile.img_files():
        r = tile.tileimg(p)
        groups.append((os.path.basename(p)[:-4], r))
    pics = []
    for name, r in groups:
        for k in range(0, len(r['entries']), max(1, step)):
            pics.append((name, k, r['entries'][k]))
    print('groups', len(groups), 'picked', len(pics))
    pages = (len(pics) + per_page - 1) // per_page
    for page in range(pages):
        chunk = pics[page * per_page:(page + 1) * per_page]
        rows_n = (len(chunk) + cols - 1) // cols
        im = Image.new('RGBA', (cols * CW, rows_n * CH), (28, 30, 36, 255))
        dr = ImageDraw.Draw(im)
        for i, (name, k, t) in enumerate(chunk):
            bg = Image.new('RGBA', t.size, (20, 22, 26, 255))
            bg.alpha_composite(t)
            x = (i % cols) * CW + 4
            y = (i // cols) * CH + 4
            im.paste(bg, (x, y))
            dr.text((x, y + t.height + 3), '%s/%d' % (name.replace('tileimg', 'i'), k),
                    fill=(200, 200, 210, 255))
        out_p = out if page == 0 else out[:-4] + '-%d.png' % (page + 1)
        im.save(out_p)
        print('  ->', out_p, im.size)


if __name__ == '__main__':
    step = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    main(step=step)
