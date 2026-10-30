"""Try to explain the .gsa payload size with a few candidate layout rules."""
import collections
import os
import struct
import paths

ROOT = paths.sub('data/official/res')


def files():
    out = []
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if f.lower().endswith('.gsa'):
                out.append(os.path.join(dp, f))
    return sorted(out)


def hdr(d):
    u = struct.unpack_from('<10I', d, 8)
    return u


def main():
    fs = files()
    score = collections.Counter()
    samples = []
    for p in fs:
        d = open(p, 'rb').read()
        if len(d) < 52:
            continue
        u = hdr(d)
        hdrsize, aw, ah, bw, bh, f32, cw, ch, stride = u[1:]
        f48 = struct.unpack_from('<I', d, 48)[0]
        body = len(d) - 52
        cand = {}
        # H1: cells of (aw x ah) x 2 bytes, tiled to cover (bw x bh)
        if aw and ah and bw and bh:
            nx = -(-bw // aw)
            ny = -(-bh // ah)
            cand['H1_cells'] = nx * ny * aw * ah * 2
        # H2: single plane (bw x bh), stride = 2*bw
        if bw and bh:
            cand['H2_plane'] = bw * bh * 2
        # H3: single plane padded to 32 px rows
        if bw and bh:
            cand['H3_pad32'] = ((bw + 31) // 32 * 32) * bh * 2
        # H4: canvas (aw x ah) frames = f32
        if aw and ah and f32:
            cand['H4_frames'] = f32 * aw * ah * 2
        # H5: stride * ah (single)
        if stride and ah:
            cand['H5_stride'] = stride * ah
        best = None
        for k, v in cand.items():
            if v and body == v:
                best = (k, 0)
                break
        if best is None:
            for k, v in cand.items():
                if v and 0 <= body - v <= 4096:
                    if best is None or (body - v) < best[1]:
                        best = (k + '+tail', body - v)
        score[best[0] if best else 'none'] += 1
        if best and len(samples) < 300:
            samples.append((os.path.relpath(p, ROOT), len(d), u, best))
    print('hypotheses:', score.most_common())
    print()
    for s in samples[:15]:
        print(s)


if __name__ == '__main__':
    main()
