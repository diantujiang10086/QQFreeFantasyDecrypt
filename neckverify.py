"""Smoke-test the neck editor endpoints (page content + APIs)."""
import json
import urllib.request

BASE = 'http://127.0.0.1:8792'


def get(path):
    r = urllib.request.urlopen(BASE + path, timeout=20)
    return r.status, r.read()


def main():
    st, body = get('/')
    html = body.decode('utf-8')
    print('page', st, len(body), 'utf8 ok')
    for probe in ("const first = $('#list').firstChild;",
                  "renderList();\n};",
                  "id=\"hud\"", "state.neck[0] - hm.pivot[0]"):
        print('  contains %-40r %s' % (probe, probe in html))
    st, b = get('/api/meta?stem=npc1000101')
    m = json.loads(b)
    print('meta', st, 'canvas', m['canvas'], 'pivot', m['pivot'], 'sprite_at', m['sprite_at'],
          'frames', len(m['frames']), 'neck', m['neck'])
    st, b = get('/api/frame?stem=npc1000101&i=0')
    print('frame png', st, len(b), b[:4] == b'\x89PNG')
    st, b = get('/api/headimg?stem=head0101&dir=1')
    print('head png', st, len(b), b[:4] == b'\x89PNG')
    st, b = get('/api/heads')
    hs = json.loads(b)
    print('heads', st, len(hs), hs[:3])
    st, b = get('/api/bodies')
    bs = json.loads(b)
    print('bodies', st, len(bs), bs[0])
    st, b = get('/api/head?stem=head0101&dir=2')
    h = json.loads(b)
    print('head dir2', st, h)


if __name__ == '__main__':
    main()
