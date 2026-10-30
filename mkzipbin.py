"""Build a static browser page for the decoded zipbin tables.

Reads out/zipbin.csv (census), out/zipbin_schema.csv and out/zipbin_fields.csv, then writes
out/zipbin/index.html which lists every table and loads its CSV on demand (viewer_server
serves `out/` as the static root, so the CSV files are fetched straight from /zipbin_csv/).
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
CSV_DIR = os.path.join(OUT, 'zipbin_csv')


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def main():
    census = {r['file']: r for r in rows(os.path.join(OUT, 'zipbin.csv'))}
    schema = {r['file']: r for r in rows(os.path.join(OUT, 'zipbin_schema.csv'))}
    fields = {}
    for r in rows(os.path.join(OUT, 'zipbin_fields.csv')):
        fields.setdefault(r['table'], []).append(r)
    entries = []
    for name in sorted(census):
        c = census[name]
        s = schema.get(name, {})
        fl = fields.get(name.lower(), [])
        csv_name = os.path.splitext(name)[0] + '.csv'
        header = []
        path = os.path.join(CSV_DIR, csv_name)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as fh:
                header = fh.readline().strip().split(',')[1:]
        entries.append({
            'n': name,
            'w': int(c['width'] or 0),
            'r': int(c['count'] or 0),
            'b': int(c['bytes'] or 0),
            'ok': c['ok'] == 'True',
            'sw': s.get('server_width', ''),
            'match': s.get('match', ''),
            'csv': os.path.join('..', 'zipbin_csv', csv_name) if header else '',
            'hdr': header,
            'f': [{'o': int(f['offset']), 't': f['kind'], 's': int(f['size']),
                   'd': f['field']} for f in fl],
        })
    payload = json.dumps({'tables': entries}, ensure_ascii=False, separators=(',', ':'))
    html = HTML.replace('__DATA__', payload).replace('__N__', str(len(entries)))
    os.makedirs(os.path.join(OUT, 'zipbin'), exist_ok=True)
    out = os.path.join(OUT, 'zipbin', 'index.html')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print('tables %d -> %s (%.1f KB)' % (len(entries), out, os.path.getsize(out) / 1024))
    print('with csv', sum(1 for e in entries if e['csv']), 'with field map', sum(1 for e in entries if e['f']))


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>zipbin 资源表浏览</title>
<style>
:root{--bg:#14161b;--panel:#1c1f26;--line:#2b3040;--fg:#d8dce6;--dim:#8b93a7;--acc:#6ea8fe}
*{box-sizing:border-box}body{margin:0;font:13px/1.5 "Segoe UI","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--fg)}
#wrap{display:flex;height:100vh}
#side{width:330px;flex:0 0 330px;border-right:1px solid var(--line);display:flex;flex-direction:column}
#side h1{font-size:14px;margin:10px 12px 6px}
#q{margin:0 12px 8px;padding:6px 8px;background:#0f1116;border:1px solid var(--line);color:var(--fg);border-radius:6px}
#list{overflow:auto;flex:1;padding:0 8px 12px}
.t{display:flex;justify-content:space-between;gap:6px;padding:5px 8px;border-radius:6px;cursor:pointer}
.t:hover{background:#232734}.t.sel{background:#2a3142;outline:1px solid var(--acc)}
.t .m{color:var(--dim);font-size:11px}.t .bad{color:#ff8080}
#main{flex:1;overflow:auto;padding:14px 18px}
h2{font-size:15px;margin:0 0 4px}#meta{color:var(--dim);margin-bottom:10px}
table{border-collapse:collapse;font:12px/1.4 ui-monospace,Consolas,monospace}
th,td{border-bottom:1px solid var(--line);padding:2px 7px;text-align:right;white-space:nowrap}
th{position:sticky;top:0;background:var(--panel);color:var(--acc);text-align:right}
td:first-child,th:first-child{text-align:left;color:var(--dim)}
.note{color:var(--dim);margin:8px 0}.fl{font:12px ui-monospace,Consolas,monospace;color:#a8b0c4}
</style></head><body><div id="wrap">
<aside id="side"><h1>zipbin 资源表 <span id="cnt"></span></h1>
<input id="q" placeholder="搜索表名…">
<div id="list"></div></aside>
<main id="main"><h2>选择一个表</h2><div class="note">左侧共 __N__ 张表。容器格式：16 字节头 &lt;4I：magic 0x5566 / version 1 / 行宽 / 行数&gt;，随后是定长行。</div></main>
</div>
<script>
const D = __DATA__;
const listEl = document.getElementById('list'), qEl = document.getElementById('q');
const mainEl = document.getElementById('main');
let cur = -1;
document.getElementById('cnt').textContent = D.tables.length;

function fmtBytes(n){ return n > 1048576 ? (n/1048576).toFixed(2)+' MB' : (n/1024).toFixed(1)+' KB'; }
function renderList(){
  const q = qEl.value.trim().toLowerCase();
  const items = D.tables.filter(t => !q || t.n.toLowerCase().includes(q));
  listEl.innerHTML = '';
  for (const t of items){
    const i = D.tables.indexOf(t);
    const d = document.createElement('div');
    d.className = 't' + (i === cur ? ' sel' : '');
    d.innerHTML = '<span>' + t.n + '</span><span class="m">' +
      (t.ok ? ('w' + t.w + ' · ' + t.r + '行') : '<span class="bad">magic 异常</span>') + '</span>';
    d.onclick = () => { cur = i; renderList(); show(t); };
    listEl.appendChild(d);
  }
}
async function show(t){
  mainEl.innerHTML = '<h2>' + t.n + '</h2><div id="meta"></div><div id="body"></div>';
  const meta = document.getElementById('meta');
  const bits = ['行宽 ' + t.w + ' B', t.r + ' 行', fmtBytes(t.b)];
  if (t.sw) bits.push('服务器声明 ' + t.sw + (t.match === 'True' ? ' ✓一致' : ' ⚠不一致'));
  meta.textContent = bits.join(' · ');
  if (t.f.length){
    const fm = t.f.map(f => f.d + '@' + f.o + ':' + f.t + f.s).join('  ');
    const p = document.createElement('div'); p.className = 'fl';
    p.textContent = '私服源码里已命名的字段: ' + fm;
    meta.appendChild(p);
  }
  const named = t.hdr.filter(h => !/^[wszx]@/.test(h) && h !== 'id');
  const p2 = document.createElement('div'); p2.className = 'fl';
  p2.style.color = '#7f8798';
  p2.textContent = 'CSV 列名：已命名 ' + named.length + ' 个 / 共 ' + t.hdr.length +
    ' 列；未命名的按内容标成 w@偏移(整数) / s@偏移(文本) / z@偏移(全零) / x@偏移(字节)';
  meta.appendChild(p2);
  if (!t.ok){
    document.getElementById('body').innerHTML = '<div class="note">这张表的 magic 不是 0x5566，属于另一种容器，未导出 CSV。</div>';
    return;
  }
  if (!t.csv){
    document.getElementById('body').innerHTML = '<div class="note">未生成 CSV（可用 python zipbin_export.py 重新导出）。</div>';
    return;
  }
  const res = await fetch(t.csv);
  const text = await res.text();
  const lines = text.trim().split('\n');
  const head = lines[0].split(',');
  const body = lines.slice(1, 1501).map(l => l.split(','));
  const tb = document.createElement('table');
  const tr = document.createElement('tr');
  for (const h of head){ const th = document.createElement('th'); th.textContent = h; tr.appendChild(th); }
  tb.appendChild(tr);
  for (const r of body){
    const row = document.createElement('tr');
    for (const c of r){ const td = document.createElement('td'); td.textContent = c; row.appendChild(td); }
    tb.appendChild(row);
  }
  const wrap = document.getElementById('body');
  wrap.innerHTML = '<div class="note">显示前 ' + body.length + ' 行（共 ' + t.r + ' 行；完整数据见 ' + t.csv + '）</div>';
  const sc = document.createElement('div'); sc.style.overflow = 'auto'; sc.style.maxHeight = 'calc(100vh - 190px)';
  sc.appendChild(tb); wrap.appendChild(sc);
}
qEl.oninput = renderList;
renderList();
</script></body></html>"""


if __name__ == '__main__':
    main()
