# `official\zipbin` 资源表格式（`.bin`）

> 结论先行：`zipbin\*.bin` 不是图像容器，而是一堆**定长行资源表**。每张表 =
> **16 字节头** + `行数 × 行宽` 的原始行数据，头部是 4 个 u32：`magic=0x5566`、
> `version=1`、`行宽`、`行数`。字段语义直接来自私服源码（`服务器\server\resources60.py`），
> 本目录 225 张表里 **224 张** 完全符合这个模型，剩下 1 张是另一种同族容器（见 §7）。

分析对象：`F:\WG自由幻想\自由幻想\data\data\official\zipbin`
参考实现：`D:\ffo\FFO7.3\packages\自由幻想10.09\服务器\`（Python 私服，`server\resources60.py`、`server\extra_tables60.py`）

---

## 1. 目录构成

| 项 | 数量 / 大小 |
|---|---|
| 文件总数 | **227**（`.bin` 225 + `client.xml` 4,239 B + `35.txt` 2 B） |
| 总字节 | **89,107,186 B = 84.98 MB** |
| 单表大小 | 2 B ～ 40,674,320 B（`ov_desc.bin`） |
| 行数合计 | **265,994 行** |
| 行宽 | **141 种**，最小 4 B、最大 31,088 B（`ov_exceptdetail.bin`） |

- 命名以 `ov_<表名>.bin` 为主；另有 `badge_peak_*.bin`、`capture_pet_para_refresh.bin`、
  `cross_boss_reward.bin`、`star_map*.bin` 等少数不带 `ov_` 前缀的表。
- `client.xml` 与表无关：它是引擎的模块声明（`<DREAMLAND AppName="Fantasy Online II">`
  + `DLLPath="GameUIModule.dll"` 之类），`35.txt` 内容就是两个字节 `35`（版本号占位）。

## 2. 容器格式（16 字节头）

```
偏移  类型   字段
0     u32    magic   = 0x5566
4     u32    version = 1
8     u32    row_size     行宽（字节）
12    u32    row_count    行数
16    ...    row_count × row_size 字节的行数据
```

恒等式：**`文件长度 == 16 + row_size × row_count`**（224/225 张表逐字节吻合）。

私服源码原文（`server/extra_tables60.py`，与 `resources60.py:table()` 同一逻辑）：

```python
magic, version, size, count = struct.unpack_from('<4I', data, 0)
if (magic, version, size) != (0x5566, 1, width) or len(data) != 16 + size * count:
    raise ValueError(f'Unexpected 6.0 resource table: {name}')
return [data[offset:offset + size] for offset in range(16, len(data), size)]
```

即：调用方**必须**事先知道行宽（`table('ov_item.bin', 269)`），否则会直接抛异常 ——
所以行宽既是容器字段，也是表结构的"接口契约"。

## 3. 行内字段怎么读

服务端的读法是「拿到行 → 按固定偏移解」：

```python
for row in table('ov_levelup.bin', 244):
    stage, profession = struct.unpack_from('<HH', row)         # @0 @2
    stats   = struct.unpack_from('<9I',  row, 4)               # @4  力量/敏捷/体力/…/HP/MP
    growth  = struct.unpack_from('<7I',  row, 64)              # @64 每级成长
    free    = struct.unpack_from('<2I',  row, 228)             # @228 自由点 / 技能点
```

`ov_levelup.bin` 共 15 行 = 5 职业 × 3 段（stage 0/1/2），实测 stage=0 的 5 行整理解出：

| 职业 | @4 起 9 个 u32 | @64 起 7 个 u32 | @228 |
|---|---|---|---|
| 1 | 12, 6, 15, 7, 0, 0, 4, **210**, 36 | 3, 1, 4, 1, 0, 0, 1 | 2, 1 |
| 2 | 10, 9, 16, 5, 0, 0, 4, **224**, 36 | 2, 2, 4, 1, 0, 0, 1 | 2, 1 |
| 3 | 10, 6, 14, 10, 0, 0, 4, **168**, 36 | 3, 1, 3, 2, 0, 0, 1 | 2, 1 |
| 4 | 4, 3, 12, 0, 12, 0, 13, 120, **117** | 1, 1, 2, 0, 3, 0, 3 | 2, 1 |
| 5 | 4, 3, 12, 0, 12, 0, 13, 120, **117** | 1, 1, 2, 0, 3, 0, 3 | 2, 1 |

（HP 210/224/168/120、道士系 MP 117 —— 数值与人族五职业一致，说明偏移解对了。）

### 已恢复的字段表

`zipbin_fields.py` 扫描 `服务器\server\*.py`，把每个 `for row in table('x.bin', W)` 之后
6,000 字符内出现的 `struct.unpack_from('<fmt', row, OFF)` / `int.from_bytes(row[a:b])` /
`row[N]` 收集起来，得到：

- **62 张表**有行解析代码，共 **320 处字段读取**；
- 其余 **163 张表**服务端从未解码（它只用 `data\client60\resources\zipbin\` 里那 88 张）。

覆盖度最高的几张（"已解释字节 / 行宽"）：

| 表 | 行宽 | 已解释 | 字段数 | 说明 |
|---|---|---|---|---|
| `ov_cmon.bin` | 88 | 86 B | 18 | 几乎整行解完（id、等级、属性、掉落…） |
| `ov_arm.bin` | 414 | 76 B | 22 | 装备主表，剩余是附加属性/描述数组 |
| `ov_godlevelup.bin` | 634 | 68 B | 18 | 神兵成长 |
| `ov_desc.bin` | 1,256 | 59 B | 20 | 文本表（32,384 行） |
| `ov_npc.bin` / `ov_task.bin` | 638 / 1,252 | 57 B | 15 | id/名字/坐标类 |
| `ov_item.bin` | 269 | 26 B | 6 | 物品主表（20,776 行） |

完整清单见 `out\zipbin_fields.csv`（列：`table, offset, size, kind, field`）。

## 3.1 导出的 CSV 用真实字段名做表头

`zipbinnames.py` 把上面的字段读取聚合成「表 → 列」映射，再按它写出**带键名的 CSV**：
每列的表头直接是私服源码里的变量名（`item_id`、`name`、`slot`、`quality`、`to_quality`…），
不再是一串 `u1, u2, u3`。

- 目前 **46 / 224 张表**能拿到真实键名（共 **191 个字段**）；其余 178 张私服从未解码，没有名字可借。
- 没名字的区间按**内容类型**标注，仍然带偏移：
  | 表头 | 含义 |
  |---|---|
  | `id` | 首 4 字节：全表唯一、严格递增、值域合理 → 判定为行 id（启发式，已验证于 `ov_level` 等表） |
  | `w@68` | 偏移 68 处的 4 字节整数（未命名） |
  | `s@8` | 偏移 8 处、内容看起来是 GBK 文本 |
  | `z@24` | 偏移 24 处全为 0（占位/保留） |
  | `x@71` | 1–8 字节的零碎字节，按 hex 原样输出 |
- 精确到字节的字段（`slot@68` 是 1 字节、`to_quality@1` 也是 1 字节）按真实宽度切列，不强行按 4 字节对齐。
- 同一张表里重名的字段会带上偏移区分，例如 `ov_levelup` 的 `strength@4`（初始属性）与 `strength@64`（每级成长）。

举例（`out\zipbin_csv\ov_levelup.csv`）：

```
row,item_id,strength,dexterity,vitality,agility,intelligence,luck,spirit,hp,mp,z@40,...
0,65536,12,6,15,7,0,0,4,210,36,0000...,3,1,4,1,0,0,1,...
```

（第 0 行 `item_id=65536` 是 `(stage=0, profession=1)` 打包成的 u32，这也说明**个别表首字段未必是 id**，
需要按源码的 `struct.unpack_from('<HH', row)` 去拆。）

## 4. 逐表清单（前 20，按行数）

| 表 | 行宽 | 行数 | 字节 |
|---|---|---|---|
| `ov_desc.bin` | 1,256 | 32,384 | 40,674,320 |
| `ov_goldsuitattr.bin` | 56 | 27,996 | 1,567,792 |
| `ov_badge_attrs_limit.bin` | 19 | 27,528 | 523,048 |
| `ov_item.bin` | 269 | 20,776 | 5,588,760 |
| `ov_combine.bin` | 140 | 18,200 | 2,548,016 |
| `ov_refinerand.bin` | 44 | 12,563 | 552,788 |
| `ov_arm.bin` | 414 | 11,608 | 4,805,728 |
| `ov_card.bin` | 248 | 11,559 | 2,866,648 |
| `ov_refine.bin` | 140 | 11,544 | 1,616,176 |
| `ov_avatararm.bin` | 11 | 7,166 | 78,842 |
| `ov_avatararmdesc.bin` | 43 | 7,166 | 308,154 |
| `ov_skilldesc.bin` | 653 | 7,139 | 4,661,783 |
| `ov_arm_star_power.bin` | 44 | 5,523 | 243,028 |
| `ov_cmon.bin` | 88 | 5,183 | 456,120 |
| `ov_ugc_trade_limit.bin` | 40 | 5,130 | 205,216 |
| `ov_findroad.bin` | 150 | 4,650 | 697,516 |
| `ov_armsplit.bin` | 68 | 3,763 | 255,900 |
| `ov_armupd.bin` | 92 | 3,229 | 297,084 |
| `ov_wishstonepresent.bin` | 58 | 2,890 | 167,636 |
| `ov_qharmattrrndplan.bin` | 15 | 2,607 | 39,121 |

（全部 225 张见 `out\zipbin.csv`；合计 265,994 行 / 89,107,186 B。）

## 5. 与私服副本的差异

`服务器\data\client60\resources\zipbin\` 里有 **88** 张表：

- 与客户端 **同名 81 张**，其中 4 张字节数不同（说明客户端更新过）：
  `ov_MultiMount` 2,307 vs 1,727、`ov_magiccard` 5,360 vs 30,304、
  `ov_mountids` 3,664 vs 3,412、`ov_petnickgrow` 221 vs 211；
- 服务器独有 7 张：`ov_petppoint`、`ov_petspecial`、`ov_resancientcard*`（全小写命名）；
- **客户端独有 144 张**（`badge_peak_*`、`star_map*`、大量 `ov_Res*`/`ov_*desc` 等）。

## 6. 行宽交叉校验（客户端表头 vs 服务器代码）

`zipbin_schema.py` 把 `table('x.bin', W)` 的声明与客户端表头比对：

- 服务器代码**显式声明 62 张**行宽；
- **60 张一致**；
- **2 张不一致**：
  - `ov_magiccard.bin`：客户端行宽 **8**，服务器按 **16** 读（客户端新版把行压了一半）；
  - `ov_petnickgrow.bin`：客户端 **41**，服务器 **39**（客户端加了 2 字节）。
  这两张用服务器逻辑去读客户端文件会直接 `Unexpected 6.0 resource table`，属于**版本漂移**，
  不是文件损坏。

## 7. 例外：`ov_avatarres.bin`（另一种同族容器）

唯一不符合 0x5566 头的表，131,428 B：

```
u16 count = 32,856        u16 version/flag = 0
count × (u16 value, u16 avatar_id)     → 4 + 32,856×4 = 131,428 ✓
```

- 32,856 条记录、103 个不同 avatar_id（456 起）；首条 `(28, 456)`，尾部大量 `(65535, 65535)` 占位；
- 语义推测：`avatar_id → 资源值` 的映射（`value` 值域 28..65534，65535 = 空），
  与 avatar 目录里的外观资源编号对应，细节未定。

## 8. 工具与复现

| 脚本（`C:\Users\Administrator\Documents\deepseek-harness\default-workspace\gsn-format\`） | 作用 |
|---|---|
| `zipbin.py` | 库 + CLI：`census [csv]` / `show <file> [n]` / `csv <file> <out>` / `compare` |
| `zipbinnames.py` | **从源码恢复列名并重导 CSV**（表头 = 真实字段名，其余按 `w@/s@/z@/x@` 标注） |
| `zipbin_schema.py` | 扫服务器代码的 `table()` 声明，与客户端表头交叉校验 → `out\zipbin_schema.csv` |
| `zipbin_fields.py` | 聚合服务器每张表的字段读取偏移 → `out\zipbin_fields.csv` |
| `zipbin_export.py` | 全部表导 CSV（`--max-rows=N` 限量；默认全量） → `out\zipbin_csv\` |
| `mkzipbin.py` | 生成浏览页 `out\zipbin\index.html`（左侧表清单、右侧前 1,500 行、带列名） |
| `srvscan.py` / `srvlines.py` | 在私服源码里按关键词定位（`zipbin`、`terrashp`、`gsa`…） |

```bat
python zipbin.py census out\zipbin.csv     :: 225 张表的宽度/行数/大小
python zipbin.py compare                   :: 与私服副本的差集
python zipbin_schema.py                    :: 行宽声明交叉校验
python zipbin_fields.py                    :: 字段读取聚合
python zipbinnames.py                      :: 恢复列名 + 重导带键名的 CSV（134.5 MB / 224 表）
python zipbin_export.py --max-rows=2000    :: 纯 u32 视图导 CSV（无列名，调参用）
python mkzipbin.py                         :: 生成浏览页
python zipbin.py csv <某表.bin> out\x.csv   :: 单表 u32 全量导出
```

浏览页：**http://127.0.0.1:8791/zipbin/index.html**
（`viewer_server.py` 的静态根是 `out/`，页面按需 `fetch('../zipbin_csv/<表名>.csv')`。）

## 9. 验证结果

| 检查 | 结果 |
|---|---|
| 容器恒等式 `16 + width*count == size` | **224 / 225** 通过（唯一例外见 §7） |
| 行宽声明交叉校验 | 62 张有声明，**60 一致 / 2 版本漂移** |
| 字段偏移可解性抽查 | `ov_levelup.bin` 5 职业初始属性/成长/点数全部落在合理值域 |
| CSV 导出 | 224 张表、265,994 行 → 134.5 MB（全量、带键名表头） |
| 列名恢复 | 46 张表 191 个字段有源码名；其余列标为 `id`/`w@`/`s@`/`z@`/`x@` |
| 浏览页 | 225 表 651 KB（内嵌每张表的列表头），HTTP 200；CSV 直链 200 |

## 10. 尚未解决

1. `ov_avatarres.bin` 的 `value` 语义（§7）——只确定是 16 位值 + avatar_id 的配对表。
2. 178 张表没有任何服务端解析代码，列名只能按内容猜出**类型**（整数/文本/全零/字节），
   语义未知；`id` 是"唯一 + 递增 + 值域合理"的启发式判定，不是源码结论。
3. `ov_magiccard` / `ov_petnickgrow` 的客户端新版行布局（行宽变了，字段位置需要重新对）。

## 11. 教训

- **别先写解析器再找文档**：这次先在私服源码里 `grep zipbin`，一次就拿到 16 字节头的官方读法；
  自己盲猜头部会浪费大量时间（`terrashp*.dat` 就是反例，见 `DIMG-format.md`）。
- 控制台是 GBK：中文路径/中文输出要 `unicode_escape` 或写 UTF-8 文件再用 `read` 工具看，
  否则 `UnicodeEncodeError`。
- `python x.py | Out-String` 之类管道在沙箱里会报 `Access is denied`，一律直连运行。
