"""把预热改成可调且默认更轻：--warm N（默认 100），并支持 --no-warm。"""
p = 'viewer2.py'
s = open(p, encoding='utf-8').read()

old = ("    ap.add_argument('--no-warm', action='store_true'")
new = ("    ap.add_argument('--warm', type=int, default=100,\n"
       "                    help='启动时预热多少张特效缩略图（0 = 不预热）')\n"
       "    ap.add_argument('--no-warm', action='store_true'")
assert old in s
s = s.replace(old, new, 1)

old2 = ("    if not a.no_warm:\n"
        "        threading.Thread(target=warm_effect_thumbs, daemon=True).start()")
new2 = ("    warm = 0 if a.no_warm else a.warm\n"
        "    if warm > 0:\n"
        "        threading.Thread(target=warm_effect_thumbs, args=(warm,),\n"
        "                         daemon=True).start()")
assert old2 in s
s = s.replace(old2, new2, 1)
open(p, 'w', encoding='utf-8').write(s)
print('main() warm args patched')
