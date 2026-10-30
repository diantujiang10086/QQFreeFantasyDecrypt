import re

e = open('effimg.py', encoding='utf-8').read()
e = e.replace('_SPR_MAX = 120', '_SPR_MAX = 64')
open('effimg.py', 'w', encoding='utf-8').write(e)

v = open('viewer2.py', encoding='utf-8').read()
v, n1 = re.subn(r"('--warm', type=int, default=)100", r"\g<1>0", v)
v, n2 = re.subn(r'_MAGIC_MAX = 160', '_MAGIC_MAX = 96', v)
open('viewer2.py', 'w', encoding='utf-8').write(v)
print('effimg SPR_MAX=64; warm default patched:', n1, '; magic cap patched:', n2)
