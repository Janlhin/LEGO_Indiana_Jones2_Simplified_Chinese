<#
.SYNOPSIS
    LEGO Indiana Jones 2 简体中文补丁 —— 安装。

.DESCRIPTION
    在游戏目录里做三件事：
      1. 把汉化用DAT（GAME.dat / GAME2.dat）覆盖过去，原始DAT 先备份
      2. 放入存档修复用的 d3d9 代理 DLL（只需要这一个文件）
      3. 写入 1920x1080 默认分辨率（失败不影响，可忽略）

    与旧版的差别：
      - 不再复制系统 d3d9.dll 作为 d3d9_orig.dll。新版代理运行时
        自己定位系统 d3d9，缺了转发目标导致启动即崩的老问题不存在了。
      - 不再写注册表。语言由 GAME2.dat 内的文本库决定，写注册表无效；
        且旧版写 HKLM 那条需要管理员权限，普通用户运行会静默失败。
      - 每一步 copy 都检查结果。旧版不检查，失败也照样打印"安装完成"，
        用户只能从"游戏打不开"反过来猜是自己装漏了东西。

.EXAMPLE
    右键本文件 -> 使用 PowerShell 运行

.NOTES
    编码：UTF-8 with BOM。
    Windows PowerShell 5.1 读取无 BOM 的 .ps1 时会按系统 ANSI 代码页
    解码，脚本里的中文会变成乱码甚至导致语法错误。
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# 让中文字符在控制台正常显示。5.1 上如果控制台代码页不是 936，
# 中文会显示成乱码；这里只影响显示，不影响文件读写编码。
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # 有些环境改不动（例如重定向到文件时），忽略
}

. "$PSScriptRoot\lib\Common.ps1"


function Set-DefaultResolution {
    <#
        写 1920x1080 到 pcconfig.txt。
        这步失败不影响游戏，catch 掉只提示。
    #>
    $dirName = 'LucasArts\LEGO' + [char]0xAE + ' Indiana Jones' + [char]0x2122 + ' 2'
    $dir = Join-Path $env:APPDATA $dirName
    $cfg = Join-Path $dir 'pcconfig.txt'

    try {
        if (-not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }

        $lines = @(
            'FileVersion                 3'
            'ScreenWidth                 1920'
            'ScreenHeight                1080'
            'WindowWidth                 1920'
            'WindowHeight                1080'
            'ScreenRefreshRate           60'
            'VerticalSync                1'
        )

        if (Test-Path -LiteralPath $cfg) {
            Write-Info 'pcconfig.txt 已存在，保留你的设置不动'
        } else {
            Set-Content -LiteralPath $cfg -Value $lines -Encoding ASCII
            Write-Ok '已写入 1920x1080 默认分辨率'
        }
    } catch {
        Write-Warn "设置默认分辨率失败（不影响游戏，可稍后在游戏内 Options 调整）: $($_.Exception.Message)"
    }
}


# ==================================================================== 主流程

Write-Host ''
Write-Host '============================================================'
Write-Host '   LEGO Indiana Jones 2 汉化补丁 —— 安装'
Write-Host '============================================================'

$patchDir = $PSScriptRoot

# ---------------------------------------------------------------- 1. 自检
Write-Step "1/6 检查补丁文件（汉化补丁 v$PatchVersion）"

$required = @(
    'data\GAME.dat',
    'data\GAME2.dat',
    'data\d3d9.dll'
)
$missing = @()
foreach ($rel in $required) {
    if (Test-Path -LiteralPath (Join-Path $patchDir $rel)) {
        Write-Ok "$rel"
    } else {
        $missing += $rel
    }
}

if ($missing.Count -gt 0) {
    Write-Host ''
    Write-Err "缺少以下文件: $($missing -join ', ')"
    Write-Host '请确认补丁包已完整解压，不能在压缩包里直接运行。'
    Write-Host ''
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
    Read-Host '按回车键退出'
    exit 1
}

Write-Host ''
Write-Ok "游戏目录: $gameDir"

# ---------------------------------------------------------------- 3. 检查运行中
Write-Step '2/6 检查游戏是否在运行'

if (Test-GameRunning) {
    Write-Host ''
    Write-Err '检测到游戏正在运行。'
    Write-Host '请先关闭游戏再运行本脚本 —— 运行中复制 DAT 会被占用或写坏。'
    Write-Host ''
    Read-Host '关闭游戏后按回车继续，或按 Ctrl+C 取消'
    if (Test-GameRunning) {
        Write-Err '游戏仍在运行，已取消。'
        Read-Host '按回车键退出'
        exit 1
    }
    Write-Ok '游戏已关闭'
}

# ---------------------------------------------------------------- 4. 备份
Write-Step '3/6 备份原版文件'

Backup-Once -GameDir $gameDir -Names @('GAME.dat', 'GAME2.dat') -PatchDir $patchDir

# ---------------------------------------------------------------- 5. 写 DAT
Write-Step '4/6 安装汉化内容（约 2 GB，请勿中断）'

if (Test-FileMatch (Join-Path $patchDir 'data\GAME.dat') (Join-Path $gameDir 'GAME.dat')) {
    Write-Ok 'GAME.dat 已经是汉化版本，跳过（约 1 GB 已省下）'
} else {
    Copy-Verify -Source (Join-Path $patchDir 'data\GAME.dat') `
                -Dest (Join-Path $gameDir 'GAME.dat') `
                -Label 'GAME.dat'
}

if (Test-FileMatch (Join-Path $patchDir 'data\GAME2.dat') (Join-Path $gameDir 'GAME2.dat')) {
    Write-Ok 'GAME2.dat 已经是汉化版本，跳过（约 1 GB 已省下）'
} else {
    Copy-Verify -Source (Join-Path $patchDir 'data\GAME2.dat') `
                -Dest (Join-Path $gameDir 'GAME2.dat') `
                -Label 'GAME2.dat'
}

# ---------------------------------------------------------------- 6. 装 DLL
Write-Step '5/6 安装存档修复补丁'

Copy-Verify -Source (Join-Path $patchDir 'data\d3d9.dll') `
            -Dest (Join-Path $gameDir 'd3d9.dll') `
            -Label 'd3d9.dll'

# 旧版方案遗留的文件，已不再需要。清掉以免让人误以为还缺东西。
$legacy = Join-Path $gameDir 'd3d9_orig.dll'
if (Test-Path -LiteralPath $legacy) {
    Remove-Item -LiteralPath $legacy -Force -ErrorAction SilentlyContinue
    Write-Ok '已清理旧版遗留的 d3d9_orig.dll（新版不需要它）'
}

# 角色语音修复是可选的，失败不阻断
$voiceSrc = Join-Path $patchDir 'data\Audio\_VO'
if (Test-Path -LiteralPath $voiceSrc) {
    $voiceDst = Join-Path $gameDir 'Audio\_VO'
    try {
        Copy-Item -LiteralPath $voiceSrc -Destination $voiceDst -Recurse -Force
        Write-Ok '角色语音修复已写入'
    } catch {
        Write-Warn "角色语音修复写入失败（不影响游戏）: $($_.Exception.Message)"
    }
}

# ---------------------------------------------------------------- 7. 分辨率
Write-Step '6/6 设置默认分辨率'

Set-DefaultResolution

# ---------------------------------------------------------------- 完成
Write-Host ''
Write-Host '============================================================'
Write-Host "   安装完成（汉化补丁 v$PatchVersion）"
Write-Host ''
Write-Host '   现在从 Steam 启动游戏即可看到中文。'
Write-Host ''
Write-Host '   说明:'
Write-Host '   - 系统区域无需改成土耳其语，补丁已内置存档修复'
Write-Host '   - 游戏目录里只有 d3d9.dll 一个补丁文件即可'
Write-Host '   - 如需卸载还原，运行同目录下的 卸载.ps1'
Write-Host '   - 原版备份在游戏目录 backup_chs 文件夹内（约 2 GB）'
Write-Host '   - 若 Steam 提示文件校验，请勿验证，否则会被还原为原版'
Write-Host '============================================================'
Write-Host ''

Read-Host '按回车键退出'