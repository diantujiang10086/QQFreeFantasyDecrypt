# -*- coding: utf-8 -*-
"""Dump a .gsn file region as hex rows + int32 view, to eyeball where pixel data starts."""
import os
import struct
import sys

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'


def rows(data, start, stop, label):
    print(f'--- {label} [{start}:{stop}] ---')
    for o in range(start, min(stop, len(data)), 16):
        chunk = data[o:o + 16]
        hx = ' '.join(f'{b:02X}' for b in chunk)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f'{o:6d}  {hx:<48} |{asc}|')


def i32view(data, start, stop, label):
    print(f'--- int32 {label} ---')
    line = []
    for i, o in enumerate(range(start, min(stop, len(data)), 4)):
        line.append(f'{o//4}:{struct.unpack_from("<I", data, o)[0]}')
        if len(line) == 8:
            print('   ' + '  '.join(line))
            line = []
    if line:
        print('   ' + '  '.join(line))


def zero_profile(data, upto, win=32):
    """Report zero-byte density in a sliding window to locate the header->pixel transition."""
    print('--- zero density (win=%d) ---' % win)
    out = []
    for o in range(0, min(upto, len(data)) - win, 4):
        z = data[o:o + win].count(0)
        out.append((o, z))
    # print compactly
    for i in range(0, len(out), 8):
        print('   ' + '  '.join(f'{o}:{z}' for o, z in out[i:i + 8]))


def main():
    name = sys.argv[1]
    n_head = int(sys.argv[2]) if len(sys.argv) > 2 else 320
    n_tail = int(sys.argv[3]) if len(sys.argv) > 3 else 320
    path = os.path.join(SRC, name)
    data = open(path, 'rb').read()
    print(f'### {name} size={len(data)}')
    i32view(data, 0, min(len(data), 8 + n_head * 4), 'head')
    rows(data, 0, min(len(data), n_head), 'bytes head')
    if len(data) > n_tail * 2:
        rows(data, len(data) - n_tail, len(data), 'bytes tail')


if __name__ == '__main__':
    main()
