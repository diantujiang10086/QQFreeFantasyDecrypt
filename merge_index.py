# -*- coding: utf-8 -*-
"""Write out/export/PROBLEMS.md -- the export report.

It always reflects the CURRENT parser: the file list comes from plan.csv, and
every row is re-parsed here so the class, bpp and note are the real ones.

    python merge_index.py            # -> out/export/PROBLEMS.md
"""
import collections
import csv
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import dimg                                     # noqa: E402

OUT = os.path.join(HERE, 'out')

# The 39 files that failed before the 4-byte/pixel + dir-table work.
LEGACY = ('npc539701 npc539701e npc539701t npc539702 npc539702e npc539702t '
          'npc539801 npc539801e npc539801t npc539802 npc539802e npc539802t '
          'npc540001 npc540001t npc540002 npc540002t '
          'npc548801 npc548801e npc548801t npc548802 npc548802e npc548802t '
          'npc548901 npc548901e npc548901t npc548902 npc548902e npc548902t '
          'npc549001 npc549001e npc549001t npc549002 npc549002e npc549002t '
          'npc191405 npc304403 npc488903 npc61903 npc42102').split()


def rows(path):
    with open(path, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def iv(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def table(head, body):
    return '\n'.join(
        ['| ' + ' | '.join(head) + ' |',
         '|' + '|'.join('---' for _ in head) + '|'] +
        ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in body])


def main():
    plan = {r['file']: r for r in rows(os.path.join(OUT, 'plan.csv'))}
    man = json.load(open(os.path.join(OUT, 'view', 'manifest.json'), encoding='utf-8'))
    ent = {e['n']: e for e in man['entries']}
    tot = man['totals']
    by = collections.Counter(e['st'] for e in man['entries'])

    frames = sum(iv(p['frames']) for p in plan.values())
    skipped = sum(iv(p['skipped']) for p in plan.values())
    px_frames = frames - skipped
    px_bytes = sum(iv(p['px_bytes']) for p in plan.values())
    pngs = tot['pngs']
    dirs_on_disk = sum(1 for e in man['entries'] if e.get('c'))

    L = []
    A = L.append
    A('# DIMG (.gsn) 全量导出报告')
    A('')
    A(f'- 生成时间：{time.strftime("%Y-%m-%d %H:%M:%S")}')
    A('- 数据源：`out/plan.csv`（全库逐文件普查，当前解析器）、'
      '`out/view/manifest.json`（磁盘 PNG 实测）、`out/export/index.names.csv`（本轮补导实况）')
    A('- 上游只读：`F:\\WG自由幻想\\自由幻想\\data\\data\\official\\avatar\\npc`；'
      '产物目录：`gsn-format\\out\\export`（PNG，按 NPC 分目录）')
    A('- 格式说明见同目录 `..\\..\\DIMG-format.md`')
    A('')

    A('## 1. 总览')
    A('')
    A(table(['状态', '文件数', '含义'],
            [['ok', by.get('ok', 0), '五重校验全过，逐帧 w/h 与方向表均自洽'],
             ['partial', by.get('partial', 0),
              '记录与像素全部解出，但该文件的方向表整块全零 → 导出为扁平帧名'],
             ['empty', by.get('empty', 0), '纯锚点表：每条记录都无像素（正常格式变体，非错误）'],
             ['fail', by.get('fail', 0), '解析失败'],
             ['合计', sum(by.values()), '']]))
    A('')
    A(f'- 文件总数 **{len(plan):,}**，可解析率 **{(len(plan) - by.get("fail", 0)) / len(plan) * 100:.2f}%**')
    A(f'- 帧记录总数 **{frames:,}**（含 {skipped:,} 条无像素帧）；'
      f'有像素帧 = PNG 数 = **{px_frames:,}**')
    A(f'- PNG 占用 **{tot["bytes"] / 2**30:.2f} GiB**；原始像素 {px_bytes / 2**30:.2f} GiB；'
      f'压缩比 {tot["bytes"] / px_bytes:.3f}')
    A(f'- {len(plan):,} 个文件里有 **{dirs_on_disk:,}** 个产出了 PNG '
      f'（{len(plan) - dirs_on_disk:,} 个是纯锚点表，本来就没有像素）')
    if px_frames == pngs:
        A(f'- **逐帧 1:1 对账 ✓**：`Σ(frames − skipped) = {px_frames:,}` == 磁盘 PNG 数 '
          f'**{pngs:,}** → 每个有像素帧恰好一张 PNG，无缺无多。')
    else:
        A(f'- ⚠ 对账不一致：plan 有像素帧 {px_frames:,}，磁盘 PNG {pngs:,}')
    A('')

    A('## 2. 本轮修复的 39 个文件')
    A('')
    A('这三批文件在旧解析器下分别是「34 个解析失败 + 5 个方向表校验不过」，现在全部通过。'
      '下表是当前解析器对它们的实测结果（类别由本脚本重新解析判定）。')
    A('')
    body = []
    cls = collections.Counter()
    for stem in LEGACY:
        p = plan.get(stem + '.gsn')
        if not p:
            continue
        path = os.path.join(dimg.SRC, stem + '.gsn')
        try:
            r = dimg.parse(open(path, 'rb').read())
        except Exception as e:                  # noqa: BLE001
            r = {'ok': False, 'tried': [f'{type(e).__name__}: {e}']}
        if not r['ok']:
            kind = '仍失败'
        elif not r.get('dir_counts'):
            kind = '方向表全零'
        elif 'padding' in (r.get('dir_note') or ''):
            kind = '尾部空记录 padding'
        elif r.get('bpp') == 4:
            kind = '4 字节/像素'
        else:
            kind = '其它'
        cls[kind] += 1
        ok = r['ok']
        dirs = r.get('dir_counts') or []
        body.append([f'`{stem}`', p['version'], p['oh'], p['first_px'],
                     r['header']['n_frames'] if ok else iv(p['frames']),
                     r.get('skipped', iv(p['skipped'])) if ok else iv(p['skipped']),
                     r.get('bpp', 0) if ok else '',
                     f'[{dirs[0]}×{len(dirs)}]' if dirs and len(set(dirs)) == 1
                     else (','.join(map(str, dirs)) or '—'),
                     kind])
    A(table(['文件', '版本', 'oh', 'first_px', '记录数', '无像素帧', 'bpp', '方向表', '类别'],
            body))
    A('')
    A('按类别：' + '、'.join(f'**{k}** {v} 个' for k, v in sorted(cls.items())))
    A('')
    A('- **4 字节/像素（34 个）**：签名第 3 字是 `4w`、第 4 字是 `2` —— 像素是 B,G,R,A 四通道，'
      '不是 2 字节的 `A4R4G4B4`。旧解析器只认 `(w,h,2w,1)` 所以整族报「no signature」。')
    A('- **尾部空记录 padding（4 个）**：`npc191405`/`npc304403`/`npc488903`/`npc61903` 的方向表'
      '`Σn == nFrames − 尾部连续空记录数`（35/50/45/16）。')
    A('- **方向表全零（1 个）**：`npc42102` 的 24 字节方向表整块是 0，只能按「无方向映射」处理，'
      '帧写成 `f0000.png…`。')
    A('')

    empt = sorted(n for n, e in ent.items() if e['st'] == 'empty')
    A(f'## 3. 纯锚点表（{len(empt)} 个，无像素数据）')
    A('')
    A('这些文件的每条记录四字签名全为 0（无像素帧），因此不产 PNG —— 这是格式本身的用法，不是缺陷。'
      '锚点值落在记录前缀里（例如 `npc559201t` 的 `(-106,-163,256)`，256 ≈ 定点 1.0）。')
    A('')
    A('5.36 系 `oh=40` 的 6 字前缀实测为 `(v0, 0, 0, x, y, 256)`：`(x, y)` 是逐帧锚点偏移，'
      '第 6 字恒为 256（= 1.0 的 8.8 定点），`v0` 只在首条记录非零（语义未定）。'
      '详见 `DIMG-format.md` §3；核对工具 `anchors.py <stem>` / `anchor_scan.py`。')
    A('')
    A('```')
    A(', '.join(empt))
    A('```')
    A('')

    A('## 4. 仍未定案的部分')
    A('')
    A('- [ ] 4 字节像素的 RGB 次序：`A` 在 `byte3` 已确证；`B,G,R` 按「16 位是 `A4R4G4B4` → '
      '32 位是 `A8R8G8B8`」推定为内存序 **B,G,R,A**，需目视确认：'
      '`python px4cmp.py npc539801t.gsn 0` → `out\\px4cmp.png`（6 种候选序并排）。')
    A('- [ ] `npc42102` 的方向表为什么被写成全零（同版本其它文件都正常）。')
    A('- [ ] preamble 七字组 `(W,H,w,h,W,1,h)`、extra 段（`oh−28` 字节）、记录前缀字段的语义。')
    A('')

    A('## 5. 复现命令')
    A('')
    A('```powershell')
    A('cd C:\\Users\\Administrator\\Documents\\deepseek-harness\\default-workspace\\gsn-format')
    A('python selftest.py                       # 38 个样本的回归断言')
    A('python dimg.py --quiet <files...>        # 单文件解析（5 重校验）')
    A('python export.py --mode plan --quiet     # 全库只走记录、不解码像素 -> out\\plan.csv')
    A('python export.py --names out\\fail34.txt --quiet     # 只补导指定文件')
    A('python export.py --out out\\export --resume --quiet  # 全量导出（可重复执行）')
    A('python recon.py                          # PNG 数 vs 有像素帧 的 1:1 对账')
    A('python mkview.py                         # -> out\\view\\manifest.json')
    A('python merge_index.py                    # -> out\\export\\PROBLEMS.md（本文件）')
    A('python viewer_server.py --port 8791      # 查看器 -> http://127.0.0.1:8791/view/index.html')
    A('python empties.py <file...>              # 空帧/方向表边界诊断')
    A('```')
    A('')

    dst = os.path.join(OUT, 'export', 'PROBLEMS.md')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L))
    print(f'wrote {dst} ({os.path.getsize(dst) / 1024:.1f} KiB)')
    print(f'ok={by.get("ok",0)} partial={by.get("partial",0)} '
          f'empty={by.get("empty",0)} fail={by.get("fail",0)}')
    print('repair classes: ' + ', '.join(f'{k}={v}' for k, v in sorted(cls.items())))


if __name__ == '__main__':
    main()
