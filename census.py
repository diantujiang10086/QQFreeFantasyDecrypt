# -*- coding: utf-8 -*-
"""Head-only census: how many .gsn files carry a v1 frame signature.

Reads only the first 2 KB of each file (the first frame signature is always
within the first ~160 bytes when it exists), so this is not a decode run.

usage: python census.py [n_files] [seed]
"""
import collections
import os
import random
import struct
import sys
import paths

SRC = paths.sub('data/official/avatar/npc')
HEAD = 2048


def has_sig(head):
    for p in range(24, len(head) - 16, 2):
        w, h, s, f = struct.unpack_from('<IIII', head, p)
        if 1 <= w <= 8192 and 1 <= h <= 8192 and s == 2 * w and f == 1:
            return w, h
    return None


def main():
    n_want = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.gsn'))
    rnd = random.Random(seed)
    sample = rnd.sample(files, min(n_want, len(files)))
    print(f'population={len(files)} scanning {len(sample)} heads ({HEAD}B each)')
    vers = collections.Counter()
    nosig = []
    sig = 0
    for i, f in enumerate(sample):
        with open(os.path.join(SRC, f), 'rb') as fh:
            head = fh.read(HEAD)
        if len(head) < 24:
            continue
        major, minor = struct.unpack_from('<HH', head, 8)[0], \
            struct.unpack_from('<H', head, 12)[0]
        nf, nd = (struct.unpack_from('<H', head, 16)[0],
                  struct.unpack_from('<H', head, 20)[0])
        vers[f'{major}.{minor}.{nd}'] += 1
        if has_sig(head):
            sig += 1
        else:
            nosig.append((f, f'{major}.{minor}', nf, nd,
                          os.path.getsize(os.path.join(SRC, f))))
        if (i + 1) % 1000 == 0:
            print(f'  ...{i + 1}')
    print(f'\nhead has v1 signature: {sig}/{len(sample)} '
          f'({100.0 * sig / len(sample):.2f}%)')
    print(f'no signature in first {HEAD}B: {len(nosig)} '
          f'({100.0 * len(nosig) / len(sample):.2f}%) -> '
          f'~{int(round(len(nosig) / len(sample) * len(files)))} files')
    suf = collections.Counter(f[:-4][-1] if f[:-4][-1] in 'te' else 'plain'
                             for f, *_ in nosig)
    print('  by suffix:', dict(suf))
    print('  examples:')
    for row in nosig[:15]:
        print('   ', row)
    print('\nversion histogram (file counts in sample):')
    for k, v in sorted(vers.items()):
        print(f'   {k:10s} {v}')
    if '--out' in sys.argv:
        path = sys.argv[sys.argv.index('--out') + 1]
        with open(path, 'w', encoding='utf-8') as fh:
            for row in nosig:
                fh.write(row[0] + '\n')
        print(f'wrote {len(nosig)} no-signature names to {path}')


if __name__ == '__main__':
    main()
