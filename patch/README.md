# 🎮 LEGO Indiana Jones 2 简体中文汉化补丁

**版本 2.0.0**　·　遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)　·　2026-10-14

《乐高印第安纳琼斯 2：冒险再续》（LEGO Indiana Jones 2: The Adventure Continues）Steam 版完整汉化补丁。

针对 2009 年 Traveller's Tales 开发的这款老游戏，逆向其 NXG 引擎资源格式，从零实现了**全文本汉化 + 中文字体 + 存档修复 + 角色语音修复**，一键安装，无需改动系统区域。

---

## 📦 下载

完整补丁包分两个分卷发布在 GitHub Releases（单个分卷接近 1 GB，故拆开）：

| 分卷 | 内容 |
| --- | --- |
| `LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0_part1.zip` | 脚本、`lib/`、说明文档、`data\GAME.dat`、`data\d3d9.dll`、`data\Audio\_VO\` |
| `LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0_part2.zip` | `data\GAME2.dat` |

> 📌 **两个包必须解到同一个目录**，否则安装脚本的自检会直接报错。

📍 发布页：<https://github.com/Janlhin/LEGO_Indiana_Jones2_Simplified_Chinese/releases/tag/2.0.0>

---

## ✨ 特性

- 🈶 **完整中文文本**：1927+ 行游戏文本全部汉化，覆盖主菜单、章节、角色、关卡、载具、作弊码、教程、网络联机、以及关卡编辑器（Builder）全套界面
- 🔠 **中文字体**：微软雅黑渲染，包含 1400+ 字符（1200+ 汉字）
- ⚙️ **设置菜单汉化**：Video Settings / Screen Resolution / Vertical Sync / Shadows / Bloom 等 40 个界面标签全部中文化（80 处显示点）。这批标签硬编码在 exe 里、不在 DAT 中，靠 `d3d9.dll` 在运行时改指针完成 —— 不改游戏文件，故不触发 Steam 校验；按键名（Left / Space 等）按设计保持英文
- 💾 **存档修复**：内置 d3d9 代理 DLL，修复了中文系统下存档跳出 / 无法保存的问题（无需再把系统区域改成土耳其语）
- 🔊 **角色语音修复**：补齐 PC 版缺失的 46 个角色语音文件（跳跃 / 受伤 / 攻击 / 死亡音效）
- 🖥️ **1080p 默认分辨率**：自动写入 `pcconfig.txt`
- ⚡ **一键安装 / 卸载**：右键运行 PowerShell 脚本即可，自动备份原版文件
- 🖱️ **不挑盘符**：游戏目录四级自动定位，装在任意自定义 Steam 库路径都能找到

---

## 📋 版本与变更

本补丁遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)：不兼容修改升主版本，向下兼容的新功能升次版本，向下兼容的问题修正升修订号。**版本号的唯一来源是 `lib/Common.ps1` 里的 `$PatchVersion`**，README 与安装说明均引用该值。

### 🚀 2.0.0 —— 当前版本

**⚠️ 不兼容改动（故升主版本）：**

- 🛑 **不再分发 `d3d9_orig.dll`。** 旧版代理靠把导出转发到这份系统 DLL 副本才能启动，而副本版本被硬钉在打包者的电脑上（实测 `v0.0.26101.9587` = Win11 24H2）。别人的机器上只要系统 d3d9 版本不同就直接加载失败，且症状与「文件不存在」完全一样。现在代理在运行时用 `GetSystemDirectoryW` + `IsWow64Process` 自行定位系统 d3d9 并转发，跨 Windows 版本自适应，游戏目录只需一个 `d3d9.dll`
- 📜 **删除全部 `.bat`，改为纯 PowerShell**（需 Windows PowerShell 5.1 或 PowerShell 7+）
- 🧹 **移除注册表写入**，无需手工清理

**🆕 新增功能：**

- ⚙️ **设置菜单汉化** —— 40 个界面标签 / 80 处显示点全部中文化。这批标签硬编码在 exe 中、不在 DAT 中，靠代理 DLL 在运行时改指针完成，不改游戏文件，故不触发 Steam 校验；按键名（Left / Space 等）按设计保持英文

**🐛 问题修正：**

- 修复菜单显示为一排问号（根因是编码搞反：UI 吃 UTF-8 而非系统 ANSI）
- 修复游戏目录定位从未生效：旧 `.bat` 里的 `libraryfolders.vdf` 正则要求路径被圆括号包起，真实 vdf 里是裸字符串，正则永远匹配 0 次，实际全靠硬编码盘符兜底
- 安装脚本改为比对指纹后跳过，已装好的文件不会被重复复制 2 GB
- `backup_chs` 里的原版备份增加校验，防止把汉化版误当原版沿用（否则卸载还原不出英文）

### 📦 1.0.0

首个对外分发版本。

> 完整的提交级变更记录见项目仓库的 `git log`。

---

## 🚀 安装

> ⚠️ **从 v1.0 升级**：v2.0.0 与 v1.0 不兼容，请先看 [`安装说明.md`](安装说明.md) 的「从 v1.0 升级」一节，不要直接解压覆盖。

1. 确保已通过 Steam 安装游戏（Steam 正版），并至少启动过一次
2. **完整解压**两个分卷到同一个目录（如桌面）—— 不能在压缩包里直接运行脚本
3. 右键 **安装.ps1** → 「使用 PowerShell 运行」
4. 从 Steam 启动游戏，即可看到中文

> 🔒 若弹出「已阻止运行脚本」，右键 `安装.ps1` → 属性 → 勾选最下方的「解除锁定」→ 确定，再重新运行。

安装脚本会自动：检测游戏目录 → 备份原版文件 → 写入汉化数据 → 安装存档修复与语音修复 → 写入 1080p 分辨率。

游戏目录检测按四级依次尝试，**不猜盘符**：

1. 📋 **注册表**读 Steam 主目录（`HKCU` / `HKLM\WOW6432Node` / `HKLM` 三处候选）
2. 📄 **解析 `libraryfolders.vdf`** 列出全部 Steam 库，逐个用本作 appid（32450）确认
3. 💽 **动态枚举本机所有就绪盘符**，逐个下钻搜索 `steamapps\common\Lego Indiana Jones 2`（最多 4 层）
4. ✍️ 以上都失败才转入手动输入游戏目录（最多重试 3 次，不会卡死）

因此不挑盘符、不挑库名：装在 `D:\Games\SteamLib\steamapps` 这类任意自定义路径也能自动找到。

脚本可反复运行：已装好的文件会比对指纹后跳过，不会重复复制 2 GB；`backup_chs` 里的原版备份也不会被二次运行覆盖。

安装时会在**游戏目录**下建 `backup_chs` 文件夹备份原版 `GAME.dat` / `GAME2.dat`（约 2 GB），供 `卸载.ps1` 还原。备份**只在文件不存在时创建**——若已有备份，脚本还会校验它是否与汉化补丁完全相同，防止把汉化版误当原版（否则卸载还原不出英文）。

> ⚠️ 若你用 Steam 验证过游戏文件完整性，或重下载过游戏，汉化会被还原成英文版。此时重新运行一次 `安装.ps1` 即可恢复。

> ⚠️ 若 Steam 提示「文件已损坏 / 需要验证」，请**不要验证**——验证会把汉化文件还原为原版，此时重新运行 `安装.ps1` 即可。

---

## 🔧 卸载

右键 **卸载.ps1** → 「使用 PowerShell 运行」，或使用 Steam「验证游戏文件完整性」。

---

## 📁 目录结构

```
LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0/
├── 安装.ps1         一键安装
├── 卸载.ps1         一键还原
├── lib/
│   └── Common.ps1   公共函数库（定位游戏目录 / 复制校验 / 备份）
├── README.md        本说明
├── 安装说明.md      面向使用者的详细图文说明
├── 安装说明.txt     同一份说明的纯文本版
└── data/
    ├── GAME.dat      中文字体（GUI 字体）
    ├── GAME2.dat     中文文本库
    ├── d3d9.dll      存档修复（无需其他 DLL 配合）
    └── Audio/_VO/    角色语音修复（46 个文件）
```

> 💡 `GAME0.dat` / `GAME1.dat` 是游戏自带的纯资源归档，**不含任何文本或字体**，因此无需汉化、无需随包分发。

---

## 🔬 技术说明

本补丁基于对 TT Games 专有格式的完整逆向：

- 📦 **DAT 归档**（MkDat v4.0）：解析信息块 / 文件表 / 名字树 / CRC 结构，通过「名字树叶子 `next` 字段即文件索引」绕开未公开的哈希算法，实现不改名不加文件的原地内容替换
- 🔠 **FT2 / NFNT 字体**（TNFN 魔数）：大端结构（头部 + posTable + charsTable + kerning + 内嵌 DXT5 DDS），charsTable 使用 Unicode 码点索引，原生支持 CJK
- 🖌️ **字体构建**：ctypes 调 GDI32 栅格化 + 纯标准库 DXT5 编解码，字形 advance 对齐原版语义
- 💾 **存档修复**：d3d9.dll 代理 + IAT hook，拦截 ANSI 文件 API，按 CP1254 转换路径绕开内核 GBK 编码错误（根因：游戏硬编码了 `LEGO® Indiana Jones™ 2` 的 CP1252/1254 字节，中文代码页下 `®` / `™` 被误译成非法文件名字符）
- 🧩 **代理 DLL 自实现导出**：游戏用 `LoadLibraryA("d3d9.dll")` + `GetProcAddress("Direct3DCreate9")` 运行时动态加载 d3d9，代理必须自己提供导出。DLL 在运行时按 `IsWow64Process` 判断位数，只加载 32 位那份系统 d3d9（64 位系统的 32 位副本在 `SysWOW64`），再转发过去。因此补丁目录里只需一个 `d3d9.dll`，跨 Windows 版本自适应，不需要附带任何系统文件副本
- ⚙️ **设置菜单标签汉化（改指针而非改字符串）**：设置菜单的英文（Video Settings 等）不在 DAT 里，硬编码在 exe 的 `.rdata`，且每条串后面紧跟下一条、**零余量**，原地替换中文放不下；改 exe 文件又会触发 Steam DRM（`.bind` 节可执行 + STEAM 标记）。最终方案是发现 exe `.data` 节里有一张**多语言 UI 字符串指针表**（`0xAB09F0`–`0xAB17DC`，每项 **8 字节** `{char* text; uint32 id;}`，`char*` 指向 `.rdata` 里的实际字符串），四类内容挤在同一张表里：cvar 名（`pcconfig.txt` 的键名，**绝对不能动**）／英文 UI 两份／法语／匈牙利语。补丁只把英文那 **80 处指针（两份各 40 项）**改指向自备的 UTF-8 字符串缓冲区——指针本身 4 字节大小不变，因此不受零余量限制，不碰文件、不触发 DRM，也不影响 cvar 与其他语言
  - 🔤 **编码是 UTF-8，不是系统 ANSI**（此处曾走错弯路）：先因「这是 ANSI 程序、存档路径在中文系统下出错」，推断 UI 也走系统 ANSI，注入 GBK —— 结果菜单显示为**一排问号**。而问号正是**严格 UTF-8 解码器**把每个非法字节替换成 `?` 的典型表现（若解码器是 CP1252，非法字节会变成西欧字母而非问号；若是 CP936/GBK，本该正常显示）。据此回头查证：exe 自带的多语言串里俄语 «Вернуть» «Качество» «Использовать» «Улучшенная» 全部是合法 UTF-8，按 CP1252 / CP1254 / GBK 解均为乱码；DAT 内的中文文本同样解出通顺的「正在保存游戏」。故 UI 文本管线吃 UTF-8。DLL 内的中文常量全部预编码为 UTF-8，并逐字节写成 `\xNN` 转义，使字节不受源文件编码与编辑器影响；`check_exports.py` 会抽样确认 7 个标签以 UTF-8 存在且无 GBK 残留
  - 🌍 **不再按系统代码页设限**：先前版本会检查 `GetACP()==936` 才注入，那是基于「UI 走系统 ANSI」的错误推断，连带会把英文 Windows 的用户排除在外。既然编码是 UTF-8，就与系统代码页无关，该判断已移除
  - 🛡️ **三重自保**：每条补丁先读回指针、确认仍等于期望的英文串 VA，再逐字节 `strcmp` 比对内容，任一不符即跳过该条。Steam 更新或版本漂移时补丁自然退化为无操作，不会写坏内存
  - 📐 **RVA 换算曾踩坑**：指针表所在的 `.data` 段实测 `VA == RawAddr`（与 `.idata` / `.rsrc` / `.bind` 不同，那些段两者不等），故文件偏移**本身就是** RVA。早期版本误按「文件偏移 − ImageBase」换算，整体偏移 0x400000，会写到完全无关的地址上。现由 `tools/verify_rva_maps.py` 实读节表核对，`tools/sim_ui_patch.py` 在不启动游戏的前提下离线仿真补丁（校验 80 条命中、两段各 40 项且无越界、cvar / 法语 / 匈牙利语段零改动、版本漂移与英文系统保护、按键名零汉化）
  - 🔍 **表边界曾划小，导致漏译**：初版把表尾定在 `0xAB0F44`，只覆盖 27 个标签；用户实测 FSAA / Bloom / Shadows 三项仍是英文。用 `tools/rescan_ui_table.py` 以 0x100 字节桶统计指针命中分布后重扫，发现表实际延伸到 `0xAB17DC`（`0xAB2C08` 之后已是 `viewProj` / `SEMANTIC_*` 等着色器语义名，属另一张表）。同时确认项并非 4 字节纯指针，而是 8 字节 `{ptr, id}` 结构——按 4 字节步进会读到 id 字段当指针。重建后覆盖 **80 处指针 / 40 个标签**
  - 🔡 **字形覆盖与编码是两回事**：编码错表现为**整串**问号或乱码，字体缺字表现为**个别字**变方框。用户见到「？质质量」，实为「**材**质质量」的「材」缺字形，而编码已正确。`tools/fix_font_coverage.py` 单独扫描主字体 `gui/Font/FONT_NXG.FT2`（1461 字形）对全部汉化文案的覆盖；`tools/check_candidate_zh.py` 可批量筛选全字形可用的候选译名。据此定稿三处：Texture Quality 用「**纹理质量**」（比「材质质量」也更准确），Edge AA 用「**边角抗锯齿**」（缺「缘」，「边角」等价），FSAA 译作「**全屏抗锯齿**」（原保留英文缩写，其实全字形可用，中文反而更易读），Show Game Controls 用「**显示游戏按键**」（缺「说」「明」）。字体共缺 441 字（含日文假名与繁体），补字需重排 DDS 偏移并改写 4 处头部字段写回 4.2 MB 的 DAT，故暂以等价译名规避
- 🐚 **安装脚本用 PowerShell 而非 BAT**：旧版 `.bat` 里有两处硬伤。其一，`.bat` 必须是 CRLF + ANSI/GBK，任何一处变成 LF 或 UTF-8，cmd.exe 就会在多字节字符上丢字节，表现为中文乱码甚至语法错乱。其二，也是更严重的一处：自动定位那段读 `libraryfolders.vdf` 的正则写成 `"path"\s*"\(([^"]+)"\)`，要求 path 值被圆括号包起，但真实 vdf 里是裸字符串 `"path"    "D:\\SteamLibrary"` —— 正则永远匹配 0 次，**自动定位从未生效过**，实际全靠后面 12 条硬编码盘符兜底，装在 C～G 之外的用户必然失败。改用 PowerShell 后定位不再依赖任何硬编码：注册表动态读 Steam 主目录、vdf 正则修正并还原 `\\` 转义、用本作 appid 精确确认每个库、全盘枚举所有就绪盘符下钻搜索，最后才是手工输入。同时每一步复制结果都校验大小，失败会明确报错而不是照样打印「安装完成」

---

## ⚠️ 已知限制

- 🔤 **键位名称保持英文**（Left / Num. 3 / Space 等）：按键名是引擎硬编码的另一套字符串，**不在**设置菜单所用的那张指针表里，两者结构上就是分开的。设置菜单标签已汉化（见下），按键名保持原样
- 🖥️ **设置菜单汉化要求系统装有中文字形**：补丁注入的是 UTF-8，编码层面与系统区域无关（英文 Windows 同样生效）。但菜单文字最终由游戏自带的字体渲染，若系统缺少中文字形则可能显示为方框或空白

---

## 🙏 致谢

本项目的完成离不开以下开源项目、文档与社区资源的帮助：

- 🎮 **[Traveller's Tales / TT Games / LucasArts]** — 原游戏《LEGO Indiana Jones 2: The Adventure Continues》
- 📚 **[xmusjackson/libttdat](https://github.com/xmusjackson/libttdat)** — TT Games DAT 归档格式的权威逆向与开源实现
- 📖 **[AlubJ/lego-tt-nxg-formats](https://github.com/AlubJ/lego-tt-nxg-formats)** — NXG 引擎 NFNT/FT2 字体格式文档
- 🔎 **[Xentax Wiki](https://wiki.xentax.com/)** — TT Games 资源格式参考
- 🇧🇷 **[Central de Traduções](https://www.centraldetraducoes.net.br/)（Joapeer 的巴西葡语翻译包）** — 提供了 PC 版 NXG 引擎字体（.FT2）路径与 TtTools 思路这一决定性线索
- 🇷🇺 **[Русификатор текста 1С (доработанный)](https://steamcommunity.com/sharedfiles/filedetails/?id=2385200498)（作者 Rusik，Steam 创意工坊，2021）** — 俄语本地化补丁。其作者修掉的「部分字母与单词显示成问号」问题，与本汉化在菜单标签上遇到的问题**同源**：游戏 UI 文本管线吃 UTF-8 而非系统 ANSI，注入 GBK 会让整串变成问号。其「安装器自动定位游戏路径」的做法也是本安装脚本的参考
- 🗂️ **[PCGamingWiki — Lego Indiana Jones 2](https://www.pcgamingwiki.com/wiki/Lego_Indiana_Jones_2:_The_Adventure_Continues)** — 语言切换机制（`language_setup.ini` + 注册表 `LanguageVal`）、存档路径、高帧率崩溃、刷新率修正等技术档案
- 🔊 **[Character Voice Restoration mod for Lego Indy 2](https://community.pcgamingwiki.com/files/file/2595-character-voice-restoration-mod-for-lego-indy-2/)（原始 mod 作者 Bario The Weird，PCGamingWiki 社区页由 SirYodaJedi 于 2023-03-08 提交）** — **本补丁 46 个角色语音文件（8 个角色目录，跳跃 / 受伤 / 攻击 / 死亡）的来源**。PC 版缺失了主机版才有的 `Audio_VO` 目录，此 mod 予以还原：主体音效取自 `Lego Indy 1` 的未压缩 WAV，`Donovan` 与 `Spalko` 两目录由 Wii 版的压缩 DSP 转码而来。本补丁沿用同一批文件，安装方式为直接覆盖，无需解包 DAT
  > 若你购买的是 **GOG.com 版**，官方自 2025-02-27 起已内置还原语音，可跳过这一步
- 🇨🇳 **游民星空（Gamersky）** — 最初的《乐高侏罗纪世界》汉化包参考
- 🖌️ **微软雅黑（Microsoft YaHei）** — 中文字形来源

---

## 📄 许可证

本补丁为汉化用途的非商业项目。游戏本体版权归 Traveller's Tales / LucasArts / Disney 所有。请支持正版。

本仓库中的脚本与工具代码，除另有说明外，可自由使用与分发；但请保留本致谢。
