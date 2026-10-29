"""1:1 reconciliation: pixel-bearing frames in plan.csv vs PNG files on disk."""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, 'out', 'plan.csv')
EXPORT = os.path.join(HERE, 'out', 'export')

frames = px_frames = skipped = 0
bpp4_files = 0
with open(PLAN, newline='', encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        frames += int(r['frames'])
        skipped += int(r['skipped'])
        px_frames += int(r['frames']) - int(r['skipped'])
        if r['px_bytes'] and int(r['frames']) > 0:
            pass
print(f'plan frames          : {frames}')
print(f'plan skipped (empty) : {skipped}')
print(f'plan pixel frames    : {px_frames}')

npng = 0
for name in os.listdir(EXPORT):
    p = os.path.join(EXPORT, name)
    if os.path.isdir(p):
        npng += sum(1 for f in os.listdir(p) if f.endswith('.png'))
print(f'png on disk          : {npng}')
print('reconciled           :', 'YES' if npng == px_frames else f'NO (diff {npng - px_frames})')
