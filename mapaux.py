"""地图辅助文件（.lst / .npc / .gsm / .prc / sketchmap）取样。"""
import struct

import gsa
import pkg


def brief(text, n=1200):
    t = text.encode('ascii', 'replace').decode('ascii')
    print(t[:n])


def main(name='qw0001'):
    d = pkg.read('res/sketchmap/%s.gsa' % name)
    h = gsa.parse(d)
    print('sketch %s: %dx%d frames=%s bpp=%s' % (name, h['bw'], h['bh'], h['frames'], h['bpp']))
    g = pkg.read('map/%s.gsm' % name)
    print('gsm world: %d x %d' % struct.unpack_from('<II', g, 68))
    m = pkg.read('map/%s.msk' % name)
    w, hgt, sx, sy = struct.unpack_from('<IIII', m, 16)
    print('msk: %dx%d cells of %dx%d px -> %dx%d world, data %d B'
          % (w, hgt, sx, sy, w * sx, hgt * sy, len(m) - 32))
    print('--- lst')
    brief(pkg.read('map/%s.lst' % name).decode('gbk', 'replace'), 900)
    print('--- npc')
    brief(pkg.read('map/%s.npc' % name).decode('gbk', 'replace'), 900)
    prc = pkg.read('map/%s.prc' % name)
    print('--- prc', len(prc), [struct.unpack_from('<I', prc, o)[0] for o in range(0, 48, 4)])


if __name__ == '__main__':
    main()
