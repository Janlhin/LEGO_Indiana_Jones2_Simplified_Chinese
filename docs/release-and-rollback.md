# 发布、安装、回滚与版本兼容说明

> 本仓是 **《乐高印第安纳琼斯 2：冒险再续》** 简体中文本地化工程，不是可直接运行的游戏程序。
> 成品补丁通过 GitHub Release 附件分发；本仓入库的是源码、译文表、工具链与分发包骨架。

## 1. 发布物清单

发布物在 GitHub Release，不在仓库内（两个游戏 DAT 体积与著作权原因不入库，见 README「为什么 DAT 不入库」）：

| 发布物 | 内容 |
|---|---|
| `LEGO_Indiana_Jones2_Simplified_Chinese_v<版本>_part1.zip` | 脚本、`lib/`、说明文档、`data/GAME.dat`、`data/d3d9.dll`、`data/Audio/_VO/` |
| `LEGO_Indiana_Jones2_Simplified_Chinese_v<版本>_part2.zip` | `data/GAME2.dat` |
| `LEGO_Indiana_Jones2_SaveFix_v<版本>.zip` | 独立存档修复包：`dinput8.dll` + 安装/卸载脚本 + `lib/Common.ps1` + 说明 |

> 完整汉化包的两个分卷必须解到**同一个目录**后再安装。当前登记版本以 `patch/payload/lib/Common.ps1` 的 `$script:PatchVersion` 为准；本文件不另行记录版本号，避免两处漂移。

## 2. 安装

### 2.1 完整汉化包

解压两个分卷到同一目录，右键 `安装.ps1` →「使用 PowerShell 运行」。全程约 2–4 分钟，无需管理员权限，无需改动系统区域。图文步骤见 [`patch/安装说明.md`](../patch/安装说明.md)，纯文本版见 `patch/安装说明.txt`。

### 2.2 仅存档修复（可选独立包）

只想要存档修复、不要汉化时，单独下载 SaveFix 包，右键 `安装-仅存档修复.ps1` 运行；它只放置 `dinput8.dll`，不汉化、不改游戏内容，与中文补丁的 `d3d9.dll` 互不冲突。

## 3. 卸载与回滚

- 完整汉化包：运行 `卸载.ps1`，脚本依据备份还原原版文件。
- 存档修复包：运行 `卸载-仅存档修复.ps1`。
- 安装脚本会在游戏目录自动备份原版文件；`backup_chs` 内的原版备份带校验，防止把汉化版误当原版沿用。
- 若安装后出现异常，先卸载还原，再核对下载的分卷是否完整、是否解到同一目录。

## 4. 版本兼容

- 目标游戏：LEGO Indiana Jones 2: The Adventure Continues（2009，Traveller's Tales）。
- 运行环境：Windows；安装脚本需 Windows PowerShell 5.1 或 PowerShell 7+。
- 补丁不改游戏 exe 文件（设置菜单走运行时指针重定向），不写注册表。
- 游戏后续版本/区域版本的兼容性以实机核对为准；未核对的版本不写「兼容」结论。
- 代理 DLL 跨 Windows 版本自适应定位系统 d3d9，不再附带系统 DLL 副本（见 README 技术点）。

## 5. 校验与打包

- 分发包由 `tools/build_dist.py` 从 `patch/` staging 布局打包，需指向本机正版游戏目录：

  ```powershell
  python tools/build_dist.py --game "<游戏目录>"
  ```

- 打包后用 `tools/verify_dist.py` 校验分卷齐备、命名与版本一致、未超 GitHub 2 GB 单附件上限、合并后内容完整、脚本编码与换行合规、包内无残留 `.bat`：

  ```powershell
  python tools/verify_dist.py
  ```

- 仓库内不另建 `SHA256SUMS`：发布物是 Release 附件，哈希随 Release 附件在发版时生成；仓库原料（源码、译文表、工具）不按发布物登记校验和。
