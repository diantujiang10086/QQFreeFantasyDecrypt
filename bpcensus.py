"""Census of an avatar subfolder: file kinds, sizes, header identity."""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dimg  # noqa: E402

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar'


def walk(root):
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for f in filenames:
            p = os.path.join(dirpath, f)
            out.append((os.path.relpath(p, root), p, os.path.getsize(p)))
    return out


def main():
    sub = sys.argv[1] if len(sys.argv) > 1 else 'backpack'
    root = os.path.join(SRC, sub)
    fs = walk(root)
    print('folder %s  files %d  bytes %d' % (sub, len(fs), sum(x[2] for x in fs)))
    ext = collections.Counter(os.path.splitext(x[0])[1].lower() for x in fs)
    print('extensions:', dict(ext))
    sizes = collections.Counter(x[2] for x in fs)
    print('most common sizes:', sizes.most_common(8))
    print('size min/max:', min(x[2] for x in fs), max(x[2] for x in fs))
    # header identity for .gsn
    hdr = collections.Counter()
    nd = collections.Counter()
    for rel, p, sz in fs:
        if not rel.lower().endswith('.gsn'):
            continue
        with open(p, 'rb') as fh:
            b = fh.read(24)
        if len(b) < 24 or b[:4] != b'QQF\x1a':
            hdr['not-dimg'] += 1
            continue
        major, _u10, minor = struct.unpack_from('<3H', b, 8)
        ndirs, nframes = struct.unpack_from('<2H', b, 16)
        hdr['%d.%d' % (major, minor)] += 1
        nd[(ndirs, nframes)] += 1
    print('versions:', dict(hdr))
    print('(n_dirs, n_frames):', dict(nd))
    # directory depth / name pattern
    depth = collections.Counter(x[0].count(os.sep) for x in fs)
    print('depth histogram:', dict(depth))
    for rel, p, sz in fs[:20]:
        print('  %-40s %8d' % (rel, sz))


if __name__ == '__main__':
    main()
