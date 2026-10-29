# -*- coding: utf-8 -*-
"""Static server for the export + the viewer, plus a per-frame metadata API.

    python viewer_server.py                 # http://127.0.0.1:8791/view/index.html
    python viewer_server.py --port 8792

Serves `out/` as the web root, so
    /view/index.html        the app
    /view/manifest.json     the data file (mkview.py)
    /export/<npc>/d1_000.png  an exported frame
and adds
    /api/frames/<npc>       per-frame truth read straight from the .gsn:
                            dir, k, w, h, pixel offset, expected png name.
                            The viewer compares this with the image the
                            browser actually decoded -> catches a wrong
                            (w,h)/offset immediately.
"""
import argparse
import functools
import http.server
import json
import mmap
import os
import sys
import threading
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import dimg      # noqa: E402
import export    # noqa: E402

CACHE = {}
LOCK = threading.Lock()
CACHE_MAX = 300


def frames_for(stem):
    key = stem
    with LOCK:
        if key in CACHE:
            return CACHE[key]
    path = os.path.join(dimg.SRC, stem + '.gsn')
    out = {'file': stem + '.gsn', 'found': os.path.exists(path), 'frames': []}
    if out['found']:
        f = open(path, 'rb')
        try:
            d = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            out['size'] = len(d)
            r = dimg.parse(d)
            h = r['header']
            out['version'] = f"{h['major']}.{h['minor']}.{h['n_dirs']}"
            out['n_frames'] = h['n_frames']
            out['n_dirs'] = h['n_dirs']
            if not r['ok']:
                out['status'] = 'fail'
                out['tried'] = r['tried'][:3]
            else:
                out.update(status='ok', oh=r['oh'], first_px=r['first_px'],
                           tail=r['tail'], end=r['end'], skipped=r['skipped'],
                           method=r['method'], dirs=r['dir_counts'],
                           bpp=r['bpp'])
                counts = r['dir_counts'] or [len(r['frames'])]
                out['flat'] = not r['dir_counts']
                i = 0
                for di, c in enumerate(counts, 1):
                    for k in range(c):
                        pre, w, hh, px, bpp = r['frames'][i]
                        i += 1
                        fd = {'dir': di, 'k': k, 'w': w, 'h': hh, 'pre': pre,
                              'px': px, 'bpp': bpp,
                              'png': (f'd{di}_{k:03d}.png' if r['dir_counts']
                                      else f'f{k:04d}.png')}
                        if px is None:            # anchor table: expose the prefix words
                            n = max(1, (r['oh'] - 16) // 4)
                            fd['v'] = [x - (1 << 32) if x >= (1 << 31) else x
                                       for x in dimg.prefix_words(d, pre, n)]
                        out['frames'].append(fd)
        except Exception as e:                # noqa: BLE001
            out['status'] = 'error'
            out['tried'] = [f'{type(e).__name__}: {e}']
        finally:
            f.close()
    with LOCK:
        if len(CACHE) >= CACHE_MAX:
            CACHE.clear()
        CACHE[key] = out
    return out


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):                          # noqa: N802
        u = urllib.parse.urlparse(self.path)
        if u.path in ('', '/'):
            self.send_response(302)
            self.send_header('Location', '/view/index.html')
            self.end_headers()
            return
        if u.path.startswith('/api/frames/'):
            stem = os.path.basename(urllib.parse.unquote(u.path[12:]))
            stem = os.path.splitext(stem)[0]
            try:
                data = frames_for(stem)
            except Exception as e:             # noqa: BLE001
                data = {'file': stem + '.gsn', 'status': 'error',
                        'tried': [f'{type(e).__name__}: {e}']}
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def end_headers(self):
        p = urllib.parse.urlparse(self.path).path.lower()
        if p.endswith('.png'):
            # Exported frames never change, and one overview page asks for 300
            # of them: let the browser reuse them instead of re-fetching on
            # every page turn. A burst that size re-fetched each time is what
            # makes a local server drop requests -> "missing" thumbnails.
            self.send_header('Cache-Control', 'private, max-age=600')
        elif p.endswith('.json'):
            self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, fmt, *a):            # keep the job log readable
        if '/api/' in (self.path or ''):
            return
        super().log_message(fmt, *a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8791)
    ap.add_argument('--bind', default='127.0.0.1')
    ap.add_argument('--dir', default=os.path.join(HERE, 'out'))
    a = ap.parse_args()
    h = functools.partial(Handler, directory=a.dir)
    srv = http.server.ThreadingHTTPServer((a.bind, a.port), h)
    srv.daemon_threads = True
    print(f'serving {a.dir}')
    print(f'viewer  http://{a.bind}:{a.port}/view/index.html', flush=True)
    print(f'api     http://{a.bind}:{a.port}/api/frames/npc64401', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
