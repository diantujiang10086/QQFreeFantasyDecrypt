# -*- coding: utf-8 -*-
"""一次性补丁：地图名字增加 skill_runtime_inspect.json 的 worlds 兜底，并落一份精简缓存。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'maps.py')
s = io.open(P, encoding='utf-8').read()

old = '''def names():
    """map.def 里的 File → Name（GBK），如 pw21000 → 幻想小岛。

    客户端有 3 份 map.def（objects3 / D01011C7F / D01011C81），内容不完全一致，
    合并三份：先出现的优先，后面的只补空缺。
    """
    global _NAME_CACHE
    if _NAME_CACHE is None:
        _NAME_CACHE = {}
        for _path, _ver, k, _err in pkg.catalog():
            for j in range(k.count):
                if not k.key_at(j).lower().endswith('/map.def'):
                    continue
                try:
                    d = k.read_at(j)
                except Exception:                       # noqa: BLE001
                    continue
                _parse_def(d.decode('gbk', 'replace'), _NAME_CACHE)
    return _NAME_CACHE
'''

new = '''INSPECT_GLOBS = (
    r'skill_runtime_inspect.json',
)
NAME_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'out', 'map_names.json')


def _inspect_names():
    """skill_runtime_inspect.json 的 worlds：{id: {file, name}} → {file: name}。"""
    out = {}
    for pat in INSPECT_GLOBS:
        for path in glob.glob(pat):
            try:
                with open(path, encoding='utf-8-sig') as fh:
                    data = json.load(fh)
            except Exception:                            # noqa: BLE001
                continue
            worlds = data.get('worlds') if isinstance(data, dict) else None
            if not isinstance(worlds, dict):
                worlds = data if isinstance(data, dict) else {}
            for _k, v in worlds.items():
                if not isinstance(v, dict):
                    continue
                f, n = v.get('file'), v.get('name')
                if f and n:
                    out.setdefault(f.lower(), n.strip())
        if out:
            break
    return out


def names():
    """地图 File → Name。优先级：map.def（客户端 3 份合并）> skill_runtime_inspect.json。

    为避免每次都解析 200KB 的 inspect 文件，结果落在 out/map_names.json（精简缓存）。
    """
    global _NAME_CACHE
    if _NAME_CACHE is not None:
        return _NAME_CACHE
    if os.path.isfile(NAME_CACHE_FILE):
        try:
            with open(NAME_CACHE_FILE, encoding='utf-8') as fh:
                _NAME_CACHE = json.load(fh)
            if isinstance(_NAME_CACHE, dict) and _NAME_CACHE:
                return _NAME_CACHE
        except Exception:                                # noqa: BLE001
            pass
    _NAME_CACHE = {}
    for _path, _ver, k, _err in pkg.catalog():
        for j in range(k.count):
            if not k.key_at(j).lower().endswith('/map.def'):
                continue
            try:
                d = k.read_at(j)
            except Exception:                           # noqa: BLE001
                continue
            _parse_def(d.decode('gbk', 'replace'), _NAME_CACHE)
    before = len(_NAME_CACHE)
    for f, n in _inspect_names().items():
        _NAME_CACHE.setdefault(f, n)
    try:
        os.makedirs(os.path.dirname(NAME_CACHE_FILE), exist_ok=True)
        with open(NAME_CACHE_FILE, 'w', encoding='utf-8') as fh:
            json.dump(_NAME_CACHE, fh, ensure_ascii=False, sort_keys=True)
    except Exception:                                    # noqa: BLE001
        pass
    print('[maps] names: map.def=%d + inspect=%d -> %d'
          % (before, len(_NAME_CACHE) - before, len(_NAME_CACHE)), flush=True)
    return _NAME_CACHE
'''

if old not in s:
    raise SystemExit('names() pattern not found')
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('maps.py patched')
