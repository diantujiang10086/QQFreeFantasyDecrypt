"""Cross-checks between item\\item, item\\itempic and magic\\magic.

    python gsorel.py
"""
import os
import re
import collections
import paths

OFFICIAL = paths.sub('data/official')
ITEM = os.path.join(OFFICIAL, 'item', 'item')
ITEMPIC = os.path.join(OFFICIAL, 'item', 'itempic')
MAGIC = os.path.join(OFFICIAL, 'magic', 'magic')


def ids(path):
    out = {}
    for n in os.listdir(path):
        stem, ext = os.path.splitext(n)
        if ext.lower() != '.gso':
            continue
        m = re.search(r'(\d+)$', stem)
        if m:
            out[m.group(1)] = n
    return out


def main():
    it, ip = ids(ITEM), ids(ITEMPIC)
    print('item ids', len(it), ' itempic ids', len(ip), ' both', len(set(it) & set(ip)),
          ' item only', len(set(it) - set(ip)), ' pic only', len(set(ip) - set(it)))
    print('  item id min/max', min(it), max(it))
    print('  pic  id min/max', min(ip), max(ip))

    xml = os.path.join(ITEMPIC, 'filter.xml')
    txt = open(xml, encoding='utf-8', errors='replace').read()
    names = re.findall(r'ClassName="([^"]+)"', txt)
    print('filter.xml entries', len(names), 'unique', len(set(names)))
    gso = {n for n in os.listdir(ITEMPIC) if n.lower().endswith('.gso')}
    print('  in xml but no file:', len(set(names) - gso), sorted(set(names) - gso)[:5])
    print('  file but not in xml:', len(gso - set(names)), sorted(gso - set(names))[:5])

    mg = os.listdir(MAGIC)
    stems = [os.path.splitext(n)[0] for n in mg]
    print('magic stems', len(stems))
    suffixed = [s for s in stems if re.search(r'_\d+$', s)]
    print('  with _NN suffix:', len(suffixed), suffixed[:6])
    base = collections.Counter(re.sub(r'_\d+$', '', s) for s in stems)
    multi = [k for k, v in base.items() if v > 1]
    print('  base groups with several files:', len(multi), multi[:8])

    # which bases does the .eff reference?
    eff = os.path.join(MAGIC, 'TFX9642.eff')
    t = open(eff, encoding='utf-8', errors='replace').read()
    refs = re.findall(r"'(magic\d+)'", t)
    print('  .eff references:', refs, 'exist?', [r in stems for r in refs])

    # magic id coverage vs item ids (are spell ids shared with item ids?)
    nums = set(re.search(r'(\d+)', s).group(1) for s in stems if re.search(r'\d', s))
    print('  magic numeric ids', len(nums), ' overlap with item ids', len(nums & set(it)))


if __name__ == '__main__':
    main()
