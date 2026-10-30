"""Cross-check .eff sprite references against magic\\ inventory."""
import glob
import os
import paths

MAGIC = paths.sub('data/official/magic/magic')
EFF = paths.sub('data/official/effect')

print('--- magic id families')
for i in (1, 16, 18, 19, 23, 34):
    hits = sorted(os.path.basename(p) for p in glob.glob(os.path.join(MAGIC, 'magic%04d*' % i)))
    print('  magic%04d -> %d  %s' % (i, len(hits), hits[:5]))

print('--- eff files using pseudo sprites')
n = 0
for f in sorted(os.listdir(EFF)):
    if not f.lower().endswith(('.eff', '.eff_')):
        continue
    t = open(os.path.join(EFF, f), 'rb').read().decode('gbk', 'replace')
    tags = [s for s in ('black', 'rotate') if ("'%s'" % s) in t]
    if tags:
        n += 1
        if n <= 10:
            print('  ', f, tags)
print('  total', n)

print('--- example usage of a pseudo sprite')
for f in ('CriHitSF.eff',):
    p = os.path.join(EFF, f)
    print(open(p, 'rb').read().decode('gbk', 'replace')[:400])
