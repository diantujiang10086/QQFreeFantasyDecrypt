# -*- coding: utf-8 -*-
"""Inspect the user's own decode log: per-frame value structure.

usage: python logframes.py <csv> <name> [mode] [a] [b]
  mode 'counts'  -> print (frame, value count) for every frame
  mode 'detail'  -> print first 8 / last 6 values + count for frames a..b
"""
import io
import os
import re
import sys
import paths

SRC = paths.sub('data/official/avatar/npc')


def get_line(csv, name):
    path = csv if os.path.isabs(csv) else os.path.join(SRC, csv)
    with io.open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.startswith(name):
                return line
    return None


def frames_of(line):
    parts = re.split(r'【(\d+)】', line)
    # parts[0] = header ("name version nframes "), then (num, body)*
    out = []
    for i in range(1, len(parts) - 1, 2):
        num = int(parts[i])
        body = parts[i + 1]
        vals = [int(t) for t in re.findall(r'-?\d+', body)]
        out.append((num, vals))
    return parts[0].strip(), out


def main():
    csv, name = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'counts'
    a = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    b = int(sys.argv[5]) if len(sys.argv) > 5 else 10 ** 9
    line = get_line(csv, name)
    if line is None:
        print(f'{name}: not found in {csv}')
        return
    hdr, frames = frames_of(line)
    print(f'{csv} {name}: linelen={len(line)} header="{hdr}" '
          f'records={len(frames)}')
    for num, vals in frames:
        if mode == 'counts':
            if a <= num <= b:
                print(f'  【{num}】 n={len(vals)}')
        else:
            if a <= num <= b:
                head = vals[:8]
                tail = vals[-6:]
                print(f'  【{num}】 n={len(vals)}')
                print(f'      head {head}')
                print(f'      tail {tail}')


if __name__ == '__main__':
    main()
