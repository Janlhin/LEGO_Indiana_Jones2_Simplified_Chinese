# LEGO Indiana Jones 2 —— 仅存档修复组件

独立分发的最小修复包。**只解决一个问题：中文（以及任何非土耳其语区域）系统下，
游戏存档会跳出 / 无法保存。**

它不汉化、不修改任何游戏数据，只是把 `dinput8.dll` 放进游戏目录。

---

## 这是什么

游戏在保存时会把存档写进 `我的文档\…\LEGO® Indiana Jones™ 2` 目录。游戏硬编码了
`®` / `™` 的 **CP1252/1254** 字节，而中文系统按 **GBK** 去解释这些字节，得到一个
非法的文件名字符，导致创建目录失败、存档丢失（早期社区的临时办法是把系统区域改成
土耳其语，本组件无需这么做）。

`dinput8.dll` 劫持游戏静态导入的 `DINPUT8.DLL` 槽位（只转发它唯一的
`DirectInput8Create` 导出），在进程启动时对 10 个 ANSI 文件 API 做 IAT hook，把路径
重新按 **CP1254 → Unicode** 转码后再调 W 版 API，从而绕开内核的 GBK 转换。纯 ASCII
路径在 CP1254 下映射不变，因此对其它路径无任何副作用。

## 与中文补丁的关系

- **本组件与中文补丁（`d3d9.dll`）互不冲突**：它占用 `DINPUT8.DLL` 槽位，中文补丁
  占用 `d3d9.dll` 槽位，两者都做同样的 IAT 路径修复但各自独立加载。
- 如果你**已经装了中文补丁**，它的 `d3d9.dll` 本身已带存档修复，本组件是可选增量
  （并存时两处 patch 都指向真实 `kernel32`，互不干扰）。
- 如果你**只想要存档修复、不要汉化**，装本组件即可，无需下载整个汉化包。

## 安装

1. 关闭游戏（Steam 里完全退出 LEGO Indiana Jones 2）。
2. 右键 `安装-仅存档修复.ps1` →「使用 PowerShell 运行」。
3. 脚本会自动定位游戏目录（找不到时会让你手填），把 `dinput8.dll` 复制进去。
4. 从 Steam 启动游戏，存档恢复正常。

> 也可以不用脚本：直接把 `dinput8.dll` 复制到 `LEGOIndy2.exe` 所在的游戏目录即可。

## 卸载

运行同目录下的 `卸载-仅存档修复.ps1`，或直接删除游戏目录里的 `dinput8.dll`。

## 文件清单

| 文件 | 作用 |
| --- | --- |
| `dinput8.dll` | 存档修复组件本体（约 88 KB） |
| `安装-仅存档修复.ps1` | 一键安装 |
| `卸载-仅存档修复.ps1` | 一键卸载 |
| `lib/Common.ps1` | 脚本共用的辅助函数（定位游戏目录等） |
| `README.md` | 本说明 |

## 构建

源码在仓库 `src/savesfix/`（`savesfix.c` / `savesfix.def` / `build_msvc.bat`）：

```bash
# 有 MinGW（任选其一）
gcc -m32 -O2 -shared -o dinput8.dll savesfix.c savesfix.def -Wl,--kill-at

# 或用 VS2022 32 位工具链
src/savesfix/build_msvc.bat
```

源码逻辑与中文补丁内嵌的存档修复完全一致，仅是注入槽位不同（`DINPUT8.DLL` 而非
`d3d9.dll`），因此本组件可在不安装汉化包的前提下独立修复存档。
