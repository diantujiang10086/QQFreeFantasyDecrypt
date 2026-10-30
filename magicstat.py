"""Structure stats for magic\\magic (dir counts, frame counts, biggest files).

    python magicstat.py
"""
import collections
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, 'out', 'gso.csv'), encoding='utf-8')))
    mg = [r for r in rows if r['folder'] == 'magic']
    print('files', len(mg))
    nd = collections.Counter()
    pat = collections.Counter()
    frm = collections.Counter()
    for r in mg:
        pat[r['dirs']] += 1
        d = [int(x) for x in r['dirs'].split('|')] if r['dirs'] else []
        nd[len(d)] += 1
        if r['frames']:
            frm[int(r['frames'])] += 1
    print('n_dirs histogram:', dict(sorted(nd.items())))
    print('frames-per-file: min %d max %d' % (min(frm), max(frm)))
    print('frames histogram (top 15):', frm.most_common(15))
    print('single-direction files:', sum(v for k, v in nd.items() if k == 1))
    print('uniform [F]*n patterns:', sum(v for k, v in pat.items()
                                          if len(set(k.split('|'))) == 1), '/', len(pat))
    big = sorted(mg, key=lambda r: -int(r['size']))[:8]
    print('biggest files:')
    for r in big:
        print('  %-22s %10d B  frames %-4s dirs %s' % (r['file'], int(r['size']), r['frames'], r['dirs']))
    multi = [r for r in mg if len(set(r['dirs'].split('|'))) > 1]
    print('files with non-uniform dir counts:', len(multi))
    for r in multi[:6]:
        print('  ', r['file'], r['frames'], r['dirs'])


if __name__ == '__main__':
    main()
