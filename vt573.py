"""Check the viewer's anchor-table output for npc573201t (pixel-less .gsn)."""
import json
import urllib.request as u

BASE = 'http://127.0.0.1:8791'

j = json.load(u.urlopen(BASE + '/api/frames/npc573201t', timeout=20))
fr = j['frames']
print('status', j['status'], 'frames', len(fr), 'prefix words', len(fr[0].get('v') or []))
for f in fr[:4]:
    print('  k=%-3d dir=%d  %s' % (f['k'], f['dir'], f.get('v')))
print('all pixel-less:', all(f['px'] is None for f in fr))

h = u.urlopen(BASE + '/view/index.html', timeout=20).read().decode('utf-8')
print('html bytes', len(h))
for probe in ('function renderAnchor', 'table.anchors', "e.st === 'empty' ? 'b-empty'",
              "'纯锚点表'"):
    print('  has %-38s %s' % (probe, probe in h))
