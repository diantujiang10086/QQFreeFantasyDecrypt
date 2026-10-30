import os

import dimg

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\weaponr'

for nm in ('weaponr37261.gsn', 'weaponr37152.gsn', 'weaponr37257.gsn'):
    d = open(os.path.join(SRC, nm), 'rb').read()
    n = len(d)
    h = dimg.head(d)
    nd = h['n_dirs']
    t = n - 12 * nd
    trip = [tuple(dimg.u32(d, t + 12 * i + 4 * k) for k in range(3)) for i in range(nd)]
    print('==', nm, 'size', n, 'n_frames', h['n_frames'], 'n_dirs', nd,
          'table@', t, 'sum', sum(x[0] for x in trip), trip)
    print('   tail 96 bytes:', d[n - 96:].hex())
    # words of the last 96 bytes
    base = n - 96
    print('   words:', [(base + 4 * i, dimg.u32(d, base + 4 * i)) for i in range(24)])
