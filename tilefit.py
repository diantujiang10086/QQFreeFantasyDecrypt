"""Find (header, entry_size) that exactly divide each tile\\*.til / *.dat file size."""
import glob
import os

ROOT = r'F:\WG自由幻想\自由幻想\data\data\official\tile'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'tile_fit.txt')

CANDS = [65536, 32768, 16384, 8192, 4096, 24576, 65536 // 2, 128 * 128 * 4,
         64 * 64 * 4, 32 * 32 * 4, 128 * 128 * 2, 64 * 64 * 2, 32 * 32 * 2,
         256 * 256, 128 * 256 * 4, 512 * 512]


def main():
    lines = []
    groups = {'til': [], 'tileimg': [], 'terrashp': []}
    for p in sorted(glob.glob(os.path.join(ROOT, '*'))):
        b = os.path.basename(p).lower()
        if b.endswith('.til'):
            groups['til'].append(p)
        elif b.startswith('tileimg'):
            groups['tileimg'].append(p)
        elif b.startswith('terrashp'):
            groups['terrashp'].append(p)
    for g, fs in groups.items():
        lines.append('### %s  (%d files)' % (g, len(fs)))
        hist = {}
        for p in fs:
            n = os.path.getsize(p)
            fits = []
            for e in CANDS:
                h = n % e
                if h <= 4096 and (n - h) % e == 0 and (n - h) // e > 0:
                    fits.append((e, h, (n - h) // e))
            hist.setdefault(n, fits)
        for n, fits in sorted(hist.items()):
            short = ' | '.join('%dK h=%d n=%d' % (e // 1024, h, c) for e, h, c in fits[:4])
            lines.append('%10d  %s' % (n, short))
        lines.append('')
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
