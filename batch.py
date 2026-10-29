# -*- coding: utf-8 -*-
"""Stratified random validation of dimg.py over the real .gsn population.

Picks a few hundred files (size buckets + the 't'/'e' name variants),
parses each with dimg.parse and reports pass rate, how (first_px, oh) was
found, the oh-vs-version relation, skip counts and grouped failure reasons.

usage:  python batch.py [--n-scale F] [--all-fail]
"""
import collections
import mmap
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dimg

SRC = dimg.SRC
OUT = dimg.OUT
SEED = 20250607


def pick(n_scale=1.0):
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.gsn'))
    rnd = random.Random(SEED)
    by = collections.OrderedDict(
        (('lt10k', 40), ('10k_1m', 80), ('1m_10m', 60), ('gt10m', 20)))
    pools = {k: [] for k in by}
    for f in files:
        s = os.path.getsize(os.path.join(SRC, f))
        k = ('lt10k' if s < 10_000 else '10k_1m' if s < 1_000_000
             else '1m_10m' if s < 10_000_000 else 'gt10m')
        pools[k].append(f)
    sample = []
    for k, n in by.items():
        v = pools[k]
        rnd.shuffle(v)
        sample += [(k, f) for f in v[:max(2, int(n * n_scale))]]
    for suf, n in (('t', 60), ('e', 40)):
        v = [f for f in files if f[:-4].endswith(suf)]
        rnd.shuffle(v)
        sample += [(suf, f) for f in v[:max(2, int(n * n_scale))]]
    seen, uniq = set(), []
    for k, f in sample:
        if f not in seen:
            seen.add(f)
            uniq.append((k, f))
    return files, uniq


def norm(why):
    why = re.sub(r'\d+', 'N', why)
    return re.sub(r'\s+', ' ', why)


def main():
    scale = 1.0
    if '--n-scale' in sys.argv:
        scale = float(sys.argv[sys.argv.index('--n-scale') + 1])
    files, sample = pick(scale)
    print(f'population={len(files)}  sample={len(sample)}  seed={SEED}\n')

    ok = fail = 0
    per_bucket = collections.Counter()
    per_bucket_ok = collections.Counter()
    methods = collections.Counter()
    ohs = collections.Counter()
    ver_oh = collections.defaultdict(collections.Counter)
    skips = collections.Counter()
    reasons = collections.Counter()
    fails = []
    rows = []
    slow = []
    t0 = time.time()
    for bucket, name in sample:
        p = os.path.join(SRC, name)
        r = None
        try:
            with open(p, 'rb') as fh:
                with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as d:
                    t1 = time.time()
                    r = dimg.parse(d)
                    dt = time.time() - t1
        except Exception as e:  # noqa: BLE001
            reasons[f'EXC {type(e).__name__}: {e}'] += 1
            fails.append((name, f'EXC {type(e).__name__}: {e}'))
            per_bucket[bucket] += 1
            fail += 1
            continue
        per_bucket[bucket] += 1
        slow.append((dt, name, os.path.getsize(p)))
        if not r['ok']:
            fail += 1
            why = ' ; '.join(r['tried'][-1:])
            reasons[norm(why)] += 1
            fails.append((name, why))
            continue
        ok += 1
        per_bucket_ok[bucket] += 1
        methods[r['method']] += 1
        ohs[r['oh']] += 1
        h = r['header']
        ver = f"{h['major']}.{h['minor']}.{h['n_dirs']}"
        ver_oh[ver][r['oh']] += 1
        if r['skipped']:
            skips[name] = r['skipped']
        rows.append((name, ver, os.path.getsize(p), r['oh'], r['first_px'],
                     len(r['frames']), r['skipped'], r['extra']))

    print(f'== pass rate: {ok} ok / {fail} failed  ({time.time()-t0:.1f}s)')
    print('\n== per bucket (bucket: ok/total)')
    for k in ['lt10k', '10k_1m', '1m_10m', 'gt10m', 't', 'e']:
        if per_bucket[k]:
            print(f'   {k:8s} {per_bucket_ok[k]:4d}/{per_bucket[k]:<4d}')
    print('\n== method: ' + ', '.join(f'{k}={v}' for k, v in methods.items()))
    print('== oh values: ' + ', '.join(f'{k}:{v}' for k, v in sorted(ohs.items())))
    print('\n== version -> oh  (proof that oh is NOT version-determined)')
    for ver, c in sorted(ver_oh.items()):
        print(f'   {ver:10s} ' + '  '.join(f'oh{k}x{v}' for k, v in sorted(c.items())))
    if skips:
        print(f'\n== files with pixel-less frames: {len(skips)}')
        for k, v in list(skips.items())[:12]:
            print(f'   {k} skip={v}')
    print('\n== failure reasons')
    for why, c in reasons.most_common():
        print(f'   {c:4d}  {why[:110]}')
    if fails:
        print('\n== first 40 failures')
        for name, why in fails[:40]:
            print(f'   {name:22s} {why[:100]}')
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'batch.csv'), 'w', encoding='utf-8') as f:
        f.write('file,version,size,oh,first_px,frames,skipped,extra\n')
        for row in rows:
            f.write(','.join(str(x) for x in row) + '\n')
    print(f'\nwrote {len(rows)} ok-rows to {os.path.join(OUT, "batch.csv")}')


if __name__ == '__main__':
    main()
