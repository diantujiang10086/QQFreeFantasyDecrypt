"""Dump the tile\\*.ini files (GBK, UTF-16 possible) into out/tile_ini_dump.txt (UTF-8)."""
import os
import sys
import paths

ROOT = paths.sub('data/official/tile')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tile_ini_dump.txt')


def decode(d):
    for enc in ('utf-16', 'gbk', 'utf-8'):
        try:
            return d.decode(enc), enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return d.decode('gbk', 'replace'), 'gbk-replace'


def main():
    names = sys.argv[1:] or ['tile.ini', 'tileset.ini', 'tilebase.ini', 'tilelink.ini']
    lines = []
    for n in names:
        p = os.path.join(ROOT, n)
        d = open(p, 'rb').read()
        t, enc = decode(d)
        lines.append('=' * 70)
        lines.append('%s  %d bytes  enc=%s' % (n, len(d), enc))
        lines.append(t[:6000])
        if len(t) > 6000:
            lines.append('… (%d chars total)' % len(t))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
