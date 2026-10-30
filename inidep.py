"""Dump the (dirN) number blocks of an avatar ini and show non-default values.

Usage: python inidep.py FILE [--sec NAME] [--limit N]
Defaults are 50 (first item) and 0 for the rest, which is what Head.ini/Npc.ini
contain everywhere; weapon inis carry real numbers and reveal the block layout.
"""
import sys


def parse(path):
    txt = open(path, 'rb').read().decode('gbk', 'replace')
    out = []
    sec = di = None
    for raw in txt.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('['):
            sec = line
        elif line.startswith('(dir'):
            di = line
        elif '=' in line and ',' not in line:
            out.append((sec, di, line))
        elif ',' in line:
            nums = []
            for tok in line.split(','):
                tok = tok.strip()
                if tok == '':
                    continue
                try:
                    nums.append(int(tok))
                except ValueError:
                    nums.append(None)
            out.append((sec, di, nums))
    return out


def main():
    a = sys.argv[1:]
    path = a[0]
    want = a[a.index('--sec') + 1] if '--sec' in a else None
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 40
    rows = parse(path)
    shown = 0
    for sec, di, val in rows:
        if want and sec != '[' + want + ']' and want not in (sec or ''):
            continue
        if isinstance(val, str):
            print(sec, di, val)
        else:
            nz = [(i, v) for i, v in enumerate(val) if v not in (0, 50, None)]
            print('%-10s %-7s len=%-3d first=%-3s nz=%s' % (sec, di, len(val), val[0] if val else '-', nz[:12]))
        shown += 1
        if shown >= limit:
            break


if __name__ == '__main__':
    main()
