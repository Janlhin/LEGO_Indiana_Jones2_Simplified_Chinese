<#
.SYNOPSIS
    LEGO Indiana Jones 2 —— 仅存档修复（独立组件）。

.DESCRIPTION
    本脚本只做一件事：把 dinput8.dll 放进游戏目录。

    dinput8.dll 劫持游戏静态导入的 DINPUT8.DLL 槽位（只转发它唯一的
    DirectInput8Create 导出），在进程启动时对 10 个 ANSI 文件 API 做 IAT hook，
    把路径按 CP1254 → Unicode 重新转码后再调 W 版 API，从而绕开中文（及其它
    非土耳其语）系统下内核的 GBK 转换错误，修复存档跳出 / 无法保存的问题。

    它：
      - 不修改任何游戏数据（不碰 GAME.dat / GAME2.dat），不改汉化；
      - 不占用、不覆盖中文补丁的 d3d9.dll 槽位；
      - 与中文补丁并存时，两处 IAT patch 都指向真实 kernel32，互不干扰；
      - 单独使用即可修存档 —— 这正是它的全部用途。

.EXAMPLE
    右键本文件 -> 使用 PowerShell 运行

.NOTES
    编码：UTF-8 with BOM。原因同中文补丁的安装脚本。
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# 让中文字符在控制台正常显示。
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}

. "$PSScriptRoot\lib\Common.ps1"


<#
    小文件复制 + 校验。dinput8.dll 只有约 88 KB，这里用 KB 显示体积，
    不走 Common.ps1 里为 2 GB DAT 准备的「约 X GB」提示。
#>
function Copy-Dll {
    param(
        [string]$Source,
        [string]$Dest,
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        throw "$Label 源文件不存在: $Source`n请确认压缩包已完整解压。"
    }

    $size = (Get-Item -LiteralPath $Source).Length
    Write-Info "写入 $Label （$([math]::Round($size / 1KB, 1)) KB）..."
    Copy-Item -LiteralPath $Source -Destination $Dest -Force

    if (-not (Test-Path -LiteralPath $Dest)) {
        throw "$Label 写入后目标文件不存在。`n常见原因：杀毒软件拦截、或磁盘空间不足。"
    }

    if ((Get-Item -LiteralPath $Dest).Length -ne $size) {
        throw "$Label 写入不完整：大小不一致，可能磁盘已满。"
    }

    Write-Ok "$Label 写入完成"
}


# ==================================================================== 主流程

Write-Host ''
Write-Host '============================================================'
Write-Host '   LEGO Indiana Jones 2 —— 仅存档修复'
Write-Host "   （组件版本 v$PatchVersion）"
Write-Host '============================================================'

$patchDir = $PSScriptRoot

# ---------------------------------------------------------------- 1. 自检
Write-Step '检查组件文件'

if (Test-Path -LiteralPath (Join-Path $patchDir 'dinput8.dll')) {
    Write-Ok 'dinput8.dll'
} else {
    Write-Err '缺少 dinput8.dll，请确认压缩包已完整解压，不能在压缩包里直接运行。'
    Read-Host '按回车键退出'
    exit 1
}

# ---------------------------------------------------------------- 2. 定位
$gameDir = Find-LegoGameDir

if (-not $gameDir) {
    Write-Host ''
    Write-Warn '没能自动定位到游戏目录。'
    $gameDir = Read-GameDirManual
}

if (-not $gameDir) {
    Write-Host ''
    Write-Err '不知道游戏目录，未做任何改动。'
    Read-Host '按回车键退出'
    exit 1
}

Write-Host ''
Write-Ok "游戏目录: $gameDir"

# ---------------------------------------------------------------- 3. 检查运行中
Write-Step '检查游戏是否在运行'

if (Test-GameRunning) {
    Write-Host ''
    Write-Err '检测到游戏正在运行。'
    Write-Host '请先关闭游戏再继续 —— 运行中复制文件可能被占用。'
    Read-Host '关闭游戏后按回车继续，或按 Ctrl+C 取消'
    if (Test-GameRunning) {
        Write-Err '游戏仍在运行，已取消。'
        Read-Host '按回车键退出'
        exit 1
    }
    Write-Ok '游戏已关闭'
}

# ---------------------------------------------------------------- 4. 写入 DLL
Write-Step '安装存档修复组件'

Copy-Dll -Source (Join-Path $patchDir 'dinput8.dll') `
         -Dest (Join-Path $gameDir 'dinput8.dll') `
         -Label 'dinput8.dll'

# 旧版方案遗留的文件，已不再需要。清掉以免让人误以为还缺东西。
$legacy = Join-Path $gameDir 'd3d9_orig.dll'
if (Test-Path -LiteralPath $legacy) {
    Remove-Item -LiteralPath $legacy -Force -ErrorAction SilentlyContinue
    Write-Ok '已清理旧版遗留的 d3d9_orig.dll（新版不需要它）'
}

# ---------------------------------------------------------------- 完成
Write-Host ''
Write-Host '============================================================'
Write-Host '   存档修复组件已安装。'
Write-Host ''
Write-Host '   现在从 Steam 启动游戏即可正常存档。'
Write-Host ''
Write-Host '   说明:'
Write-Host '   - 本组件只修存档，不改任何游戏内容、不汉化；'
Write-Host '   - 若已装中文补丁（d3d9.dll），两者并存互不影响；'
Write-Host '   - 卸载请运行同目录下的 卸载-仅存档修复.ps1；'
Write-Host '   - 也可直接删除游戏目录里的 dinput8.dll 来移除它。'
Write-Host '============================================================'
Write-Host ''

Read-Host '按回车键退出'
