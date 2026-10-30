"""Show lines that mention a keyword, grouped by file (bounded output)."""
import os
import sys

ROOT = r'D:\ffo\FFO7.3\packages\自由幻想10.09\服务器'
SKIP = {'.git', '__pycache__', 'node_modules', '.pytest_cache', '.workbuddy'}
TEXT = {'.py', '.cpp', '.h', '.hpp', '.c', '.lua', '.txt', '.md', '.json', '.ini',
        '.xml', '.cs', '.js', '.sql', '.bat', '.cfg'}


def main(kw, maxfiles=25, maxlines=200, only=None):
    shown = 0
    files = 0
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in SKIP]
        for f in sorted(fn):
            ext = os.path.splitext(f)[1].lower()
            if ext not in TEXT:
                continue
            fp = os.path.join(dp, f)
            if only and only.lower() not in fp.lower():
                continue
            try:
                if os.path.getsize(fp) > 3_000_000:
                    continue
                s = open(fp, 'rb').read().decode('utf-8', 'ignore')
            except OSError:
                continue
            if kw.lower() not in s.lower():
                continue
            files += 1
            if files > maxfiles:
                continue
            print('=== %s' % os.path.relpath(fp, ROOT))
            for i, line in enumerate(s.splitlines(), 1):
                if kw.lower() in line.lower():
                    print('  %4d: %s' % (i, line.strip()[:200]))
                    shown += 1
                    if shown >= maxlines:
                        print('  ... (line limit)')
                        return
    print('files matching:', files, 'lines shown:', shown)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 25,
         int(sys.argv[3]) if len(sys.argv) > 3 else 200,
         sys.argv[4] if len(sys.argv) > 4 else None)
