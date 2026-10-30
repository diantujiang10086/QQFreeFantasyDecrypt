"""Group-order probe: are records dir-major (blocks of frames) or frame-major (blocks of dirs)?"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import headtool  # noqa: E402
import paths

SRC = paths.sub('data/official/avatar/backpack')


def dims(path):
    d = open(path, 'rb').read()
    recs, extra, k = headtool.segment(d)
    return [(w, h) for _p, w, h, _s, _f in recs]


def runs(seq):
    """count how many consecutive equal/similar entries; report identical-run lengths."""
    out = []
    cur = 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            cur += 1
        else:
            out.append(cur)
            cur = 1
    out.append(cur)
    return out


def main():
    names = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.gsn'))
    for nm in names:
        ds = dims(os.path.join(SRC, nm))
        n = len(ds)
        if n < 20:
            continue
        r = runs(ds)
        # count identical blocks of size n//5 ?
        f = n // 5
        blocks = [tuple(ds[i:i + f]) for i in range(0, n, f)]
        uniq = len(set(blocks))
        print('%-18s n=%-3d frames/dir=%d  identical-runs=%s  distinct blocks of %d: %d'
              % (nm[:-4], n, f, r[:12], f, uniq))
    print()
    # detail for two examples
    for nm in ('backpack75201.gsn', 'backpack91601.gsn'):
        ds = dims(os.path.join(SRC, nm))
        n = len(ds)
        f = n // 5
        print('%s  n=%d  frames/dir=%d' % (nm, n, f))
        for i, (w, h) in enumerate(ds):
            print('  #%-3d dir%-2d frame%-2d  %dx%d' % (i, i // f + 1, i % f, w, h))


if __name__ == '__main__':
    main()
