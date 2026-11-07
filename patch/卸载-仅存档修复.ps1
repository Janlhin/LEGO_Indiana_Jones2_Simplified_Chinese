<#
.SYNOPSIS
    LEGO Indiana Jones 2 —— 仅存档修复组件卸载。

.DESCRIPTION
    删除游戏目录里的 dinput8.dll（即「仅存档修复」组件）。
    不动 GAME.dat / GAME2.dat，也不动中文补丁的 d3d9.dll。

.EXAMPLE
    右键本文件 -> 使用 PowerShell 运行

.NOTES
    编码：UTF-8 with BOM。原因同中文补丁的脚本。
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
}

. "$PSScriptRoot\lib\Common.ps1"


# ==================================================================== 主流程

Write-Host ''
Write-Host '============================================================'
Write-Host '   LEGO Indiana Jones 2 —— 仅存档修复组件卸载'
Write-Host "   （组件版本 v$PatchVersion）"
Write-Host '============================================================'

# ---------------------------------------------------------------- 1. 定位
Write-Step '定位游戏目录'

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

# ---------------------------------------------------------------- 2. 检查运行中
Write-Step '检查游戏是否在运行'

if (Test-GameRunning) {
    Write-Host ''
    Write-Err '检测到游戏正在运行，请先关闭。'
    Read-Host '关闭游戏后按回车继续，或按 Ctrl+C 取消'
    if (Test-GameRunning) {
        Write-Err '游戏仍在运行，已取消。'
        Read-Host '按回车键退出'
        exit 1
    }
}

# ---------------------------------------------------------------- 3. 移除 DLL
Write-Step '移除 dinput8.dll'

$p = Join-Path $gameDir 'dinput8.dll'
if (Test-Path -LiteralPath $p) {
    Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    Write-Ok '已删除 dinput8.dll（存档修复组件已移除）'
} else {
    Write-Info '游戏目录里没有 dinput8.dll，无需卸载'
}

# ---------------------------------------------------------------- 完成
Write-Host ''
Write-Host '============================================================'
Write-Host '   完成。游戏目录已恢复原样（未改动任何其它文件）。'
Write-Host '============================================================'
Write-Host ''

Read-Host '按回车键退出'
