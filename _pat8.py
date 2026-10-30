import io

p = 'page2.html'
s = io.open(p, encoding='utf-8').read()

a = "const IMGEXT=new Set(['gsn','gso','gsa','til','dat','tga','bmp','png','jpg','jpeg','eff']);"
b = "const IMGEXT=new Set(['gsn','gso','gsa','til','dat','tga','bmp','png','jpg','jpeg','eff','map']);"
assert a in s
s = s.replace(a, b)

c = "    if(ext(name)==='eff'){"
d = "    if(ext(name)==='map'){\n      await mapDetail(p,name,box);\n    }else if(ext(name)==='eff'){"
assert c in s
s = s.replace(c, d, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('ok', "'eff','map'" in s, "ext(name)==='map'" in s)
