# -*- coding: utf-8 -*-
"""Look up lines of the user's own decode log (outputs/log.csv, log2.csv).

usage: python lookup.py <csv> <name> [maxchars]
"""
import io
import os
import sys

SRC = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'


def main():
    csv = sys.argv[1]
    name = sys.argv[2]
    maxchars = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
    path = csv if os.path.isabs(csv) else os.path.join(SRC, csv)
    n = 0
    with io.open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.startswith(name):
                n += 1
                head = line[:maxchars].rstrip('\n')
                print(f'--- line {n} len={len(line)}')
                print(head)
                if n >= 3:
                    break
    if not n:
        print(f'{name}: no line found in {csv}')


if __name__ == '__main__':
    main()
