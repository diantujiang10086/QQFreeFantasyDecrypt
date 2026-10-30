"""Parser + census for `official\\effect\\*.eff` (Lua-ish effect descriptors).

    python eff.py census [--csv out\\eff.csv]
    python eff.py show FILE.eff [--full]
    python eff.py refs                       # which magic assets are referenced

An .eff file is a single Lua-style tuple:

    (9,
    [
      [ (144, ('magic144', 0, 100, 0), (0,), (0,), 1, (0, 0)),
        [ [0,   ((80, 0, 300), (1.0, 1.0), 0, (255, 255, 255), 1.0)],
          [400, ((0, 0, 0),    (1.0, 1.0), 0, (255, 255, 255), 1.0)] ]
      ],
      ...
    ],
    [0,0,]
    )

`('magic144', 0, 100, 0)` names the animated sprite folder used by that layer:
`magic\\magic\\magic144.gso` (DIMG). Keyframes are `[time_ms, ((x,y,z), (sx,sy),
rotation, (r,g,b), alpha)]`.
"""
import collections
import csv
import os

import pkg
import re
import sys

_BASE = pkg.PKG_ROOT
EFF = os.path.join(_BASE, 'data', 'official', 'effect')
MAGIC = os.path.join(_BASE, 'data', 'official', 'magic', 'magic')
HERE = os.path.dirname(os.path.abspath(__file__))

NUM = '0123456789+-.'


def parse(text):
    """Parse the Lua-ish data into nested lists/tuples of numbers + strings."""
    i = 0
    n = len(text)

    def ws():
        nonlocal i
        while i < n:
            c = text[i]
            if c in ' \t\r\n':
                i += 1
            elif c == '-' and text.startswith('--', i):
                while i < n and text[i] not in '\r\n':
                    i += 1
            else:
                break

    def value():
        nonlocal i
        ws()
        c = text[i]
        if c in '([':
            close = ')' if c == '(' else ']'
            i += 1
            items = []
            while True:
                ws()
                if i >= n:
                    raise ValueError('unterminated %s' % c)
                if text[i] == close:
                    i += 1
                    break
                if text[i] == ',':          # allow `[0,0,]`
                    i += 1
                    continue
                items.append(value())
                ws()
                if i < n and text[i] == ',':
                    i += 1
            return items
        if c in '\'"':
            q = c
            i += 1
            j = i
            out = []
            while i < n and text[i] != q:
                if text[i] == '\\' and i + 1 < n:
                    out.append(text[i:i + 2])
                    i += 2
                    continue
                out.append(text[i])
                i += 1
            i += 1
            return ''.join(out)
        j = i
        while i < n and (text[i] in NUM or text[i] in 'eE' and i > j):
            i += 1
        tok = text[j:i]
        try:
            if tok.lower().lstrip('+-').startswith(('0x',)):
                return int(tok, 16)
            return int(tok) if tok.lstrip('+-').isdigit() else float(tok)
        except ValueError:
            raise ValueError('bad token %r at %d' % (tok, j))

    v = value()
    ws()
    return v


def load(path):
    with open(path, 'rb') as fh:
        raw = fh.read()
    for enc in ('gbk', 'utf-8'):
        try:
            return parse(raw.decode(enc))
        except (UnicodeDecodeError, ValueError):
            continue
    return None


def layers(tree):
    """-> [(key_tuple, sprite_name, keyframes)] from a parsed eff tree."""
    out = []
    if not isinstance(tree, list) or len(tree) < 2:
        return out
    for layer in tree[1]:
        if not isinstance(layer, list) or not layer:
            continue
        head = layer[0]
        keys = layer[1] if len(layer) > 1 and isinstance(layer[1], list) else []
        if isinstance(head, list) and head and isinstance(head[0], int):
            sprite = ''
            if len(head) > 1 and isinstance(head[1], list) and head[1]:
                sprite = head[1][0] if isinstance(head[1][0], str) else ''
            out.append((head, sprite, keys))
        elif isinstance(head, list) and head and isinstance(head[0], list):
            out.append((head, '', keys))
    return out


def census(paths, csv_path=None):
    rows = []
    bad = []
    kinds = collections.Counter()
    headlen = collections.Counter()
    nlayers = collections.Counter()
    nkeys = collections.Counter()
    sprites = collections.Counter()
    for p in paths:
        tree = load(p)
        name = os.path.basename(p)
        if tree is None:
            bad.append((name, 'parse failed'))
            rows.append(dict(file=name, size=os.path.getsize(p), ok=0, kind='', layers=0,
                             keys=0, sprites='', err='parse failed'))
            continue
        kind = tree[0] if tree and isinstance(tree[0], int) else -1
        kinds[kind] += 1
        ls = layers(tree)
        nlayers[len(ls)] += 1
        keys = 0
        names = []
        for head, sprite, kf in ls:
            keys += len(kf)
            nkeys[len(kf)] += 1
            headlen[len(head)] += 1
            if sprite:
                sprites[sprite] += 1
                names.append(sprite)
        rows.append(dict(file=name, size=os.path.getsize(p), ok=1, kind=kind,
                         layers=len(ls), keys=keys, sprites=' '.join(names), err=''))
    print('files %d  ok %d  bad %d' % (len(paths), sum(1 for r in rows if r['ok']), len(bad)))
    print('kind (first number):', dict(kinds.most_common(12)))
    print('layers/file:', dict(nlayers.most_common(12)))
    print('keyframes/layer:', dict(nkeys.most_common(12)))
    print('head tuple length:', dict(headlen.most_common(12)))
    print('distinct sprites: %d  layers using one: %d' % (len(sprites), sum(sprites.values())))
    for name, e in bad[:10]:
        print('  FAIL', name, e)
    if csv_path:
        p = csv_path if os.path.isabs(csv_path) else os.path.join(HERE, csv_path)
        os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
        with open(p, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print('csv', p)
    return rows, sprites


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    opt = {}
    for i, a in enumerate(args):
        if a.startswith('--'):
            nxt = args[i + 1] if i + 1 < len(args) else ''
            opt[a] = nxt if nxt and not nxt.startswith('--') else True
    used = set(v for v in opt.values() if isinstance(v, str))
    rest = [a for a in args[1:] if not a.startswith('--') and a not in used]
    files = sorted(os.path.join(EFF, f) for f in os.listdir(EFF)
                   if f.lower().endswith(('.eff', '.eff_')))
    if cmd == 'census':
        census(files, opt.get('--csv'))
    elif cmd == 'show':
        p = rest[0] if rest else files[0]
        if not os.path.isabs(p) and not os.path.exists(p):
            p = os.path.join(EFF, p)
        tree = load(p)
        print(os.path.basename(p), os.path.getsize(p), 'kind', tree[0])
        for k, (head, sprite, kf) in enumerate(layers(tree), 1):
            print('  layer %d  head=%s  sprite=%s  keys=%d' % (k, head, sprite, len(kf)))
            for kx in kf if '--full' in opt else kf[:4]:
                print('     ', kx)
    elif cmd == 'refs':
        _, sprites = census(files)
        have = set(os.path.splitext(f)[0] for f in os.listdir(MAGIC))

        def norm(s):
            m = re.fullmatch(r'(magic)(\d+)', s or '')
            return '%s%04d' % (m.group(1), int(m.group(2))) if m else s

        missing = sorted(s for s in sprites if norm(s) not in have)
        special = sorted(s for s in sprites if not re.fullmatch(r'magic\d+', s or ''))
        print('referenced sprites: %d (raw)  present in magic\\: %d  missing: %d'
              % (len(sprites), len(sprites) - len(missing), len(missing)))
        print('non-magic sprite names:', special[:20], '...' if len(special) > 20 else '')
        print('top used:', sprites.most_common(12))
        print('missing sample:', missing[:12])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
