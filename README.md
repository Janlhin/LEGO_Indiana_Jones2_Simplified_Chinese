# lego-indy2-chs

《乐高印第安纳琼斯 2：冒险再续》（LEGO Indiana Jones 2: The Adventure
Continues，2009，Traveller's Tales）简体中文本地化工程。

从零逆向其自研 NXG 引擎的资源格式，实现中文文本、中文字体与 Windows
中文系统下的存档修复。工具链为纯 Python 标准库 + ctypes，唯一需要外部
依赖的是编译代理 DLL 用的 MinGW。

> **本仓库不含完整的游戏 DAT。** `GAME.dat` / `GAME2.dat`（各约 1 GB）
> 不入库 —— 它们 99.5% 是原版素材，且远超 GitHub 单文件 100 MB 上限。
> 唯一的例外是 [`assets/fonts/`](assets/fonts/)：17.4 MB 改写后的字体与
> 文本索引，让持有正版的玩家不必重做格式逆向。它们**仍属权利方素材，
> 不在 MIT 授权范围内**。请自行通过 Steam 购买正版游戏。
> 详见 [LICENSE](LICENSE)。

---

## 这是什么

一个「补丁生成器」，不是补丁成品。运行工具后会在你自己的游戏副本上
生成中文 DAT 并安装，产出物仅供你个人使用。

三类工作：

| 方向 | 内容 |
|---|---|
| **资源格式逆向** | MkDat v4.0 归档结构、NFNT/FT2 字体结构（含内嵌 DXT5 DDS 图集）、`.GIP` 菜单包 |
| **汉化** | 1927+ 行文本翻译、中文字体栅格化与图集打包、设置菜单标签 |
| **运行时补丁** | `d3d9.dll` 代理：文件 API 代码页修复 + 菜单字符串指针重定向 |

### 已汉化的文本

[`translations/text.csv`](translations/text.csv) 就是打进 DAT 的那份文本表
本体，**UTF-8 with BOM**，2124 行有效数据、16 列。游戏按平台读取对应语言列，
我们把简体中文写进 `CHINESE` 列，同时把 `ENGLISH` 一列同步覆盖（部分调用点
按英语列取值）。

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

当前 1952 行已汉化、171 行仍是西文（未收录的条目会回落到英文原文，不影响
游戏运行）。

### 字体资产

汉化必须重写游戏字体（游戏渲染中文只认自带的位图字体，不认系统字体）。
[`assets/fonts/`](assets/fonts/) 存放改写后的字体与文本索引，**17.4 MB**，
免去持有正版的玩家重做一遍格式逆向。逐字节原样入库（`.gitattributes` 里标了
`-text`），详见该目录的 [README](assets/fonts/README.md)。

### 关于两个 DAT

改动其实极小 —— 全部汉化只碰了 **12 个文件**：

| DAT | 文件数 | 原始体积 | 改动文件 | 改动量 |
|---|---|---|---|---|
| `GAME.dat` | 7659 | 1849.5 MB | 3 | 8.8 MB（0.47%） |
| `GAME2.dat` | 1237 | 1526.1 MB | 9 | 19.8 MB（1.30%） |

两个 DAT 本身**不入库**，原因是技术上的硬限制而非选择：

- GitHub 单文件上限 **100 MB**，超了直接拒绝 push（不是警告）。两个 DAT
  分别是 981 MB 和 925 MB
- Git LFS 单文件能到 2 GB，但**免费账户只有 1 GB 存储 + 1 GB/月带宽**，
  1.9 GB 装不下，得付费
- GitHub Release 附件上限 2 GB 且不计入仓库体积，但那是「分发」，
  不是「仓库内容」，也不适合当上游依赖

所以要么各自跑工具在自己的正版副本上重建（推荐，本来就该如此），
要么自行解决存储与托管。仓库提供的是**原料 + 工具**，不是 2 GB 的成品。

---

## 快速上手

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

各步骤的详细说明见 [`patch/README.md`](patch/README.md)（面向使用者）与
[`docs/`](docs/)（面向开发者）。

---

## 仓库结构

```
├── src/d3d9proxy/        代理 DLL 源码（C）
│   ├── d3d9proxy.c         主逻辑：IAT hook + 菜单补丁 + 系统 d3d9 转发
│   ├── d3d9.def            16 个导出的别名映射
│   └── ui_patch.h          由 gen_ui_patch.py 生成，勿手改
├── tools/                84 个 Python 工具（标准库 + ctypes，无三方依赖）
├── translations/         译文表（KEY → 简体中文）
│   ├── translations*.py     分模块的译文字典（构建脚本读这三个）
│   └── text.csv             **汉化后的游戏文本表本体**（可直接查看/审校）
├── assets/fonts/         改写后的字体与文本索引（17.4 MB，非 MIT）
├── patch/                分发包骨架：安装/卸载脚本与用户文档
│   └── payload/            运行时数据（DAT、DLL 在此生成，不入库）
└── docs/                 逆向笔记与踩坑记录
```

---

## 值得一看的技术点

### 菜单标签汉化：改指针而非改字符串

设置菜单的英文（`Video Settings` 等）不在 DAT 里，硬编码在 exe 的
`.rdata`，且每条串后紧跟下一条、**零余量**，原地替换中文放不下。改 exe
文件又会触发 Steam DRM（`.bind` 节可执行 + `STEAM` 标记）。

解法是 exe `.data` 节里的一张**多语言 UI 字符串指针表**：每项 8 字节
`{char* text; uint32 id;}`，每种语言各有一份完整并行翻译。补丁只把英文
那 80 处指针改指向自备的 UTF-8 缓冲区 —— 指针大小不变，故不受零余量
限制，不碰文件、不触发 DRM。

三项前置条件缺一不可：

- **边界要划准**。表真实范围 `0xAB09F0`–`0xAB17DC`；`0xAB2C08` 之后已是
  着色器语义名（`viewProj` / `SEMANTIC_*`），属另一张表
- **RVA 换算**：`.data` 段实测 `VA == RawAddr`，故**文件偏移本身就是
  RVA**。按「偏移 − ImageBase」换算会整体偏 0x400000，写到无关地址上
- **编码是 UTF-8，不是系统 ANSI**。曾误注入 GBK 导致菜单显示为一排问号
  —— 而问号正是严格 UTF-8 解码器把非法字节替换成 `?` 的典型表现

### 存档修复：IAT hook 文件 API

游戏是 2009 年的非 Unicode 程序，只用 ANSI 文件 API，且 exe 硬编码了
CP1252/1254 编码的存档目录名（含 `®` `™`）。中文系统（GBK/CP936）下
这些字节被内核转成 `?`（非法文件名字符）→ 存档失败跳出。

代理 hook `CreateFileA` 等 9 个 A 版 API，把路径按 CP1254 转成 Unicode
后调 W 版，从而绕过内核的 GBK 转换。纯 ASCII 路径在 CP1254 下映射不变，
对其它路径无副作用。

### 代理 DLL 必须自实现全部导出

游戏用 `LoadLibraryA("d3d9.dll")` + `GetProcAddress("Direct3DCreate9")`
**运行时动态加载**，导入表里没有 d3d9 条目。靠文件名劫持被加载的代理
必须把 d3d9 的 16 个导出全部自己实现出来。

早期版本转发到同目录的 `d3d9_orig.dll`，这要求分发包附带一份系统 d3d9
副本 —— 而那份副本的版本被硬钉在打包者电脑上，别人机器上只要系统版本
不同就直接加载失败，**且症状与「文件不存在」完全一样**，极难排查。现在
改为运行时 `GetSystemDirectoryW` + `IsWow64Process` 自行定位系统 d3d9
并转发，跨 Windows 版本自适应，补丁目录只需一个 `d3d9.dll`。

### 三重自保

每条补丁先读回指针、确认仍等于期望的英文串 VA，再逐字节 `strcmp`
比对内容，任一不符即跳过。Steam 更新或版本漂移时补丁自然退化为无操作，
不会写坏内存。

---

## 开发

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

## 致谢

### 角色语音还原

PC 版缺失了主机版才有的 `Audio_VO` 目录（角色跳跃、受伤、攻击、死亡
时的咕哝声）。这部分语音的还原方案来自 PCGamingWiki 社区：

- **[Character Voice Restoration mod for Lego Indy 2](https://community.pcgamingwiki.com/files/file/2595-character-voice-restoration-mod-for-lego-indy-2/)**
  —— 原始 mod 由 **Bario The Weird** 制作，PCGamingWiki 社区页由
  **SirYodaJedi** 于 2023-03-08 提交（2023-03-10 更新，968.9 kB，
  6,144 次浏览）。它还原了主机版有、PC 版缺失的角色 vocal grunt；
  主体音效取自 `Lego Indy 1` 的未压缩 WAV，`Donovan` 与 `Spalko`
  两个目录则由 Wii 版 `Lego Indy 2` 的压缩 DSP 转码而来

本项目的语音修复沿用同一批文件（46 个，8 个角色目录），安装方式为直接
覆盖 —— 无需解包 DAT，这也是 PCGamingWiki 主页面特别强调的一点。
[GOG.com 版](https://www.pcgamingwiki.com/wiki/Lego_Indiana_Jones_2:_The_Adventure_Continues)
自 2025-02-27 起已内置还原语音，购买 GOG 版可省去这一步。

### 格式研究

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

### 权利声明

原作的剧情、美术、字体与配音由 Traveller's Tales /
Warner Bros. Interactive Entertainment 及各配音演员的权利方所有。

本仓库**入库的文件**分两类，性质完全不同：

| 类别 | 文件 | 授权 |
|---|---|---|
| 源代码与文档 | `src/` `tools/` `translations/translations*.py` `translations/text.csv` `patch/` `docs/` | [MIT](LICENSE) |
| 从正版游戏 DAT 中提取的素材 | `assets/fonts/`（见下节） | **不授权**，仅供持有正版者自行重建 |

汉化需要重写游戏字体（FT2 / FNT），而这些字体文件本身是从原版 DAT 中
提取的二进制，**著作权属于权利方，MIT 许可覆盖不到它们**。放在仓库里
是为了让持有正版的玩家不必自己逆向一遍，不构成对原作品权的授权或转让。

两个 DAT（`GAME.dat` 981 MB / `GAME2.dat` 925 MB）**不入库**，原因有二：
① 它们 99.5% 是原版游戏素材，MIT 同样管不到；
② GitHub 单文件硬限制 100 MB，这两个文件都远超。见下节。

## 许可

源代码与文档以 [MIT](LICENSE) 许可。**游戏素材不在授权范围内**，
请自行购买正版。
