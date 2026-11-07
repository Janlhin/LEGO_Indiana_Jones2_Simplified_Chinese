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
| `stuff\text\<lang>.txt` | **角色名文本文件**，引擎按当前语言拼路径加载（`stuff\text\` 是格式前缀）。内容是别的游戏（星战等）的残留，但**在位**，且英文槽读的 `english.txt` 已被本项目汉化 —— 详见 §2.3.1 |
| `gui\Font\<font>.txt` | 字体网格定义（UTF-16LE），逐行列出字符 |
| `gui\Font\<font>_pc.fnt` | 位图字体容器（内嵌 DDS 图集） |

`text.csv` 列头：
`LABEL, PLATFORM, TYPE, ENGLISH, AMERICAN, FRENCH, GERMAN, SPANISH,
ITALIAN, DANISH, JAPANESE, RUSSIAN, HUNGARIAN, CZECH, POLISH`

### 2.3 语言 / 字体选择机制（exe 逆向）

- 导入了 `GetUserDefaultLangID` → **自动跟随 Windows 系统语言**

**两段结构**（2026-11-07 用指针反查重新定位，此前记录的「0x903A80..0x9040B0 一条表」
是把字符串块和记录表算在了一起，条目数也算错了）：

| 区域 | raw 偏移 | 内容 |
|---|---|---|
| 字符串块 | `0x903A80` | 每条语言 36 字节 = 字体名/小写名/显示名 各 12 字节定长槽 |
| 记录表 | `0x903D50` | **21 条 × 40 字节** `{ u32 id, char* 显示名, char* 小写名, char* 字体名, float[6] }` |

**全部 21 条（按 id 排序）** —— 注意 `id=3 American` 的小写名也是 `english`：

| id | 显示名 | 小写名 | 字体名 |
|---|---|---|---|
| 0 | Japanese | japanese | font_jpn |
| 1 | Korean | korean | font_kor |
| 2 | English | english | font |
| **3** | **American** | **english** | **font** |
| 4 | Deutsch | german | font |
| 5 | Français | french | font |
| 6 | Español | spanish | font |
| 7 | Italiano | italian | font |
| 8 | Nederlands | dutch | font |
| 9 | Portuguese | portuguese | font |
| 10 | Dansk | danish | font |
| 11 | Norwegian | norwegian | font |
| 12 | Swedish | swedish | font |
| 13 | Finnish | finnish | font |
| 14 | Greek | greek | font |
| 15 | Czech | czech | font_cze |
| 16 | Polish | polish | font_pol |
| 17 | Russian | russian | font_rus |
| 18 | Brazilian | brazilian | font |
| **19** | **Chinese** | **chinese** | **font_chi** |
| 20 | Hungarian | hungarian | font_hun |

`0x904098` 处还有一条 id=21 的空记录（字段全 0），是表尾终止项，不是语言。

**两条结论**：

1. **没有繁体槽。** 21 条里只有 `chinese` 一个中文槽，没有 `taiwanese` / `traditional`
   / `zh-TW` 之类的条目。简繁能否共存的问题由此确定（见 `TODO.md` 第 2 项）。
2. **`English` 与 `American` 共用 `stuff\text\english.txt`。** 两条记录的小写名都是
   `english`，所以「美式」不是独立文件，只是在同一份 character text 上的覆盖层。

- 小写名与 `text.csv` 的**列名一一对应**（JAPANESE/RUSSIAN/HUNGARIAN/
  POLISH/CZECH 列都存在）⇒ 引擎按语言取 `text.csv` 的对应列
- 中文字段齐备，但游戏**没有** `CHINESE` 列，也没有 `font_chi*` 文件
  ⇒ 中文 Windows 下游戏回退到英文

**汉化落点 = 给 `text.csv` 增加 `CHINESE` 列 + 提供中文字体。**

### 2.3.1 `stuff\text\<lang>.txt` 在不在生效链上（2026-11-07 实测）

这是 `TODO.md` 第 3 项的静态部分，结论：**在，但读的是当前语言的对应文件**。

exe 里的证据（都是 raw 偏移）：

| 偏移 | 字符串 |
|---|---|
| `0x903BF0` | `Fran` + `çais`（`ç` 是非 ASCII，纯 ASCII 扫描时会被切断成两段，非截断） |
| `0x903C50` | `english` |
| `0x903C60` | `gui\font\` |
| `0x903C6C` | **`stuff\text\`**（格式前缀，紧随语言名之后） |
| `0x903C78` | `***TEXT STRING ERROR*** No valid name entry in character text file` |

即引擎用 `stuff\text\` + 语言小写名 拼出**角色名文本文件**路径，并由
「character text file」这句错误串佐证其用途。另一个字面量 `american.txt` 在
`0x905D74`，与平台表 `wii/psp/ps3/ps2/360/trc.csv/american` 相邻。

**各文件实测状态**（`GAME2.dat` 内，本机安装的 v2.1.0）：

| 文件 | 大小 | 汉字 | 假名 | 判定 |
|---|---|---|---|---|
| `english.txt` | 26,821 | **2,337** | 0 | 已被汉化（480 行，id 190..990） |
| `american.txt` | 323 | 75 | 0 | 已被汉化（仅 7 条覆盖：181/185/544/656/802/818/860） |
| `japanese.txt` | 43,464 | 2,455 | **8,340** | **未动**，是别的游戏的日文 |
| `french.txt` / `german.txt` | 38,039 / 39,643 | 0 | 0 | 未动 |

**`japanese.txt` 的真实身份**：981 行，首行 `20 "LEGO スタ-・ウォ-ズ II"`，
片假名 4,903 + 平假名 3,437，全文 **0 次**提及 Indiana / インディ / スカル。
即**乐高星球大战 II 的日文**，是 TT Games 共用引擎资产残留，与 Indy2 无关。

> 之前记录的「含 2455 个汉字」是被 UTF-8 解码后的统计口径误导 —— 那是日文里的
> **汉字（kanji）**，不是中文。加上片假名/平假名后才看得出它整份是日文。

**为什么能断定英文槽不读它**：当前 v2.1.0 构建**完全没有触碰** `japanese.txt`
（工具链里没有任何一处写它），而汉化用户看到的角色名是中文的 ⇒ 英文槽读的必然是
`english.txt`。若 `japanese.txt` 在链上，玩家会看到星战的日文人名。

**`assets/fonts/japanese.txt` 是误命名**：27,680 字节、480 行、id 190..990、
注释头与 `english.txt` 完全一致、0 假名 / 1,206 汉字 / 14,800 拉丁字母 —— 它是
**早期「日语槽方案」时期的 `english.txt` 快照**（那时引擎读 `japanese.txt`，
所以得给这份文件填中文），不是日文文件，也不是 DAT 里那份。此前「两者对不上」
的记录由此解释清楚。

**因此**：繁体版**不需要**翻译 `japanese.txt`；反过来，若用户机器上残留
`LanguageVal=1041`（旧版 `tools/set_language.py` 写过），游戏会切到日语槽 →
读星战日文 + `text.csv` 的 195 条真实日文。这是旧方案的遗留风险，发布版应确保
语言值为 1033（本机 HKCU/HKLM 三处实测均为 1033）。

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

---

## 9. 巴西葡语补丁的核实（2026-10-14）

[Central de Traduções 的 PT-BR 补丁](https://www.centraldetraducoes.net.br/2024/06/traducao-do-lego-indiana-jones-2-pc.html)
（2024-06-01，2.49 MB，Inno Setup 分发）是最有价值的外部参照 ——
它的安装器里带着**官方工具**，且其说明文档直接印证了本项目的核心结论。

### 9.1 官方工具 TtTools.exe

`Traducao/tool/TtTools.{exe,dll,pdb}`（.NET 9 / WinForms，145 KB exe +
21 KB dll）。从元数据字符串可确认它**不是自制工具**，而是 TT 自家
Lego Text Extractor 的扩展：

```
; Lego Batman Text Extractor v1.0      ← 原始工具名
; TTLB1Text                          ← TT 自己的文本格式标记
TtTools - Ver 1.0 - Created By Joapeer @2024
usage: TtTools.exe <code> [parameters]
```

| 项 | 值 |
|---|---|
| 支持游戏码 | `lb1`（乐高蝙蝠侠）、`lhp`（HP 1–7）、`lij1`、`lij2`、`lsw3`、`tcs`、`nxg` |
| 子命令 | `ExtractDat` / `ReplaceDat` / `ExtractExeText` / **`InsertExeText`** / `ExtractMenu` / `Extract2` |
| 内部类 | `TtDatHelper`、`TtTextHelper` |
| 压缩 | 内置 LZ2K 解码（`Error to decompress LZ2K`）、`RNC_` |
| 打包命令 | `TtTools.exe -r lij2 <输入目录> GAME2.DAT <输出 DAT>` |

两个对本项目有直接意义的点：

1. **`InsertExeText` 存在** —— 官方支持**改写 exe 内的文本**。本项目目前
   改的是运行时内存里的指针、不碰 exe（Steam DRM 的 `.bind` 节可执行 +
   `STEAM` 标记会校验文件）。官方走文件改写，说明这条路在技术上可行，
   值得评估 —— 但要确认 Steam 版 exe 是否可安全改写而不触发校验。
2. **官方工具的覆盖面广于本项目**。本项目 `tools/ttdat.py` 是独立逆向
   （仅标准库、无需 .NET），优势是零依赖、便于脚本化；劣势是不如官方
   工具完整。两者互补而非替代。

### 9.2 独立印证：菜单文本确实不在 DAT

葡语补丁的说明文档原文：

> Alguns termos do Menu estão sem tradução porque estão no executável
> do jogo.
> （部分菜单项未翻译，因为它们在游戏可执行文件里。）

这与本项目逆向出的结论**完全一致**：设置菜单英文硬编码在 exe
`.data` 节的多语言指针表中（`0xAB09F0`–`0xAB17DC`，80 处指针 / 40 个
标签）。核对其文件清单也印证了这一点 —— 补丁只投放到 DAT 内部路径
（`GUI/FONT/`、`GUI/LEGAL/`、`GUI/TEXTURES/`、`stuff/text/`），
**没有任何 exe 文件**。因此它同样没能汉化菜单。

**本项目补上了菜单标签这一块**（见 README「菜单标签汉化」）。

### 9.3 译文写在 AMERICAN 列，不是 ENGLISH 列

逐列统计含葡语特征字符（`ãõçáéíóúâêôàü`）的行数：

| 列名 | 原版 | PT-BR 补丁 | 增量 |
|---|---|---|---|
| ENGLISH | 1 | 1 | **+0** |
| **AMERICAN** | 1 | 827 | **+826** |
| GERMAN | 383 | 387 | +4 |
| 其余列 | — | — | +0 |

而按 LABEL 对齐后统计 `AMERICAN` 列**实际改动 1903 行**。
即：葡语补丁**完全没有动 `ENGLISH` 列**，译文全写进 `AMERICAN` 列。

这与 9.2 吻合 —— `ENGLISH` 列对应菜单，而菜单在 exe 里；游戏在
非英语系统上取的其实是 `AMERICAN` 列的文本，所以把葡语填进
`AMERICAN` 就能覆盖绝大多数界面文本，一行 exe 都不用改。

**对本项目的直接价值**：

- 该补丁 `AMERICAN` 列覆盖 **1903 行**，本项目 1860 行 → 其译文可作为
  校对本项目漏译条目的对照底本
- 本项目目前把中文同时写进 `CHINESE` 与 `ENGLISH` 两列。这个选择比
  葡语补丁更稳（`ENGLISH` 列在任何语言环境下都是兜底），但也意味着
  **若目标用户系统语言映射到非中文槽位，`ENGLISH` 列的中文会生效** ——
  这正是我们想要的，可视为一个刻意的「无条件汉化」设计

### 9.4 其他差异

- **LOGO 未汉化**：补丁投了 `GUI/LEGAL/INDY2LOGO_US_NXG.TEX` 与
  `GUI/TEXTURES/INDY2LOGO_ENGLISH_NXG.tex`（把标题 LOGO 译成
  「A Aventura Continua」），本项目未处理，LOGO 仍为英文
- **片尾字幕独立成文件**：补丁新增了 `english_credits.txt`（26,726 字节），
  格式为 `<条目> <类别> <r> <g> <b>`（如 `company colour 1.0 1.00 1.0`）。
  它没改 `english.txt`（与原版**逐字节相同**），而是另加一个带颜色参数的
  字幕文件 —— 说明原版的 `english.txt` 里片尾部分不是纯文本，TT 的工具
  需要单独的文件形态才能带颜色
- **`font_chi` 槽位**：本项目在 `2.3` 提到 exe 有 id=19 的 Chinese 槽位
  但无 `font_chi*` 文件。葡语补丁同样没有提供该字体文件
- **安装器行为**：其 `install_script.iss` 里 `[Run]` 会
  `xcopy` 把 `Backup\GAME.DAT` 复制到临时目录再打包 —— 即
  **安装时依赖一份已存在的原版备份**，且从 `[Registry]` 看它写
  `HKLM\Software\Central de Traduções`（需管理员）。本项目的
  `安装.ps1` 已改为运行时 `GetSystemDirectoryW` 定位 + 自动备份，
  不写注册表、不依赖预置备份
