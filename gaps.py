# -*- coding: utf-8 -*-
"""Adaptive gap walk: from a signature, follow pixel blocks and report the
real inter-record overhead at every step (finds variable-length extras).

usage: python gaps.py <file> <sig_pos> [n] [window]
"""
import os
import sys

from dimg import SRC, sig_at, u32


def next_sigs(d, pos, window):
    """All signature positions in [pos, pos+window)."""
    out = []
    end = min(len(d), pos + window)
    p = pos
    while p + 16 <= end:
        if sig_at(d, p):
            out.append((p, u32(d, p), u32(d, p + 4)))
        p += 2
    return out


def main():
    name = sys.argv[1]
    sig = int(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    window = int(sys.argv[4]) if len(sys.argv) > 4 else 4096
    d = open(os.path.join(SRC, name), 'rb').read()
    print(f'{name} size={len(d)} start_sig={sig}')
    for i in range(n):
        if not sig_at(d, sig):
            print(f'  [{i}] no signature at {sig} -- stop')
            break
        w, h = u32(d, sig), u32(d, sig + 4)
        px = sig + 16
        pend = px + 2 * w * h
        cands = next_sigs(d, pend, window)
        pre = [u32(d, sig - 4 * k) for k in range(6, 0, -1)]
        line = f'  [{i}] sig@{sig} {w}x{h} pend={pend} pre={pre}'
        if not cands:
            print(line + ' -> NO next sig in window')
            break
        delta = cands[0][0] - pend
        print(line + f' -> next@{cands[0][0]} delta={delta} '
                     f'({cands[0][1]}x{cands[0][2]})'
                     + (f'  [{len(cands)} cands]' if len(cands) > 1 else ''))
        sig = cands[0][0]


if __name__ == '__main__':
    main()
