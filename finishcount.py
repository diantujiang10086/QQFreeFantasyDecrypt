"""Recount the export tree + plan.csv after the 39-file re-export.

Prints: PNG count/bytes per top-level dir under out/export, total, and the
plan.csv side (frames, pixel frames, ok/partial/fail counts).
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, 'out', 'export')
PLAN = os.path.join(HERE, 'out', 'plan.csv')

npng = 0
nbytes = 0
ndirs = 0
per = []
for name in sorted(os.listdir(EXPORT)):
    p = os.path.join(EXPORT, name)
    if not os.path.isdir(p):
        continue
    ndirs += 1
    c = b = 0
    for f in os.listdir(p):
        if f.endswith('.png'):
            c += 1
            b += os.path.getsize(os.path.join(p, f))
    npng += c
    nbytes += b
    per.append((name, c, b))

print(f'png dirs      : {ndirs}')
print(f'png files     : {npng}')
print(f'png bytes     : {nbytes} ({nbytes/2**30:.2f} GiB)')
print(f'empty dirs    : {sum(1 for _, c, _ in per if c == 0)}')
big = sorted(per, key=lambda x: -x[2])[:5]
print('largest dirs  : ' + ', '.join(f'{n}={c}png/{b/2**20:.0f}MiB' for n, c, b in big))

if os.path.exists(PLAN):
    st = {}
    frames = 0
    px_frames = 0
    px_bytes = 0
    with open(PLAN, newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            st[r['status']] = st.get(r['status'], 0) + 1
            try:
                frames += int(r['frames'])
                px_bytes += int(r['px_bytes'])
            except ValueError:
                pass
    print('plan status   : ' + ', '.join(f'{k}={v}' for k, v in sorted(st.items())))
    print(f'plan frames   : {frames}')
    print(f'plan px_bytes : {px_bytes} ({px_bytes/2**30:.2f} GiB)')
