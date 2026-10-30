"""Inspect the npc data tables (_npc_.txt / action.txt / action-9085.txt).

    python npctab.py keys                 # which keys appear in _npc_.txt
    python npctab.py entry A103           # dump one npc entry
    python npctab.py find 1000101         # which npc/action mentions this number
    python npctab.py actions 10001        # action table of one npc id
"""
import re
import sys

BASE = r'F:\WG自由幻想\自由幻想\data\data\official\avatar\npc'
NPCTXT = BASE + r'\_npc_.txt'
ACTION = BASE + r'\action.txt'
ACTION9 = BASE + r'\action-9085.txt'


def load(path):
    return open(path, 'rb').read().decode('gbk')


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else 'keys'
    s = load(NPCTXT)
    if what == 'keys':
        import collections
        c = collections.Counter(re.findall(r'^\s*([A-Za-z_]+)\s*=', s, re.M))
        for k, v in c.most_common(50):
            print(f'{k:24s} {v}')
        print('--- sections:', re.findall(r'^\[?([A-Za-z_]+)\]?\s*=', s, re.M)[:20])
        print('--- size', len(s))
    elif what == 'entry':
        want = sys.argv[2]
        i = s.find('id = "%s"' % want)
        print(s[max(0, i - 40): i + 1200])
    elif what == 'find':
        want = sys.argv[2]
        for m in re.finditer(re.escape(want), s):
            print(repr(s[max(0, m.start() - 160): m.start() + 160]))
            print('-' * 60)
    elif what == 'actions':
        want = sys.argv[2]
        for path in (ACTION, ACTION9):
            t = load(path)
            i = t.find("( '%s'" % want)
            if i < 0:
                i = t.find("(' %s'" % want)
            print('==', path)
            print(t[i:i + 1400] if i >= 0 else 'not found')


if __name__ == '__main__':
    main()
