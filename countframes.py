"""Sum frames / empty frames for a folder listed in an avacensus CSV.

    python countframes.py out\\ava_wr.csv weaponr
"""
import csv
import mmap
import os
import sys

import dimg

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(dimg.SRC), '..', 'official', 'avatar')


def main():
    csvp, folder = sys.argv[1], sys.argv[2]
    base = os.path.join(dimg.SRC, '..', folder)
    rows = list(csv.DictReader(open(csvp, encoding='utf-8')))
    frames = skips = px = 0
    files = 0
    for r in rows:
        p = os.path.join(base, r['file'])
        with open(p, 'rb') as fh:
            d = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            res = dimg.parse(d)
            d.close()
        if not res.get('ok'):
            print('FAIL', r['file'], res.get('err'))
            continue
        files += 1
        frames += len(res['frames'])
        skips += res.get('skipped', 0)
        px += res.get('px_bytes', 0)
    print('%s: files %d  frames %d  empty %d  pixels %d -> %d with-pixel frames'
          % (folder, files, frames, skips, px, frames - skips))


if __name__ == '__main__':
    main()
