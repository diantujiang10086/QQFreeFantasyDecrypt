import re
s = open('viewer2.py', encoding='utf-8').read()
for m in re.finditer(r"p == '([^']+)'", s):
    print('route', m.group(1), 'line', s[:m.start()].count('\n') + 1)
print('--- page2 ---')
h = open('page2.html', encoding='utf-8').read()
for i, l in enumerate(h.split('\n'), 1):
    if 'eff' in l.lower() or 'txt' in l.lower():
        print(i, l.strip()[:160])
