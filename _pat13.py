# -*- coding: utf-8 -*-
"""一次性补丁：给原图浮层加左侧容器 + 样式。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'page2.html')
s = io.open(P, encoding='utf-8').read()


def rep(old, new, why):
    global s
    if old not in s:
        raise SystemExit('pattern not found: ' + why)
    s = s.replace(old, new, 1)


rep('#lbhint{position:fixed;bottom:8px;left:0;right:0;',
    '#lbside{display:flex;align-items:flex-start;margin-right:14px}\n'
    '#lbside[hidden]{display:none}\n'
    '#lbhint{position:fixed;bottom:8px;left:0;right:0;', 'css')

rep('<div id="lb" hidden><img id="lbimg" alt="">',
    '<div id="lb" hidden><div id="lbside" hidden></div><img id="lbimg" alt="">', 'markup')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('page2 lightbox side added')
