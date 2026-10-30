# -*- coding: utf-8 -*-
"""一次性补丁：地图怪物列表（图例）+ 原图浮层左侧怪物列表 + 名字搜索。"""
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


# 1) lightbox 支持左则面板
rep("""function lightbox(src){
  const lb=$('#lb');
  $('#lbimg').src=src;
  lb.hidden=false;
}""",
    """function lightbox(src,side){
  const lb=$('#lb');
  $('#lbimg').src=src;
  const box=$('#lbside');
  box.innerHTML='';
  if(side){box.hidden=false;box.appendChild(side);}else{box.hidden=true;}
  lb.hidden=false;
}""", 'lightbox')

rep("""function closeLb(){
  $('#lb').hidden=true;
  $('#lbimg').removeAttribute('src');
}""",
    """function closeLb(){
  $('#lb').hidden=true;
  $('#lbimg').removeAttribute('src');
  const box=$('#lbside');box.hidden=true;box.innerHTML='';
}""", 'closeLb')

# 2) mapDetail：取怪物分组，画图例，点原图时把图例带进浮层
rep("""  const src=()=>cMask.checked?('/api/mapmask?p='+enc(p)+'&w=1400')""",
    """  let groups=[];
  try{ const ml=await j('/api/maplist?p='+enc(p)); groups=ml.groups||[]; }catch(e){}
  const legend=document.createElement('div');
  legend.style.cssText='display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 10px;'
    +'color:#cfd6e3;font-size:12px;max-height:96px;overflow:auto';
  const fillLegend=(host)=>{
    host.innerHTML='';
    if(!groups.length){const t=document.createElement('span');
      t.textContent='（这张地图没有刷怪点）';t.style.color='#8b95a5';host.appendChild(t);return;}
    groups.forEach(g=>{
      const it=document.createElement('span');
      it.style.cssText='display:inline-flex;align-items:center;gap:5px';
      const dot=document.createElement('i');
      dot.style.cssText='width:9px;height:9px;border-radius:50%;display:inline-block;'
        +'border:1px solid #0008;background:rgb('+g.color.join(',')+')';
      it.appendChild(dot);
      it.appendChild(document.createTextNode(g.name+' ×'+g.count));
      host.appendChild(it);
    });
  };
  fillLegend(legend);
  box.appendChild(legend);
  const src=()=>cMask.checked?('/api/mapmask?p='+enc(p)+'&w=1400')""", 'legend')

# 3) 点原图 → 浮层左则显示怪物列表
rep("""  img.onclick=()=>lightbox(img.src);""",
    """  img.onclick=()=>{
    const side=document.createElement('div');
    side.style.cssText='min-width:170px;max-width:230px;max-height:90vh;overflow:auto;'
      +'background:#20242c;border:1px solid #313846;border-radius:8px;padding:10px;'
      +'color:#cfd6e3;font-size:12px;cursor:default';
    const h=document.createElement('div');
    h.textContent='怪物列表（'+groups.length+' 种）';
    h.style.cssText='font-weight:600;margin-bottom:8px;color:#e6ebf3';
    side.appendChild(h);
    const list=document.createElement('div');
    list.style.cssText='display:flex;flex-direction:column;gap:6px';
    fillLegend(list);
    side.appendChild(list);
    side.onclick=e=>e.stopPropagation();
    lightbox(img.src,side);
  };""", 'map lightbox side')

io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
print('page2 patched')
