"""Full verification + decoder sketch for `official\\res\\*.gsa`.

Layout (as established):
    0..7    magic b'QQF\\x1aIANI'
    8..47   10 u32: ver(65536), hdrsize(36), aw, ah, bw, bh, frames, cw, ch, stride
    48..51  u32: f48  (1 -> 16 bit/px, 2 -> 32 bit/px)
    52..    N tiles; tile i (i>0) is preceded by a 16-byte header (w, h, stride, f48)
    N = frames * ceil(bw/aw) * ceil(bh/ah)
    tile bytes = aw * ah * 2 * f48
"""
import os
import struct
import sys
import paths

ROOT = paths.sub('data/official/res')
HEAD = 52
TH = 16


def files():
    out = []
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if f.lower().endswith('.gsa'):
                out.append(os.path.join(dp, f))
    return sorted(out)


def parse(d):
    u = struct.unpack_from('<10I', d, 8)
    ver, hdrsize, aw, ah, bw, bh, frames, cw, ch, stride = u
    f48 = struct.unpack_from('<I', d, 48)[0]
    bpp = 4 if f48 >= 2 else 2
    nx = -(-bw // cw) if cw else 0
    ny = -(-bh // ch) if ch else 0
    return dict(ver=ver, hdrsize=hdrsize, aw=aw, ah=ah, bw=bw, bh=bh, frames=frames,
                cw=cw, ch=ch, stride=stride, bpp=bpp, nx=nx, ny=ny, f48=f48,
                n_tiles=frames * nx * ny, tile=cw * ch * bpp)


def layout(d):
    h = parse(d)
    want = HEAD + h['n_tiles'] * h['tile'] + TH * (h['n_tiles'] - 1)
    return h, want


def main():
    ok = bad = 0
    bads = []
    for p in files():
        d = open(p, 'rb').read()
        if len(d) < HEAD:
            bad += 1
            continue
        h, want = layout(d)
        if want == len(d):
            ok += 1
        else:
            bad += 1
            if len(bads) < 10:
                bads.append((os.path.relpath(p, ROOT), len(d), want, h))
    print('matched %d / %d   mismatched %d' % (ok, ok + bad, bad))
    for b in bads:
        print('  %-46s size=%-9d want=%-9d %s' % b)

    for a in sys.argv[1:]:
        p = a if os.path.isabs(a) else os.path.join(ROOT, a)
        d = open(p, 'rb').read()
        h, want = layout(d)
        print()
        print('===', os.path.relpath(p, ROOT), len(d), 'ok' if want == len(d) else 'MISMATCH want %d' % want)
        print('    aw,ah=%dx%d  bw,bh=%dx%d  frames=%d  grid=%dx%d  bpp=%d  stride=%d'
              % (h['aw'], h['ah'], h['bw'], h['bh'], h['frames'], h['nx'], h['ny'], h['bpp'], h['stride']))
        pos = HEAD
        for i in range(min(h['n_tiles'], 6)):
            if i:
                th = struct.unpack_from('<4I', d, pos)
                print('    tile %2d hdr %s' % (i, th))
                pos += TH
            print('    tile %2d data @%d  first px %s' % (i, pos, d[pos:pos + 8].hex(' ')))
            pos += h['tile']


if __name__ == '__main__':
    main()
