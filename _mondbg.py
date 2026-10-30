# -*- coding: utf-8 -*-
import glob
import json

PAT = r'D:\ffo\FFO7.3\packages\*\服务器\data\tables\monster_stats.json'
files = glob.glob(PAT)
print('files', len(files))
for path in files:
    try:
        with open(path, encoding='utf-8-sig') as fh:
            data = json.load(fh)
    except Exception as exc:                          # noqa: BLE001
        print('load fail', type(exc).__name__, exc)
        continue
    print('entries', len(data))
    by_model = {}
    n_int = n_nm = 0
    for _k, row in data.items():
        if not isinstance(row, dict):
            continue
        nm = (row.get('name') or '').strip()
        mdl = row.get('model')
        if not nm or mdl is None:
            continue
        try:
            mdl = int(mdl)
        except (TypeError, ValueError):
            continue
        n_int += 1
        by_model[mdl] = nm
    print('mapped models', len(by_model), 'rows', n_int)
    print('3045 ->', by_model.get(3045), '3046 ->', by_model.get(3046))
