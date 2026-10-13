# 乐高印第安纳·琼斯 2（LEGO Indiana Jones 2）汉化工程

目标：把 3DM/游民星空发布的《乐高侏罗纪世界》汉化补丁思路迁移到
**LEGO Indiana Jones 2**，为其实施中文本地化。

结论先行：**侏罗纪世界的汉化补丁无法直接用于 Indy2**，两者引擎不同。
本项目改为逆向 Indy2 自身的本地化体系，从零构建中文文本与中文字体。

---

## 1. 关于那个 RAR

`Gamersky-LEGO.Jurassic.World.CHS.Patch.v1.0.rar` 内只有一个
8.9 MB 的自解压安装器 `LEGO.Jurassic.World.CHS.Patch.v1.0.exe`。

| 检查项 | 结果 |
|---|---|
| PE 结构 | 32 位 MSVC，4 节，映像 933 KB |
| overlay | 7.6 MB，熵 **8.0000**（加密/强压缩） |
| 容器魔数 | 7z / RAR4 / RAR5 / ZIP / ZSTD / BZIP2 / CAB 全部未命中 |
| Bandizip 识别 | `Unknown archive` |

其载荷对《侏罗纪世界》（2015，新版 DAT + `.FT2` 字体）生效，
对 Indy2（2009，旧版 DAT + `.FNT` 字体）既不能复制、也不兼容格式。
因此本文档其余部分全部围绕 Indy2 自身体系展开。

---

## 2. 逆向成果（全部有字节级证据）

### 2.1 归档容器（`MkDat v4.0`，infoType = -3）

```
[0x000] u32 infoOffset      信息块在文件尾部的起始偏移
[0x004] u32 infoSize        信息块大小（infoOffset + infoSize == fileSize）
[0x008] char  "BEGIN_APP_ID_STRING" "MkDat v4.0" "END_APP_ID_STRING"
[0x400]                     数据区起始（所有文件 256 字节对齐）

信息块：
  u32 infoType == -3
  u32 fileCount
  fileCount × 16B  { u32 offset>>8, u32 zsize, u32 size, u8[3] packed, u8 offset&0xFF }
  u32 nameCount
  nameCount × 8B   { i16 next, i16 prev, i32 nameOffset }   ← 名字树
  u32              nameBlobSize + 8
  nameBlob         全部名字字符串
  u32              自相对指针
  fileCount × u32  CRC 表（升序，自研哈希，非 FNV）
  尾部若干字节
```

关键点：**叶子名字条目的 `next` 字段就是文件索引**（`next<=0` → `-next`）。
在 GAME.dat 上验证：7659 个叶子 ↔ 7659 条文件记录，索引 0..7658
无缺失、无重复。据此命名匹配率从 1/7659 提升到 **7659/7659**。
（这使得"改内容而不改名"的重建方案成为可能——无需破解自研哈希。）

### 2.2 本地化体系

| 文件 | 作用 |
|---|---|
| `stuff\text\text.csv` | **真正的运行时文本库**，2106 行，15 列 |
| `stuff\text\<lang>.txt` | 旧流程产物，Indy2 中为残留（内容是哈利波特/蝙蝠侠） |
| `gui\Font\<font>.txt` | 字体网格定义（UTF-16LE），逐行列出字符 |
| `gui\Font\<font>_pc.fnt` | 位图字体容器（内嵌 DDS 图集） |

`text.csv` 列头：
`LABEL, PLATFORM, TYPE, ENGLISH, AMERICAN, FRENCH, GERMAN, SPANISH,
ITALIAN, DANISH, JAPANESE, RUSSIAN, HUNGARIAN, CZECH, POLISH`

### 2.3 语言 / 字体选择机制（exe 逆向）

- 导入了 `GetUserDefaultLangID` → **自动跟随 Windows 系统语言**
- `.rdata @ 0x903A80..0x9040B0` 存在一张 40 字节/条的语言表：
  `{ u32 id, char* 显示名, char* 小写名, char* 字体名, float[6] }`

| id | 显示名 | 小写名 | 字体名 |
|---|---|---|---|
| 0 | Japanese | japanese | font_jpn |
| 17 | Russian | russian | font_rus |
| **19** | **Chinese** | **chinese** | **font_chi** |
| 20 | Hungarian | hungarian | font_hun |

- 小写名与 `text.csv` 的**列名一一对应**（JAPANESE/RUSSIAN/HUNGARIAN/
  POLISH/CZECH 列都存在）⇒ 引擎按语言取 `text.csv` 的对应列
- 中文字段齐备，但游戏**没有** `CHINESE` 列，也没有 `font_chi*` 文件
  ⇒ 中文 Windows 下游戏回退到英文

**汉化落点 = 给 `text.csv` 增加 `CHINESE` 列 + 提供中文字体。**

### 2.4 字体容器 `.FNT`

```
[0x00] u32 payloadSize        == fileSize - 64
[0x04] u32 12
[0x08] u32 ddsOffset - 8
[0x18] u32 glyphTableEnd
[0x1C] u32 N1                 == 网格字符数 + 3
[0x20] u32 N2                 == N1 + 2
[0x24] f32 lineHeight         （网格 height）
[0x28] f32 base               （网格 base）
[0x40] u32 0 / u32 28         ← 8 字节子头
[0x48] N × 12B                字形度量 { f32 x, f32 y, f32 advanceWidth }
glyphTableEnd                 中间块：+0x20/+0x24 为纹理宽高，其后为 HLSL 串
ddsOffset                     内嵌 DDS（DXT5 + 完整 mip 链）
fileSize-64                   64 字节尾块
```

度量布局用**图集 alpha 投影反查**交叉验证：
PS2_FONT_J_PC.FNT（1024×1024，23 行 × 44px）与 font_pc.fnt（512×512，
10 行 × 48px）的 x 坐标与投影结果完全一致。

---

## 3. 实施方案

1. `text.csv` 追加 `CHINESE` 列（追加在末尾，不动既有列序）
2. 用 GDI32（ctypes）把微软雅黑栅格化进 2048×2048 DXT5 图集，
   按 `.FNT` 结构组装出中文字体，替换 `gui\Font\font_pc.fnt` + `font.txt`
3. 重建 GAME.dat / GAME2.dat：**不改名、不加名**，只改 16 字节文件记录
   （因此完全绕开自研哈希问题）
4. exe 打 4 字节补丁：CHINESE 槽位字体名指针 `font_chi` → `font`

**安全设计**：`CHINESE` 列中未翻译的行回填英文原文 ⇒ 不会出现空白串；
字体字符集 = 全部用到的中文字符 + 全部 ASCII。

---

## 4. 离线验证结果（全部通过）

| 验证 | 结果 |
|---|---|
| 4 个 DAT 解析 | infoType=-3，计数自洽，命名 1237/1237 ~ 7659/7659 |
| 原字体图集解码 | PNG 目视正确（ASCII + 日文汉字） |
| 自制字体回读 | 头/DDS/度量/网格全部一致，**PASS** |
| 自制字体图集目视 | ASCII + 中文（乐高印第二部/开始游戏/选项…）正确 |
| 重建 DAT 抽样 | 各 300 个未改动文件 **300/300 字节级一致** |
| 新 text.csv | 16 列，CHINESE 列就位，375 行中文 |

---

## 5. 目录结构

```
work/
  tools/    ttdat.py           DAT 读取器（读+定位）
            bc3.py             纯标准库 BC3/DXT5 编解码 + PNG 读写
            ttfnt.py           .FNT 读取器
            gdi_font.py        ctypes+GDI32 字形栅格化
            build_font.py      中文字体构建器
            build_text.py      text.csv 注入 CHINESE 列
            rebuild_dat.py     DAT 重建器
            patch_exe.py       exe 4 字节补丁
            verify_fnt.py      字体自检
            （其余为逆向过程脚本，保留作证据链）
  02_extract/  从 GAME2.dat 抽取的原始文本与字体
  03_atlas/    原始字体图集 PNG
  04_build/    ★ 汉化载荷：GAME.dat / GAME2.dat / LEGOIndy2.exe
  05_text/     翻译表 translations.py
  docs/        格式逆向笔记
```

## 6. 已知限制

- **未实机验证**：所有结论均来自静态逆向与字节级自洽性检查，
  需要启动游戏确认（见下）。
- 翻译覆盖 375 / 2106 行（菜单、选项、按键设置、存读档、章节枢纽、
  印第专属提示）；其余行显示英文。补翻译只需改
  `05_text/translations.py` 后重跑 `build_text.py` 与 `rebuild_dat.py`。
- 哈希算法未破解 ⇒ 不能向 DAT 添加新文件名，只能改内容。
- 若系统语言被引擎映射到非中文槽位，文本会显示英文但字体正常。

## 7. 实机验证步骤

1. 备份 `GAME.dat`、`GAME2.dat`、`LEGOIndy2.exe`
2. 用 `04_build/` 内三个文件覆盖游戏目录同名文件
3. 启动游戏，检查：
   - 主菜单是否出现中文（新的游戏 / 选项 / 退出…）
   - 文字是否有乱码或空白方块
   - OPTION→Control Setup 按键页是否为中文
4. 如需还原：用备份覆盖回去即可

---

## 8. 部署状态（已完成）

- `GAME.dat` / `GAME2.dat` / `LEGOIndy2.exe` 已写入游戏目录，
  MD5 与 `04_build` 构建产物逐一比对一致
- 原始文件已备份到 `work/backup/`（975 MB + 906 MB + 16 MB）
- 还原命令：
  `python work/tools/deploy.py --restore --game "D:/SteamLibrary/steamapps/common/Lego Indiana Jones 2"`
- 游戏内抽查：`gui\Font\font_pc.fnt` = 5,600,520 字节（中文字体）；
  `stuff\text\text.csv` 列头含 `CHINESE`
