# 🎮 LEGO Indiana Jones 2 简体中文本地化

**《乐高印第安纳琼斯 2：冒险再续》**（LEGO Indiana Jones 2: The Adventure Continues，2009，Traveller's Tales）简体中文本地化工程。

从零逆向其自研 NXG 引擎的资源格式，实现中文文本、中文字体与 Windows 中文系统下的存档修复。工具链为**纯 Python 标准库 + ctypes**，唯一需要外部依赖的是编译代理 DLL 用的 MinGW。

> 🈶 **成品补丁可直接下载** —— GitHub Release 提供完整可安装包（含汉化 DAT），无需自行构建。
> 🛠️ **仓库同时提供全部原料与工具** —— 想自己重建、或想审校译文的玩家，这里是完整工程。

📍 发布页：<https://github.com/Janlhin/LEGO_Indiana_Jones2_Simplified_Chinese/releases/tag/2.0.0>

---

## 📦 直接下载使用

补丁成品分两个分卷发布在 GitHub Releases（单卷接近 1 GB，故拆开）：

| 分卷 | 内容 |
| --- | --- |
| `LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0_part1.zip` | 脚本、`lib/`、说明文档、`data\GAME.dat`、`data\d3d9.dll`、`data\Audio\_VO\` |
| `LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0_part2.zip` | `data\GAME2.dat` |
| `d3d9.dll` | **单独分发的代理 DLL**（56.9 KB），见下方说明 |

**两个包必须解到同一个目录**，然后右键 `安装.ps1` →「使用 PowerShell 运行」。全程约 2–4 分钟，无需管理员权限，无需改动系统区域。

📖 详细步骤见 [`patch/安装说明.md`](patch/安装说明.md)（图文版）或 `patch/安装说明.txt`（纯文本版）。

### 🧩 单独分发代理 DLL

Release 里另有一份独立的 `d3d9.dll`（58,220 字节，sha256 `1a60de56fd730e85af395b90aaa49abe5179e08a19d8d4e9e32dfce8a9276d5d`）。它就是装在 `part1.zip` 里的那一个代理 DLL，单独提供是为了**不必为此下载 1.8 GB**：

- 🛡️ 提供**存档修复**（中文系统下存档跳出 / 无法保存）
- ⚙️ 提供**设置菜单中文化**（40 个界面标签 / 80 处显示点）
- 🔧 需要它的典型场景：汉化 DAT 已装好，但 Steam 验证把游戏目录里的 `d3d9.dll` 删掉了

用法：下载后确认文件名就是 `d3d9.dll`，放进游戏目录（`...\steamapps\common\Lego Indiana Jones 2\`）覆盖即可。它不依赖 DAT，单独放进去就能工作。

> ⚠️ 游戏目录里**只需要这一个** `d3d9.dll`，不需要 `d3d9_orig.dll`（那个方案已废弃，见「值得一看的技术点」）。

---

## ✨ 汉化内容与特性

| 方向 | 内容 |
|---|---|
| 🈶 **资源格式逆向** | MkDat v4.0 归档结构、NFNT/FT2 字体结构（含内嵌 DXT5 DDS 图集）、`.GIP` 菜单包 |
| 🈶 **汉化** | 1927+ 行文本翻译、中文字体栅格化与图集打包、设置菜单标签 |
| 🈶 **运行时补丁** | `d3d9.dll` 代理：文件 API 代码页修复 + 菜单字符串指针重定向 |

- 🈶 **完整中文文本**：1927+ 行游戏文本全部汉化，覆盖主菜单、章节、角色、关卡、载具、作弊码、教程、网络联机、以及关卡编辑器（Builder）全套界面
- 🔠 **中文字体**：楷体渲染，包含 1400+ 字符（1200+ 汉字），与游戏原版斜体手写风格统一
- ⚙️ **设置菜单汉化**：40 个界面标签 / 80 处显示点。这批标签硬编码在 exe 里、不在 DAT 中，靠 `d3d9.dll` 在运行时改指针完成 —— 不改游戏文件，故不触发 Steam 校验；按键名（Left / Space 等）按设计保持英文
- 💾 **存档修复**：内置 d3d9 代理 DLL，修复中文系统下存档跳出 / 无法保存的问题（无需再把系统区域改成土耳其语）
- 🔊 **角色语音修复**：补齐 PC 版缺失的 46 个角色语音文件（跳跃 / 受伤 / 攻击 / 死亡音效）
- 🖥️ **1080p 默认分辨率**：自动写入 `pcconfig.txt`
- ⚡ **一键安装 / 卸载**：右键运行 PowerShell 脚本即可，自动备份原版文件
- 🖱️ **不挑盘符**：游戏目录四级自动定位，装在任意自定义 Steam 库路径都能找到

### 📝 译文表本体

[`translations/text.csv`](translations/text.csv) 就是打进 DAT 的那份文本表本体，**UTF-8 with BOM**，2124 行有效数据、16 列。游戏按平台读取对应语言列，我们把简体中文写进 `CHINESE` 列，同时把 `ENGLISH` 一列同步覆盖（部分调用点按英语列取值）。

当前 **1952 行已汉化**、172 行仍是西文（未收录的条目会回落到英文原文，不影响游戏运行）。

```bash
# 看看汉化覆盖率与长什么样
python - <<'PY'
import csv, io
rows = [r for r in csv.reader(io.StringIO(
    open('translations/text.csv', encoding='utf-8-sig').read())) if len(r) == 16]
head = rows[0]
zh = sum(1 for r in rows[1:]
         if any('一' <= c <= '鿿' for c in r[head.index('ENGLISH')]))
print(f'{zh} / {len(rows)-1} 行已汉化')
for r in rows[1:5]:
    print(r[head.index('ENGLISH')])
PY
```

---

## 🧰 仓库提供什么

仓库提供的是**原料 + 工具**，以及一个已经打好补丁的成品发布渠道。

| 想做什么 | 从哪儿开始 |
| --- | --- |
| 我只想装汉化 | 去 [Releases](https://github.com/Janlhin/LEGO_Indiana_Jones2_Simplified_Chinese/releases/tag/2.0.0) 下两个分卷，解到同一目录，跑 `安装.ps1` |
| 我想审校 / 补翻译文 | 改 [`translations/text.csv`](translations/text.csv)，然后按下面「自行构建」重跑 |
| 我想复现整个构建链 | 见下面「自行构建」，工具链全在 `tools/` |
| 我想研究 NXG 格式 | [`docs/research-notes.md`](docs/research-notes.md) 是踩坑记录，`tools/ttdat.py` / `ttfnt.py` 是独立实现 |

### 🔒 为什么 DAT 不入库，但成品可以下载

本仓库**不含完整的游戏 DAT**。`GAME.dat` / `GAME2.dat`（980.8 MB / 925.0 MB）不入库：

- 它们 99.5% 是原版素材，著作权属权利方，MIT 授权覆盖不到
- GitHub 单文件硬上限 **100 MB**，超了直接拒绝 push（不是警告）；Git LFS 免费账户只有 1 GB 存储 + 1 GB/月带宽，1.9 GB 装不下

但 **GitHub Release 附件**不受仓库体积约束、单文件上限 2 GB，所以成品补丁走 Release 分发 —— 那已经是「分发」而非「仓库内容」。

> 💡 游戏目录里还有 `GAME0.dat`（1105.1 MB）与 `GAME1.dat`（984.2 MB）。经解析核对，这两个归档里**不含任何文本或字体条目**，是纯资源，因此既无需汉化、也无需随包分发。

### 🖌️ 关于字体资产

汉化必须重写游戏字体（游戏渲染中文只认自带的位图字体，不认系统字体）。[`assets/fonts/`](assets/fonts/) 存放改写后的字体与文本索引，**17.4 MB**，免去持有正版的玩家重做一遍格式逆向。它们**仍属权利方素材，不在 MIT 授权范围内**，详见 [LICENSE](LICENSE)。请自行通过 Steam 购买正版游戏。

---

## 🛠️ 自行构建

### 前置

1. 通过 Steam 安装正版游戏，且至少启动过一次
2. Python 3.8+（开发用 3.13）
3. MinGW i686-w64-mingw32（仅编译代理 DLL 需要）

### 构建与安装

```bash
# 1. 生成 UI 补丁表（会读你本机的游戏 exe）
python tools/gen_ui_patch.py

# 2. 编译代理 DLL
cd src/d3d9proxy
gcc -m32 -O2 -shared -o d3d9.dll d3d9proxy.c d3d9.def \
    -Wl,--kill-at -static-libgcc -static-libstdc++

# 3. 把 DLL 放进 patch/payload/data/，然后运行安装脚本
#    Windows 上右键 patch/安装.ps1 →「使用 PowerShell 运行」
```

### 📦 打包分发件

成品包（两个分卷的 zip）由打包脚本生成 —— 它从 `patch/` 的 staging 布局还原出发行目录结构，并把本机游戏目录里的 DAT 装进 `data/`：

```bash
python tools/build_dist.py --game "D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2"
# 输出：dist/LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0_part1.zip
#       dist/LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0_part2.zip
```

各步骤的详细说明见 [`patch/README.md`](patch/README.md)（面向使用者）与 [`docs/`](docs/)（面向开发者）。

---

## 📋 版本与变更

本项目遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。**版本号的唯一来源是 `patch/payload/lib/Common.ps1` 里的 `$script:PatchVersion`**（当前 `2.0.0`）—— 那也是给终端用户看的安装包版本，仓库自身以 git tag 为准。

### 🚀 2.0.0 —— 当前版本

**⚠️ 不兼容改动（故升主版本）：**

- 🛑 **不再分发 `d3d9_orig.dll`。** 旧版代理靠把导出转发到这份系统 DLL 副本才能启动，而副本版本被硬钉在打包者的电脑上（实测 `v0.0.26101.9587` = Win11 24H2）。别人的机器上只要系统 d3d9 版本不同就直接加载失败，且症状与「文件不存在」完全一样。现在代理在运行时用 `GetSystemDirectoryW` + `IsWow64Process` 自行定位系统 d3d9 并转发，跨 Windows 版本自适应，游戏目录只需一个 `d3d9.dll`
- 📜 **安装脚本从 `.bat` 全面改为 PowerShell**（需 Windows PowerShell 5.1 或 PowerShell 7+），并移除全部注册表写入
- 🧹 **移除注册表写入**，无需手工清理

**🆕 新增功能：**

- ⚙️ **设置菜单汉化** —— 40 个界面标签 / 80 处显示点全部中文化

**🐛 问题修正：**

- 修复菜单显示为一排问号（根因是编码搞反：UI 吃 UTF-8 而非系统 ANSI）
- 修复游戏目录定位从未生效：旧 `.bat` 里的 `libraryfolders.vdf` 正则要求路径被圆括号包起，真实 vdf 里是裸字符串，正则永远匹配 0 次，实际全靠硬编码盘符兜底
- 安装脚本改为比对指纹后跳过，已装好的文件不会被重复复制 2 GB
- `backup_chs` 里的原版备份增加校验，防止把汉化版误当原版沿用（否则卸载还原不出英文）

### 📦 1.0.0

首个可用的中文本地化：主菜单、章节、角色、关卡、载具、教程、网络联机与关卡编辑器（Builder）全套界面。

> 完整的提交级变更记录见 `git log`，详见 [`CHANGELOG.md`](CHANGELOG.md)。

---

## 📁 仓库结构

```
├── src/d3d9proxy/        代理 DLL 源码（C）
│   ├── d3d9proxy.c         主逻辑：IAT hook + 菜单补丁 + 系统 d3d9 转发
│   ├── d3d9.def            16 个导出的别名映射
│   └── ui_patch.h          由 gen_ui_patch.py 生成，勿手改
├── tools/                53 个 Python 工具（标准库 + ctypes，无三方依赖）
│   └── build_dist.py         打包分发件（两个分卷的 zip）
├── translations/         译文表（KEY → 简体中文）
│   ├── translations*.py     分模块的译文字典（构建脚本读这三个）
│   └── text.csv             汉化后的游戏文本表本体（可直接查看/审校）
├── assets/fonts/         改写后的字体与文本索引（17.4 MB，非 MIT）
├── patch/                分发包骨架：安装/卸载脚本与用户文档
│   └── payload/            运行时数据（DAT、DLL 在此生成，不入库）
└── docs/                 逆向笔记与踩坑记录
```

---

## 🔬 值得一看的技术点

### ⚙️ 菜单标签汉化：改指针而非改字符串

设置菜单的英文（`Video Settings` 等）不在 DAT 里，硬编码在 exe 的 `.rdata`，且每条串后紧跟下一条、**零余量**，原地替换中文放不下。改 exe 文件又会触发 Steam DRM（`.bind` 节可执行 + `STEAM` 标记）。

解法是 exe `.data` 节里的一张**多语言 UI 字符串指针表**：每项 8 字节 `{char* text; uint32 id;}`，每种语言各有一份完整并行翻译。补丁只把英文那 80 处指针改指向自备的 UTF-8 缓冲区 —— 指针大小不变，故不受零余量限制，不碰文件、不触发 DRM。

三项前置条件缺一不可：

- 📐 **边界要划准**。表真实范围 `0xAB09F0`–`0xAB17DC`；`0xAB2C08` 之后已是着色器语义名（`viewProj` / `SEMANTIC_*`），属另一张表
- 🧮 **RVA 换算**：`.data` 段实测 `VA == RawAddr`，故**文件偏移本身就是 RVA**。按「偏移 − ImageBase」换算会整体偏 0x400000，写到无关地址上
- 🔤 **编码是 UTF-8，不是系统 ANSI**。曾误注入 GBK 导致菜单显示为一排问号 —— 而问号正是严格 UTF-8 解码器把非法字节替换成 `?` 的典型表现

### 💾 存档修复：IAT hook 文件 API

游戏是 2009 年的非 Unicode 程序，只用 ANSI 文件 API，且 exe 硬编码了 CP1252/1254 编码的存档目录名（含 `®` `™`）。中文系统（GBK/CP936）下这些字节被内核转成 `?`（非法文件名字符）→ 存档失败跳出。

代理 hook `CreateFileA` 等 9 个 A 版 API，把路径按 CP1254 转成 Unicode 后调 W 版，从而绕过内核的 GBK 转换。纯 ASCII 路径在 CP1254 下映射不变，对其它路径无副作用。

### 🧩 代理 DLL 必须自实现全部导出

游戏用 `LoadLibraryA("d3d9.dll")` + `GetProcAddress("Direct3DCreate9")` **运行时动态加载**，导入表里没有 d3d9 条目。靠文件名劫持被加载的代理必须把 d3d9 的 16 个导出全部自己实现出来。

早期版本转发到同目录的 `d3d9_orig.dll`，这要求分发包附带一份系统 d3d9 副本 —— 而那份副本的版本被硬钉在打包者电脑上，别人机器上只要系统版本不同就直接加载失败，**且症状与「文件不存在」完全一样**，极难排查。现在改为运行时 `GetSystemDirectoryW` + `IsWow64Process` 自行定位系统 d3d9 并转发，跨 Windows 版本自适应，补丁目录只需一个 `d3d9.dll`。

### 🛡️ 三重自保

每条补丁先读回指针、确认仍等于期望的英文串 VA，再逐字节 `strcmp` 比对内容，任一不符即跳过。Steam 更新或版本漂移时补丁自然退化为无操作，不会写坏内存。

---

## 🧪 开发

```bash
# 离线仿真 UI 补丁（不启动游戏，验证 80 条全部命中、无越界）
python tools/sim_ui_patch.py

# 校验导出表：16 个导出须全为真实代码，不能有 forwarder 残留
python tools/check_exports.py <dll路径>

# 检查译文用字是否都在字体里（编码问题与缺字问题要分开看）
python tools/fix_font_coverage.py
```

更多工具说明见 [`docs/tools.md`](docs/tools.md)。

---

## 🙏 致谢

### 🔊 角色语音还原

PC 版缺失了主机版才有的 `Audio_VO` 目录（角色跳跃、受伤、攻击、死亡时的咕哝声）。这部分语音的还原方案来自 PCGamingWiki 社区：

- **[Character Voice Restoration mod for Lego Indy 2](https://community.pcgamingwiki.com/files/file/2595-character-voice-restoration-mod-for-lego-indy-2/)**
  —— 原始 mod 由 **Bario The Weird** 制作，PCGamingWiki 社区页由
  **SirYodaJedi** 于 2023-03-08 提交（2023-03-10 更新，968.9 kB，
  6,144 次浏览）。它还原了主机版有、PC 版缺失的角色 vocal grunt；
  主体音效取自 `Lego Indy 1` 的未压缩 WAV，`Donovan` 与 `Spalko`
  两个目录则由 Wii 版 `Lego Indy 2` 的压缩 DSP 转码而来

本项目的语音修复沿用同一批文件（46 个，8 个角色目录），安装方式为直接覆盖 —— 无需解包 DAT，这也是 PCGamingWiki 主页面特别强调的一点。
[GOG.com 版](https://www.pcgamingwiki.com/wiki/Lego_Indiana_Jones_2:_The_Adventure_Continues) 自 2025-02-27 起已内置还原语音，购买 GOG 版可省去这一步。

### 🔬 格式研究

- [PCGamingWiki — Lego Indiana Jones 2: The Adventure Continues](https://www.pcgamingwiki.com/wiki/Lego_Indiana_Jones_2:_The_Adventure_Continues)
  —— 社区维护的游戏技术档案（配置路径、语言切换机制、高帧率崩溃、
  刷新率修正等），页面内容以 CC BY-NC-SA 授权
- Traveller's Tales 的 NXG 引擎与 [lego-tt-nxg-formats](https://github.com/tygerx/lego-tt-nxg-formats)
  社区对格式的公开研究
- [Русификатор текста 1С (доработанный)](https://steamcommunity.com/sharedfiles/filedetails/?id=2385200498)
  —— Steam 创意工坊上作者 **Rusik** 改进官方 1С 俄语本地化的补丁
  （2021，83 条评价）。作者修掉的「部分字母与单词显示成问号」问题，
  与本项目在菜单汉化上踩到的**编码判定**问题同源：游戏 UI 文本管线吃
  UTF-8，而非常见的系统 ANSI；注入 GBK 会让整串变成 `'?'`。其补丁采用
  自解压安装器并自动定位游戏路径，本项目的安装脚本沿用了类似思路
- [Tradução do LEGO Indiana Jones 2 – PC [PT-BR]](https://www.centraldetraducoes.net.br/2024/06/traducao-do-lego-indiana-jones-2-pc.html)
  —— 巴西葡语补丁（2024-06-01，Central de Traduções 社团，主笔
  **RevolutionJTG**，复核 **Joapeer**）。这是本项目**最直接的参照**：

  - 它的说明文档写着「部分菜单项未翻译，因为它们在游戏可执行文件里」
    —— 独立印证了本项目定位到的结论：菜单英文不在 DAT，而在 exe
    `.data` 节的指针表里。它因此也没汉化菜单。
  - 它用**官方工具** `TtTools.exe` 打包（`-r lij2 <in> GAME2.DAT
    <out>`），比本项目从零写的 `tools/ttdat.py` 更权威，见下方技术点。
  - 它**翻译了标题 LOGO 贴图**（`INDY2LOGO_ENGLISH_NXG.TEX` → 「A Aventura
    Continua」），而本项目未做，LOGO 仍是英文。
  - 覆盖面比本项目大：`AMERICAN` 列 1903 行已译；本项目 1860 行。
    其译文可作为校对本项目漏译条目的对照底本。

### 🛠️ 官方工具 TtTools

葡语补丁里带的那份 `TtTools.exe`（.NET 9 / WinForms，含 `TtTools.pdb`）**不是自制工具**，而是 Traveller's Tales 自家的 Lego Text Extractor 的扩展：

```
; Lego Batman Text Extractor v1.0
; TTLB1Text
TtTools - Ver 1.0 - Created By Joapeer @2024
usage: TtTools.exe <code> [parameters]
```

支持 `lb1`（乐高蝙蝠侠）、`lhp`（HP1–7）、`lij1`/`lij2`、`lsw3`、`tcs`、`nxg`，子命令含 `ExtractDat` / `ReplaceDat` / `ExtractExeText` / `**InsertExeText**` / `ExtractMenu` / `Extract2`。

值得注意：`InsertExeText` 说明**官方工具支持改写 exe 里的文本**，且内置 LZ2K 解码（`Error to decompress LZ2K`、`RNC_`），与本项目逆向出的 `.data` 节多语言指针表是同一片区域。本项目目前改的是内存里的指针、不碰 exe（Steam DRM 的 `.bind` 节会校验），而官方走的是文件改写 —— 这条路值得评估。

本项目 `tools/ttdat.py` 是独立逆向实现（仅标准库），优势是不依赖 .NET 运行时、不需要安装器；劣势是不如官方工具覆盖面广。两者可互补。

---

## 📄 权利声明与许可

原作的剧情、美术、字体与配音由 Traveller's Tales / Warner Bros. Interactive Entertainment 及各配音演员的权利方所有。

本仓库**入库的文件**分两类，性质完全不同：

| 类别 | 文件 | 授权 |
|---|---|---|
| 源代码与文档 | `src/` `tools/` `translations/translations*.py` `translations/text.csv` `patch/` `docs/` | [MIT](LICENSE) |
| 从正版游戏 DAT 中提取的素材 | `assets/fonts/`（见上文） | **不授权**，仅供持有正版者自行重建 |

汉化需要重写游戏字体（FT2 / FNT），而这些字体文件本身是从原版 DAT 中提取的二进制，**著作权属于权利方，MIT 许可覆盖不到它们**。放在仓库里是为了让持有正版的玩家不必自己逆向一遍，不构成对原作品权的授权或转让。

两个 DAT（`GAME.dat` 980.8 MB / `GAME2.dat` 925.0 MB）**不入库**，原因见上文「为什么 DAT 不入库，但成品可以下载」。成品补丁通过 GitHub Release 分发，其中绝大部分字节仍是原版素材 —— 请在持有正版的前提下使用，并支持正版。

源代码与文档以 [MIT](LICENSE) 许可。**游戏素材不在授权范围内**，请自行购买正版。

## 💖 赞助支持

如果这个汉化补丁让你玩得更顺手，欢迎用下面的方式请作者喝杯咖啡 ☕

<div align="center">

| 微信赞赏 | 支付宝 |
|:---:|:---:|
| <img src="docs/assets/sponsor-wechat.jpg" width="220" alt="微信赞赏码" /> | <img src="docs/assets/sponsor-alipay.jpg" width="220" alt="支付宝收款码" /> |

</div>

> 扫码即可，金额随意。不想掏钱也完全没关系，点个 ⭐ Star 同样是很大的支持。

---

<div align="center">

⭐ 如果这个补丁让你玩得舒服一点，点个 Star 就是最好的支持

</div>
