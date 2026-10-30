import os
import sys

import dimg

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\weaponr'

CASES = [('weaponr37261.gsn', 132, 40, 20),
         ('weaponr37152.gsn', 132, 40, 40),
         ('weaponr37257.gsn', 132, 40, 40)]

for nm, fp, oh, nf in CASES:
    d = open(os.path.join(SRC, nm), 'rb').read()
    n = len(d)
    p = fp - 16
    print('==', nm, 'size', n, 'start', p)
    for i in range(nf):
        ws = [dimg.u32(d, p + 4 * k) for k in range(4)]
        s = dimg.sig_at(d, p)
        print('  f%-2d p=%-7d words=%-28s sig=%s' % (i, p, ws, s))
        if s:
            w, hh, bpp = s
            p = p + 16 + bpp * w * hh + (oh - 16)
        elif ws == [0, 0, 0, 0]:
            p += oh
        else:
            print('     -> break: not a signature and not all zeros;', n - p, 'bytes left')
            print('     next 32 bytes:', d[p:p + 32].hex())
            break
    print('  stop p', p, 'EOF', n, 'tail', n - p)
