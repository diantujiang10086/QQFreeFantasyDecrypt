# -*- coding: utf-8 -*-
"""一次性补丁：地图真实名字 + 「俯视碰撞」开关（page2.html）。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'page2.html')

s = io.open(P, encoding='utf-8').read()
n = 0


def rep(old, new, cnt=1):
    global s, n
    if old not in s:
        raise SystemExit('pattern not found: %r' % old[:60])
    s = s.replace(old, new, cnt)
    n += 1


# 1) 详情标题用真实名字
rep("$('#dmeta').textContent=(info.name||name)+'",
    "$('#dmeta').textContent=(info.title||info.name||name)+'")

# 2) 加「俯视碰撞」开关
rep("  const [l3,cNpc]=mk('input','NPC',true);",
    "  const [l3,cNpc]=mk('input','NPC',true);\n"
    "  const [l4,cMask]=mk('input','俯视碰撞',false);")
rep("  bar.append(l1,l2,l3,btn);", "  bar.append(l1,l2,l3,l4,btn);")
rep("  const src=()=>'/api/mapimg?p='+enc(p)+'&w=1400&col='+(cCol.checked?1:0)",
    "  const src=()=>cMask.checked?('/api/mapmask?p='+enc(p)+'&w=1400')\n"
    "    :'/api/mapimg?p='+enc(p)+'&w=1400&col='+(cCol.checked?1:0)")
rep("  cCol.onchange=cMon.onchange=cNpc.onchange=draw;",
    "  cCol.onchange=cMon.onchange=cNpc.onchange=cMask.onchange=draw;")

# 3) 网格卡片显示真实名字
old_lbl = ("  const l=document.createElement('div');l.className='lbl';l.textContent=f.n;"
           "l.title=f.n+'  '+(f.s|0)+' B';")
new_lbl = ("  const lbl=f.t||f.n;\n"
           "  const l=document.createElement('div');l.className='lbl';l.textContent=lbl;"
           "l.title=f.n+'  '+(f.s|0)+' B';")
rep(old_lbl, new_lbl)

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('patched %d spots' % n)
