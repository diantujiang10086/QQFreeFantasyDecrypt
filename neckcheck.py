"""Extract the <script> block of necktool.py's PAGE to out/_neck_check.js for node --check."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'necktool.py'), encoding='utf-8').read()
m = re.search(r'PAGE = r"""(.*?)"""', src, re.S)
html = m.group(1)
js = re.search(r'<script>(.*)</script>', html, re.S).group(1)
out = os.path.join(HERE, 'out', '_neck_check.js')
open(out, 'w', encoding='utf-8').write(js)
print('wrote', out, len(js), 'chars')
