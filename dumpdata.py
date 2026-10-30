# -*- coding: utf-8 -*-
"""一次性导出：把运行期需要的外部数据固化成本地 JSON（之后脚本运行时只读本地文件）。

输出到 gsn-format/data/：
  map_names.json      地图 file -> 名字
  monster_names.json  怪物 id -> 名字
  map_fit.json        底图/碰撞契合度
  eff_blank.json      全空特效清单
  fields_cache.json   zipbin 列名
  eff_box.json        特效包围盒
"""
import json
import os
import shutil

import maps
import viewer2

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
os.makedirs(DATA, exist_ok=True)


def dump(name, obj):
    p = os.path.join(DATA, name)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, sort_keys=True)
    print('%-22s %8d B' % (name, os.path.getsize(p)))


dump('map_names.json', maps.names())
dump('monster_names.json', {str(k): v for k, v in sorted(maps.monster_names().items())})
dump('map_fit.json', maps._FIT_CACHE or {})

for name in ('eff_blank.json', 'fields_cache.json', 'eff_box.json'):
    src = os.path.join(HERE, 'out', name)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(DATA, name))
        print('%-22s %8d B (copied)' % (name, os.path.getsize(os.path.join(DATA, name))))
    else:
        print('!! missing', src)
