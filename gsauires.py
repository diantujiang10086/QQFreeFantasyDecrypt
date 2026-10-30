"""Show how the res\\uires\\*.lua UI scripts reference .gsa files (context window)."""
import os
import re
import paths

ROOT = paths.sub('data/official/res')
PAT = re.compile(r'res/[^\'"\s]+\.gsa')


def main():
    n = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        for f in filenames:
            if not f.lower().endswith('.lua'):
                continue
            p = os.path.join(dirpath, f)
            t = open(p, 'rb').read().decode('gbk', 'replace')
            for m in PAT.finditer(t):
                a = max(0, m.start() - 120)
                b = min(len(t), m.end() + 120)
                print('%-34s %s' % (os.path.relpath(p, ROOT), t[a:b].replace('\r', ' ').replace('\n', ' ')))
                n += 1
                if n >= 12:
                    return
    print('total shown', n)


if __name__ == '__main__':
    main()
