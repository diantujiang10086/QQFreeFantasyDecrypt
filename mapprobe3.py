"""地图资源普查：sketchmap 尺寸 / 世界尺寸 / msk / lst 怪物点。"""
import re
import struct

import gsa
import pkg


def stems(ext):
    out = []
    for path, ver, k, err in pkg.catalog():
        for j in range(k.count):
            key = k.key_at(j)
            if key.startswith('map/') and key.endswith(ext):
                out.append(key.rsplit('/', 1)[-1][:-len(ext)])
    return sorted(set(out))


def main():
    sk = set(stems('.smp'))  # placeholder
    smaps = stems('.gsm')
    sk = set()
    for path, ver, k, err in pkg.catalog():
        for j in range(k.count):
            key = k.key_at(j)
            if key.startswith('res/sketchmap/'):
                sk.add(key.rsplit('/', 1)[-1][:-4])
    both = [m for m in smaps if m in sk]
    print('maps with gsm', len(smaps), 'sketch', len(sk), 'both', len(both))

    sizes = {}
    ok = 0
    bad = []
    for name in both[:60]:
        try:
            h = gsa.parse(pkg.read('res/sketchmap/%s.gsa' % name))
            g = pkg.read('map/%s.gsm' % name)
            w, hh = struct.unpack_from('<II', g, 68)
        except Exception:
            continue
        sizes[(h['bw'], h['bh'])] = sizes.get((h['bw'], h['bh']), 0) + 1
        if w and hh:
            a1, a2 = h['bw'] / h['bh'], w / hh
            if abs(a1 - a2) / a2 < 0.03:
                ok += 1
            else:
                bad.append((name, h['bw'], h['bh'], w, hh))
    print('aspect match', ok, 'of', sum(sizes.values()), 'sizes', sorted(sizes.items(), key=lambda x: -x[1])[:8])
    print('bad', bad[:5])

    # 找有怪物点的 .lst
    for name in both[:200]:
        try:
            t = pkg.read('map/%s.lst' % name).decode('gbk', 'replace')
        except Exception:
            continue
        body = [l for l in t.splitlines() if l.strip() and not l.strip().startswith('#')]
        if body:
            print('\n== lst sample', name, len(body), 'lines')
            for line in body[:12]:
                print('   ', line.encode('ascii', 'replace').decode('ascii'))
            break
    else:
        print('no non-empty lst in first 200 maps')


if __name__ == '__main__':
    main()
