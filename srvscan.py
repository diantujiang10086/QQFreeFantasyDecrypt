"""Scan the server source tree for references to client container formats."""
import collections
import os
import sys

ROOT = r'D:\ffo\FFO7.3\packages\自由幻想10.09\服务器'
SKIP = {'.git', '__pycache__', 'node_modules', '.pytest_cache', '.workbuddy'}
TEXT = {'.py', '.cpp', '.h', '.hpp', '.c', '.lua', '.txt', '.md', '.json', '.ini',
        '.xml', '.cs', '.js', '.sql', '.bat', '.cfg'}
KW = ['zipbin', 'terrashp', 'tileimg', '.til', 'gsa', 'i ani', 'iani', 'dimg', 'gsn']


def main(kws=None):
    kws = kws or KW
    hits = collections.Counter()
    samples = collections.defaultdict(list)
    scanned = 0
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in fn:
            ext = os.path.splitext(f)[1].lower()
            if ext not in TEXT:
                continue
            fp = os.path.join(dp, f)
            try:
                if os.path.getsize(fp) > 3_000_000:
                    continue
                s = open(fp, 'rb').read().decode('utf-8', 'ignore')
            except OSError:
                continue
            scanned += 1
            low = s.lower()
            rel = os.path.relpath(fp, ROOT)
            for kw in kws:
                c = low.count(kw.lower())
                if c:
                    hits[kw] += c
                    if len(samples[kw]) < 8:
                        samples[kw].append(rel)
    print('scanned', scanned, 'text files')
    for kw in kws:
        if hits[kw]:
            print('%-12s %5d  %s' % (kw, hits[kw], samples[kw]))


if __name__ == '__main__':
    main(sys.argv[1:] or None)
