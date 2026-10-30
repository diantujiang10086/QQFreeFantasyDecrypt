"""把 pkg.py 里对 _official_pkg60 的 import 换成内联实现（避免依赖 inspect60_files）。"""
import re

base = open('pkg2.py', encoding='utf-8').read()
ref = open('_official_pkg60.py', encoding='utf-8').read()

i = ref.index('def _u32')
j = ref.index('class OfficialPkg')
helpers = ref[i:j].rstrip() + '\n\n'

# 去掉 pkg2.py 里的 importlib 段落
start = base.index('HERE = os.path.dirname')
end = base.index('class Pkg:')
head = base[:start]
head = head.replace('import importlib.util\nimport os\nimport struct\nfrom array import array\n',
                    'import os\nimport struct\nimport zlib\nfrom array import array\n')
head = head.replace(
    "XOR/压缩逻辑照抄私服工程 `official_pkg60.py`（逆向自 foplayer.exe）。",
    "XOR/压缩逻辑照抄私服工程 `official_pkg60.py`（逆向自 foplayer.exe，这里内联了一份）。")

middle = ("HERE = os.path.dirname(os.path.abspath(__file__))\n"
          "PKG_ROOT = r'F:\\WG自由幻想\\自由幻想\\data'\n"
          "MASK32 = 0xFFFFFFFF\n\n\n")
tail = base[end:]

out = head + middle + helpers + tail
open('pkg.py', 'w', encoding='utf-8').write(out)
print('wrote pkg.py %d bytes' % len(out))
