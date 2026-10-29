# -*- coding: utf-8 -*-
"""Summarise out/failed.csv (or any export index/failed CSV)."""
import collections
import csv
import sys

p = sys.argv[1] if len(sys.argv) > 1 else 'out/failed.csv'
rows = list(csv.DictReader(open(p, encoding='utf-8')))
print(f'{p}: {len(rows)} rows, columns={list(rows[0].keys()) if rows else []}')
if 'err' in (rows[0] if rows else {}):
    for k, v in collections.Counter(r['err'] for r in rows).most_common(12):
        print(f'{v:4d} | {k}')
print('by id prefix:', dict(collections.Counter(r['file'][3:7] for r in rows)))
print('by version :', dict(collections.Counter(r['version'] for r in rows)))
for r in rows:
    print(f"{r['file']:22s} v{r['version']:8s} size={r['size']:>10s} "
          f"frames={r['frames']:>4s}")
