# -*- coding: utf-8 -*-
"""一次性补丁：page2.html 用服务端给的完整相对路径（f.p）。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'page2.html')

old = "  const p=S.cat+'/'+f.n;"
new = "  const p=f.p?(f.p):(S.cat?S.cat+'/'+f.n:f.n);"

s = io.open(P, encoding='utf-8').read()
if old not in s:
    raise SystemExit('pattern not found')
s = s.replace(old, new)
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('patched ->', new)
