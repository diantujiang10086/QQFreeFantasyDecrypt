"""Field-level statistics of .eff structures (head tuples, keyframe tuples, trailer)."""
import collections
import os

import eff

EFF = eff.EFF


def flat(v):
    if isinstance(v, list):
        return '(' + ','.join(flat(x) for x in v) + ')'
    return str(v)


files = sorted(os.path.join(EFF, f) for f in os.listdir(EFF)
               if f.lower().endswith(('.eff', '.eff_')))
kinds = collections.Counter()
trailer = collections.Counter()
h0 = collections.Counter()
h1_rest = collections.Counter()
h2 = collections.Counter()
h3 = collections.Counter()
h4 = collections.Counter()
h5 = collections.Counter()
kf_pos = collections.Counter()
kf_scale = collections.Counter()
kf_rot = collections.Counter()
kf_col = collections.Counter()
kf_alpha = collections.Counter()
kf_time = collections.Counter()
kf_arity = collections.Counter()
headlen = collections.Counter()

for p in files:
    tree = eff.load(p)
    kinds[tree[0]] += 1
    if len(tree) > 2 and isinstance(tree[2], list):
        trailer[flat(tree[2])] += 1
    for head, sprite, kfs in eff.layers(tree):
        headlen[len(head)] += 1
        h0['id==sprite' if str(head[0]) == ''.join(ch for ch in sprite if ch.isdigit()).lstrip('0') else 'other'] += 1
        if len(head) > 1:
            h1_rest[flat(head[1][1:])] += 1
        if len(head) > 2:
            h2[flat(head[2])] += 1
        if len(head) > 3:
            h3[flat(head[3])] += 1
        if len(head) > 4:
            h4[flat(head[4])] += 1
        if len(head) > 5:
            h5[flat(head[5])] += 1
        for kf in kfs:
            kf_arity[len(kf)] += 1
            if len(kf) < 2:
                continue
            kf_time[kf[0]] += 1
            body = kf[1]
            if not isinstance(body, list) or len(body) < 5:
                kf_arity['weird:%s' % flat(body)[:40]] += 1
                continue
            kf_pos[flat(body[0])[:24]] += 1
            kf_scale[flat(body[1])] += 1
            kf_rot[flat(body[2])] += 1
            kf_col[flat(body[3])] += 1
            kf_alpha[flat(body[4])] += 1


def show(name, c, n=10):
    print('%-22s %d distinct  %s' % (name, len(c), c.most_common(n)))


print('files', len(files))
show('kind', kinds, 6)
show('trailer', trailer, 8)
show('head arity', headlen, 6)
show('head[0] vs speite id', h0, 4)
show('head[1][1:]', h1_rest, 10)
show('head[2]', h2, 8)
show('head[3]', h3, 8)
show('head[4]', h4, 8)
show('head[5]', h5, 8)
show('keyframe arity', kf_arity, 6)
show('keyframe time', kf_time, 12)
show('pos', kf_pos, 8)
show('scale', kf_scale, 8)
show('rotation', kf_rot, 8)
show('color', kf_col, 8)
show('alpha', kf_alpha, 8)
