"""Extra aggregates for the .eff report (files with missing sprites, totals)."""
import collections
import os
import re

import eff

have = set(os.path.splitext(f)[0] for f in os.listdir(eff.MAGIC))
files = sorted(f for f in os.listdir(eff.EFF) if f.lower().endswith(('.eff', '.eff_')))


def norm(s):
    m = re.fullmatch(r'(magic)(\d+)', s or '')
    return '%s%04d' % (m.group(1), int(m.group(2))) if m else s


tot_layers = tot_keys = 0
with_miss = collections.Counter()
miss_refs = collections.Counter()
kinds = collections.Counter()
times = []
for f in files:
    tree = eff.load(os.path.join(eff.EFF, f))
    kinds[tree[0]] += 1
    miss = 0
    for head, sprite, kfs in eff.layers(tree):
        tot_layers += 1
        tot_keys += len(kfs)
        for k in kfs:
            if isinstance(k, list) and k:
                times.append(k[0])
        if norm(sprite) not in have:
            miss += 1
            miss_refs[sprite] += 1
    with_miss[miss] += 1

print('files', len(files), 'layers', tot_layers, 'keyframes', tot_keys)
print('kind', dict(kinds))
print('file -> missing layer count', dict(sorted(with_miss.items())))
print('files with >=1 missing:', sum(v for k, v in with_miss.items() if k))
print('missing distinct sprites:', len(miss_refs), 'refs:', sum(miss_refs.values()))
print('worst missing:', miss_refs.most_common(8))
print('time range', min(times), max(times), 'median', sorted(times)[len(times) // 2])
