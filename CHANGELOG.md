# 更新日志

本项目遵循[语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

版本号的历史定义在**分发包** `patch/payload/lib/Common.ps1` 的
`$script:PatchVersion` —— 那是给终端用户看的安装包版本。仓库自身的
版本以 git tag 为准。

## [2.0.0]

### 不兼容

- **不再分发 `d3d9_orig.dll`。** 早期代理靠把导出转发到这份系统 DLL
  副本才能启动，而副本版本被硬钉在打包者的电脑上（实测
  `v0.0.26101.9587` = Win11 24H2）。别人机器上只要系统 d3d9 版本不同
  就加载失败，且症状与「文件不存在」完全一样。现在代理在运行时用
  `GetSystemDirectoryW` + `IsWow64Process` 自行定位系统 d3d9 并转发
- **安装脚本从 `.bat` 全面改为 PowerShell**（需 Windows PowerShell 5.1
  或 PowerShell 7+），并移除全部注册表写入

### 新增

- **设置菜单汉化** —— 40 个界面标签 / 80 处显示点。这批标签硬编码在
  exe 里、不在 DAT 中，靠代理 DLL 在运行时改指针完成
- **游戏目录自动定位重写。** 旧 `.bat` 里的 `libraryfolders.vdf` 正则
  写成 `"path"\s*"\(([^"]+)"\)`，要求路径被圆括号包起，而真实 vdf 里是
  裸字符串 `"path"  "D:\\SteamLibrary"` —— 正则永远匹配 0 次，**自动定位
  从未生效过**，实际全靠后面 12 条硬编码盘符兜底，装在 C～G 之外的用户
  必然失败。现改为注册表 + vdf 解析 + 全盘枚举四级定位，不挑盘符
- **备份校验** —— 防止 `backup_chs` 里已是汉化版却被当原版沿用
- **DAT 版本判定工具** —— 区分原版与汉化版

### 修正

- 菜单显示为一排问号（根因是编码搞反：UI 吃 UTF-8 而非系统 ANSI）
- 代理加载的是 64 位 d3d9（`GetSystemDirectoryW` 在 64 位系统的 32 位
  进程里返回 System32，需换 SysWOW64）
- 删除 `.def` 里虚构的导出 `Direct3D9ShaderValidatorCreate9`（该名字不存在
  于任何 d3d9.dll）
- 安装脚本改为比对指纹后跳过，已装好的文件不会被重复复制 2 GB

## [1.0.0]

首个可用的中文本地化：主菜单、章节、角色、关卡、载具、教程、网络联机
与关卡编辑器（Builder）全套界面。

---

完整的提交级变更记录见 `git log`。
