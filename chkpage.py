import re
s = open('page2.html', encoding='utf-8').read()
m = re.search(r'<script>(.*)</script>', s, re.S)
open('out/_p2.js', 'w', encoding='utf-8').write(m.group(1))
print('click-to-load text present:', '\u70b9\u51fb\u52a0\u8f7d' in s)
print('max=512 occurrences:', s.count('&max=512'))
print('lazy attr:', "im.loading='lazy'" in s)
