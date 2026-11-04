# 工具清单

53 个 Python 工具，**全部只用标准库 + ctypes**，无第三方依赖。
（例外：`build_font.py` 通过 ctypes 调 GDI32 栅格化，仍属标准库范畴。）

大部分工具需要读取游戏文件，因此**只能在自备正版游戏的环境下运行**。
仓库不含任何游戏素材。

---

## 环境变量

迁移到独立仓库后不再硬编码工作目录布局，统一用环境变量：

| 变量 | 默认 | 用途 |
|---|---|---|
| `GAME_ROOT` | `./game_files` | 含 `GAME2/` 子目录的目录 |
| `GAME_TEXT_DIR` | `$GAME_ROOT/GAME2/stuff/text` | 文本与字体资源 |
| `BUILD_DIR` | `./build` | 中间构建产物 |
| `TXT_OUT` | `$BUILD_DIR/stuff/text/text.csv` | 生成的 CSV |

安装/卸载脚本（`patch/` 下）**不依赖任何环境变量** —— 它们自动定位
Steam 库。

---

## 核心构建链

按执行顺序：

| 工具 | 作用 |
|---|---|
| `build_text.py` | 生成带 CHINESE 列的 `text.csv`，并报告实际用到的字符集（驱动字体构建） |
| `build_font.py` | 用 GDI32 栅格化中文字形，打包成 NFNT 字体（含内嵌 DXT5 DDS 图集） |
| `build_ft2.py` | FT2 字体打包 |
| `rebuild_dat.py` | 写回 MkDat 归档（改内容不改名不加文件） |
| `gen_ui_patch.py` | 解析 exe 的多语言指针表，生成 `ui_patch.h` |
| `check_exports.py` | 校验代理 DLL 的 16 个导出全为真实代码，无 forwarder 残留 |
| `deploy_dll.py` / `deploy.py` | 部署到游戏目录 |
| `build_dist.py` | **打包分发件**：把 `patch/` 的 staging 布局还原成发行目录结构，装入本机游戏目录里的 DAT，输出两个分卷 zip（GitHub Release 单附件 2 GB 上限） |

### 格式解析库

| 工具 | 说明 |
|---|---|
| `ttdat.py` | MkDat v4.0 归档。通过「名字树叶子 `next` 字段即文件索引」绕开未公开的哈希算法 |
| `ttfnt.py` / `ft2.py` | NFNT / FT2 字体，大端结构，`chars` 为 `list[tuple]`，`tuple[0]` 是 Unicode 码点 |
| `pe.py` | PE 头与节表 |
| `bc3.py` | 纯标准库 DXT3/DXT5 编解码 |
| `gdi_font.py` | ctypes 调 GDI32 栅格化 |

---

## 校验工具（提交前必跑）

| 工具 | 检查什么 |
|---|---|
| `sim_ui_patch.py` | **离线仿真 UI 补丁**，不启动游戏：80 条须全部命中、两段各 40 项无越界、cvar 段零命中、版本漂移有保护、按键名零汉化 |
| `check_exports.py` | 导出表必须是真实代码而非 forwarder 字符串；只读段须有 UTF-8 中文、无 GBK 残留 |
| `check_deps.py` | 导入表依赖：只能是 KERNEL32 / msvcrt / USER32，外发依赖须为空 |
| `verify_rva_maps.py` | 实读节表核对 `VA` 与 `RawAddr` 是否相等 —— RVA 换算的前提 |
| `fix_font_coverage.py` | 译文用字是否都在字体里。**编码问题与缺字问题要分开看**（见下） |
| `check_candidate_zh.py` | 批量筛选全字形可用的候选译名，避免逐个试 |
| `verify_version.py` | 版本号唯一来源、SemVer 正则、引用一致性、`.ps1` 的 UTF-8 BOM |
| `verify_fnt.py` / `verify_deploy.py` / `verify_dist.py` | 字体、部署、分发包一致性（`verify_dist.py` 直接读两个分卷 zip 的内容做端到端校验） |
| `check_dat_version.py` | 区分 DAT 是原版还是汉化版 |

> ⚠️ `check_dat_version.py` 里的 `PATCH` 路径硬编码了旧工作目录（已失效），
> 且它用的「扫全文件找 CJK」启发式在 1 GB 级二进制上误报严重 —— 原版 DAT
> 也会命中。判定 DAT 是原版还是汉化版，**应当用 `tools/ttdat.py` 解析出
> `stuff\text\text.csv` 再看 `ENGLISH` 列**（汉化版 1952 行含中文），
> 别信那个 CJK 计数。

### 编码问题 vs 缺字问题

这是本项目最容易混淆的一点，`fix_font_coverage.py` 专门用来区分：

- **编码错** → **整串**变成 `'?'` 或乱码。曾因把「存档路径走 ANSI」的结论推广到
  「UI 走渲染管线」而注入 GBK，结果菜单显示为一排问号 —— 而问号正是**严格
  UTF-8 解码器**把非法字节替换成 `?` 的典型表现（若解码器是 CP1252，非法字节
  会变成西欧字母而非问号）
- **字体缺字形** → **个别字**变方框。曾因「材质质量」的「材」缺字形而显示成
  「？质质量」，改用「纹理质量」解决

---

## 分析工具

用于逆向排查，通常一次性使用，读游戏文件：

`audit_text.py`（文本审计）、`audit_settings.py` / `audit_options.py` /
`audit_titles_values.py`（设置菜单）、`audit_gip_labels.py`（`.GIP` 菜单包）、
`dump_ui_ptr_table.py`（导出指针表）、`rescan_ui_table.py`（**按 0x100 字节桶
统计指针命中分布来划定表边界** —— 比逐条跟踪可靠）、`probe_font_room.py`
（评估字体补字的可行性）、`probe_font_room` 类工具、`save_*.py` / `game_state.py`
（存档）、`font_probe.py` / `fnt_*.py` / `atlas_grid.py`（字体图集分析）。

---

## 已移除的一次性脚本

迁移时清理了 32 个只用于排查、事后无用的脚本（`probe_exe.py`、
`brute_hash.py`、`xrefs.py`、`scan_strings.py`、`fix_dist*.py` 等）。
逆向过程中的结论已固化进代码注释与 `docs/research-notes.md`。
