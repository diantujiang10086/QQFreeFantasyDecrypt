# -*- coding: utf-8 -*-
"""一次性补丁：详情标题显示底图/网格吻合度，低分时提示看「俯视碰撞」。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'page2.html')

s = io.open(P, encoding='utf-8').read()

old = ("  $('#dmeta').textContent=(info.title||info.name||name)+'  \u00b7  \u4e16\u754c '+w[0]+'\u00d7'+w[1]")
new = ("  var fitTxt='';\n"
       "  if(info.fit){var pc=Math.round((info.fit.inside||0)*100);\n"
       "    fitTxt='  \u00b7  \u5e95\u56fe\u5951\u5408 '+pc+'%'+(pc<60?'\uff08\u5efa\u8bae\u770b\u300c\u4fef\u89c6\u78b0\u649e\u300d\uff09':'');}\n"
       "  $('#dmeta').textContent=(info.title||info.name||name)+fitTxt+'  \u00b7  \u4e16\u754c '+w[0]+'\u00d7'+w[1]")

if old not in s:
    raise SystemExit('pattern not found')
s = s.replace(old, new, 1)
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('patched fit label')
