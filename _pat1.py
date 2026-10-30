"""小补丁：给 _EFF_THUMBS 加上限（600 条），避免缩略图缓存无限增长。"""
p = 'viewer2.py'
s = open(p, encoding='utf-8').read()
old = '        _EFF_THUMBS[key2] = body\n'
new = ('        _EFF_THUMBS[key2] = body\n'
       '        while len(_EFF_THUMBS) > 600:\n'
       '            _EFF_THUMBS.pop(next(iter(_EFF_THUMBS)))\n')
if old in s and 'len(_EFF_THUMBS) > 600' not in s:
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)
    print('patched _EFF_THUMBS cap')
else:
    print('already patched or marker missing:', old in s)
