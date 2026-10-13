<#
.SYNOPSIS
    LEGO Indiana Jones 2 简体中文补丁 —— 卸载还原。

.DESCRIPTION
    从 backup_chs 恢复原版 DAT，删除补丁放入的文件。

.EXAMPLE
    右键本文件 -> 使用 PowerShell 运行

.NOTES
    编码：UTF-8 with BOM。原因同安装脚本。
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
Write-Host '   LEGO Indiana Jones 2 汉化补丁 —— 卸载还原'
Write-Host "   （补丁版本 v$PatchVersion）"
Write-Host '============================================================'

# ---------------------------------------------------------------- 1. 定位
Write-Step '1/4 定位游戏目录'

$gameDir = Find-LegoGameDir

if (-not $gameDir) {
    Write-Host ''
    Write-Warn '没能自动定位到游戏目录。'
    $gameDir = Read-GameDirManual
}

# Read-GameDirManual 重试耗尽时会返回 $null。必须在这里挡住——
# 少了这个判断，下面的 Join-Path 会用空路径抛异常，
# 用户看到的是一串无意义的技术报错，而不是"没找到游戏目录"。
if (-not $gameDir) {
    Write-Host ''
    Write-Err '不知道游戏目录，未做任何改动。'
    Write-Host ''
    Read-Host '按回车键退出'
    exit 1
}

Write-Host ''
Write-Ok "游戏目录: $gameDir"

# ---------------------------------------------------------------- 2. 检查运行中
Write-Step '2/4 检查游戏是否在运行'

if (Test-GameRunning) {
    Write-Host ''
    Write-Err '检测到游戏正在运行，请先关闭。'
    Write-Host ''
    Read-Host '关闭游戏后按回车继续，或按 Ctrl+C 取消'
    if (Test-GameRunning) {
        Write-Err '游戏仍在运行，已取消。'
        Read-Host '按回车键退出'
        exit 1
    }
}

# ---------------------------------------------------------------- 3. 还原 DAT
Write-Step '3/4 还原原版 DAT'

$backupDir = Join-Path $gameDir 'backup_chs'
$restored = 0
$missing  = @()

foreach ($name in @('GAME.dat', 'GAME2.dat')) {
    $src = Join-Path $backupDir $name
    $dst = Join-Path $gameDir $name

    if (Test-Path -LiteralPath $src) {
        Write-Info "还原 $name （约 1 GB，请稍候）..."
        try {
            Copy-Item -LiteralPath $src -Destination $dst -Force
            Write-Ok "$name 已还原"
            $restored++
        } catch {
            Write-Err "$name 还原失败: $($_.Exception.Message)"
        }
    } else {
        $missing += $name
    }
}

if ($missing.Count -gt 0) {
    Write-Host ''
    Write-Warn "没有备份可供还原: $($missing -join ', ')"
    Write-Host '请在 Steam 中 [属性 -> 本地文件 -> 验证游戏文件完整性] 来还原。'
}

if ($restored -eq 0) {
    Write-Host ''
    Write-Host '没有可还原的内容。若要彻底清除，请在 Steam 中验证游戏文件完整性。'
}

# ---------------------------------------------------------------- 4. 清理补丁文件
Write-Step '4/4 移除补丁文件'

foreach ($f in @('d3d9.dll', 'd3d9_orig.dll')) {
    $p = Join-Path $gameDir $f
    if (Test-Path -LiteralPath $p) {
        Remove-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
        Write-Ok "已删除 $f"
    }
}

# 角色语音：只删补丁新增的文件，保留游戏自带目录
$patchVoices = Join-Path $PSScriptRoot 'data\Audio\_VO'
if (Test-Path -LiteralPath $patchVoices) {
    $gameVoices = Join-Path $gameDir 'Audio\_VO'
    $count = 0
    Get-ChildItem -LiteralPath $patchVoices -File | ForEach-Object {
        $target = Join-Path $gameVoices $_.Name
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
            $count++
        }
    }
    if ($count -gt 0) {
        Write-Ok "已移除 $count 个角色语音文件"
    }
}

# ---------------------------------------------------------------- 完成
Write-Host ''
Write-Host '============================================================'
Write-Host '   已还原为原版英文。'
Write-Host ''
Write-Host '   备份文件夹 backup_chs 保留，确认无误后可自行删除。'
Write-Host '   若仍有残留，请在 Steam 中验证游戏文件完整性。'
Write-Host '============================================================'
Write-Host ''

Read-Host '按回车键退出'