<#
.SYNOPSIS
    定位 LEGO Indiana Jones 2 的安装目录。

.DESCRIPTION
    按可靠性从高到低依次尝试，每一级失败都记录原因，最后一级才问用户。

    为什么不按盘符猜：
    旧版安装脚本里有一段读 libraryfolders.vdf 的代码，正则写成
        "path"\s*"\(([^"]+)"\)
    要求 path 值被圆括号包起来。但真实 vdf 里是：
        "path"        "D:\\SteamLibrary"
    没有圆括号，所以那段正则永远匹配 0 次 —— 自动定位从未生效过，
    实际全靠后面 12 条硬编码盘符兜底。换个盘符的用户必然失败。

    本模块改成三条可靠来源，并且用 appid 精确确认。

.EXAMPLE
    Find-LegoGameDir
#>

# 本作在 Steam 的 appid。libraryfolders.vdf 的 apps 段里列了每个库
# 装过哪些 app，只信任"apps 段含这个号"的那个库，比"路径猜对了再看
# 有没有 exe"可靠得多 —— 别人可能把游戏装在任意自定义库里。
$script:LegoAppId = '32450'

# 游戏目录名与主程序名
$script:LegoDirName = 'Lego Indiana Jones 2'
$script:LegoExeName = 'LEGOIndy2.exe'

# ---------------------------------------------------------------- 版本号
# 全补丁**唯一**的版本号来源。改版本号只改这一行，README / 安装说明 /
# 安装与卸载脚本的输出都从 here 取，避免出现「目录名是 v1.0、文档写 v1.1」
# 这种自相矛盾。
#
# 遵循语义化版本 2.0.0（https://semver.org/lang/zh-CN/）：
#   主版本号 X —— 有任何不兼容修改时 +1，次版本号与修订号归零
#   次版本号 Y —— 有向下兼容的新功能时 +1，修订号归零
#   修订号 Z —— 只做了向下兼容的问题修正时 +1
#
# 2.0.0 相对 1.0.0 的不兼容改动（故升主版本）：
#   - 不再分发 d3d9_orig.dll。代理 DLL 改为运行时用
#     GetSystemDirectoryW + IsWow64Process 自行定位系统 d3d9 并转发，
#     旧包必须靠那份被硬钉在打包者电脑上的系统 DLL 副本才能启动。
#   - 删除全部 .bat，改为纯 PowerShell（需 Windows PowerShell 5.1 或
#     PowerShell 7+）。按旧文档双击 .bat 的用户会找不到文件。
#   - 移除注册表写入。
$script:PatchVersion = '2.0.0'


function Write-Step {
    param([string]$Message)
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Gray
}

function Write-Ok {
    param([string]$Message)
    Write-Host "    [OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "    [!] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "    [X] $Message" -ForegroundColor Red
}


<#
    从 Steam 注册表拿主安装目录。
    HKCU\SOFTWARE\Valve\Steam\SteamPath 是当前用户的 Steam 位置，
    HKLM\...\WOW6432Node\Valve\Steam\InstallPath 是机器级的。
    拿到之后 libraryfolders.vdf 的位置就是确定的，不用猜
    %ProgramFiles(x86)% 还是 %ProgramFiles%。
#>
function Get-SteamRoot {
    $candidates = @(
        'HKCU:\SOFTWARE\Valve\Steam',
        'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam',
        'HKLM:\SOFTWARE\Valve\Steam'
    )

    foreach ($key in $candidates) {
        try {
            if (-not (Test-Path -LiteralPath $key)) { continue }
            $item = Get-ItemProperty -LiteralPath $key -ErrorAction Stop
            foreach ($name in @('SteamPath', 'InstallPath')) {
                $value = $item.$name
                if ($value -and (Test-Path -LiteralPath $value)) {
                    return [pscustomobject]@{
                        Path   = $value
                        Source = "注册表 $key\$name"
                    }
                }
            }
        } catch {
            Write-Verbose "读取 $key 失败: $($_.Exception.Message)"
        }
    }
    return $null
}


<#
    解析 libraryfolders.vdf，返回候选库路径列表。

    不做完整的 VDF 语法解析，只按"path 值"逐个抓：
        "path"        "D:\\SteamLibrary"
    注意值里反斜杠是转义的（\\ 表示一个 \），取出来要还原，
    否则 C:\\Program Files 会变成字面量的两个反斜杠路径。
#>
function Get-SteamLibraryPaths {
    param([string]$SteamRoot)

    $vdf = Join-Path $SteamRoot 'steamapps\libraryfolders.vdf'
    if (-not (Test-Path -LiteralPath $vdf)) {
        Write-Verbose "没有 libraryfolders.vdf: $vdf"
        return @()
    }

    try {
        $text = [System.IO.File]::ReadAllText($vdf)
    } catch {
        Write-Warn "读取 libraryfolders.vdf 失败: $($_.Exception.Message)"
        return @()
    }

    # 兼容两种 vdf 格式：
    #   老格式 "LibraryFolders" { "1" "D:\\SteamLibrary" }
    #   新格式 "libraryfolders" { "0" { "path" "..." "apps" { "32450" "..." } } }
    $paths = New-Object System.Collections.Generic.List[string]

    foreach ($m in [regex]::Matches($text, '"path"\s+"((?:[^"\\]|\\.)*)"')) {
        $raw = $m.Groups[1].Value
        # VDF 里 \\ 是转义的单反斜杠
        $p = $raw -replace '\\\\', '\'
        if ($p -and ($paths -notcontains $p)) {
            $paths.Add($p)
        }
    }

    # 老格式兜底
    if ($paths.Count -eq 0) {
        foreach ($m in [regex]::Matches($text, '"LibraryFolders"[\s\S]*?\{([\s\S]*?)\}')) {
            foreach ($p in [regex]::Matches($m.Groups[1].Value, '"([A-Za-z]:\\\\[^"]*)"')) {
                $raw = $p.Groups[1].Value -replace '\\\\', '\'
                if ($raw -and ($paths -notcontains $raw)) {
                    $paths.Add($raw)
                }
            }
        }
    }

    return $paths.ToArray()
}


<#
    某条库里是否装了本作。
    优先看 apps 段里的 appid；vdf 没有 apps 段时退回"目录里确实有 exe"。
#>
function Test-LibraryHasGame {
    param([string]$LibraryPath)

    $gameDir = Join-Path $LibraryPath "steamapps\common\$script:LegoDirName"
    if (-not (Test-Path -LiteralPath (Join-Path $gameDir $script:LegoExeName))) {
        return $false
    }

    # 若 vdf 的 apps 段里能查到 appid，那就是精确命中
    $vdf = Join-Path $LibraryPath 'steamapps\libraryfolders.vdf'
    if (Test-Path -LiteralPath $vdf) {
        try {
            $text = [System.IO.File]::ReadAllText($vdf)
            # 该库块内出现 appid 即认为命中
            if ($text -match "`"$script:LegoAppId`"\s*`"") {
                return $true
            }
        } catch {
            # 读不了就按"有 exe 就算"处理
        }
    }
    return $true
}


<#
    列出本机所有**已就绪**的固定/可移动盘符（跳过没插盘的光驱、
    未挂载的网络盘、以及不可访问的盘）。
    旧版本把 C D E F G 五个盘符写死了，装在 H 盘或用移动硬盘的用户
    就会掉到手工输入。现在改成动态枚举，不猜盘符。
#>
function Get-ReadyDriveLetters {
    $letters = New-Object System.Collections.Generic.List[string]

    # -PSProvider FileSystem 只列出 Windows 认可的文件系统驱动器
    $drives = @(Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue)
    foreach ($d in $drives) {
        $root = $d.Root
        if (-not $root) { continue }
        # 跳过网络盘：Steam 库不会真装在UNC 上，且遍历很慢容易卡死
        if ($d.DisplayRoot) { continue }   # DisplayRoot 仅网络盘有值
        $letters.Add($root)
    }

    # 保险起见再扫一遍 A-Z，涵盖 Get-PSDrive 漏掉的（某些 USB 盘 /
    # 未分配的盘符在被某些脚本枚举时才出现）
    foreach ($c in [char[]]'ABCDEFGHIJKLMNOPQRSTUVWXYZ') {
        $root = "${c}:\"
        if ($letters -notcontains $root) {
            try {
                if (Test-Path -LiteralPath $root) {
                    # 光驱会挂载成有内容的目录，但根目录不可写
                    $probe = Test-Path -LiteralPath "${root}\"
                    if ($probe) { $letters.Add($root) }
                }
            } catch {
                # 访问被拒的盘（BitLocker 未解锁等）直接跳过
            }
        }
    }

    return $letters.ToArray()
}


<#
    在给定根目录下逐层搜索游戏目录。

    为什么要全盘搜：Steam 允许把库建在任意目录，不限于
    SteamLibrary / Steam / Program Files (x86)\Steam 这几个约定名。
    用户可能装在 D:\Games\Steam Library 之类的地方。

    搜索策略是"找 steamapps\common\<游戏目录名>"这个特征路径，
    最多下钻 $MaxDepth 层（默认 4，够覆盖绝大多数自定义库）。
#>
function Search-GameDirUnder {
    param(
        [string]$Root,
        [int]$MaxDepth = 4
    )

    $results = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path -LiteralPath $Root)) { return $results.ToArray() }

    # 优先直接命中：Root 本身就是库
    $direct = Join-Path $Root "steamapps\common\$script:LegoDirName"
    if (Test-Path -LiteralPath (Join-Path $direct $script:LegoExeName)) {
        $results.Add($direct)
        return $results.ToArray()
    }

    # 否则逐层下钻。深度优先，命中即返回（找到第一个就用，
    # 同一台机器上正常只会有一个安装）。
    $level = @(Get-ChildItem -LiteralPath $Root -Directory -Force -ErrorAction SilentlyContinue)

    for ($d = 1; $d -le $MaxDepth -and $level.Count -gt 0; $d++) {
        $next = New-Object System.Collections.Generic.List[System.IO.DirectoryInfo]

        foreach ($dir in $level) {
            # 先看这个目录下有没有 steamapps
            $candidate = Join-Path $dir.FullName "steamapps\common\$script:LegoDirName"
            if (Test-Path -LiteralPath (Join-Path $candidate $script:LegoExeName)) {
                $results.Add($candidate)
                continue
            }

            # 没命中就继续往下找一层
            $children = @(Get-ChildItem -LiteralPath $dir.FullName -Directory -Force -ErrorAction SilentlyContinue)
            foreach ($c in $children) {
                # 跳过明显无意义的深挖，省时间
                $skip = @('$Recycle.Bin', 'System Volume Information', 'Windows',
                          'node_modules', '.git', 'Program Files (x86)\Common Files')
                if ($skip -notcontains $c.Name) {
                    $next.Add($c)
                }
            }
        }

        if ($results.Count -gt 0) { return $results.ToArray() }
        $level = @($next)
    }

    return $results.ToArray()
}


<#
    主定位函数。返回找到的目录，或 $null（调用方应转入手工输入）。
#>
function Find-LegoGameDir {
    Write-Step '正在定位游戏目录'

    # --- 第 1 级：注册表拿 Steam 主目录 ---
    $steam = Get-SteamRoot
    if ($steam) {
        Write-Ok "Steam 主目录: $($steam.Path)"
        Write-Info "来源: $($steam.Source)"
    } else {
        Write-Warn '注册表里没找到 Steam 安装位置'
    }

    # --- 第 2 级：枚举所有库 ---
    $libs = @()
    if ($steam) {
        # Steam 主目录本身也是一个库
        $libs += $steam.Path
        $libs += Get-SteamLibraryPaths -SteamRoot $steam.Path
    }

    $libs = @($libs | Where-Object { $_ } | Select-Object -Unique)
    if ($libs.Count -gt 0) {
        Write-Info "共 $($libs.Count) 个 Steam 库待查:"
        foreach ($lib in $libs) {
            Write-Info "  $lib"
        }
    }

    # --- 第 3 级：逐库确认 ---
    foreach ($lib in $libs) {
        if (Test-LibraryHasGame -LibraryPath $lib) {
            $dir = Join-Path $lib "steamapps\common\$script:LegoDirName"
            Write-Ok "找到游戏目录: $dir"
            return $dir
        }
    }

    # --- 第 4 级：枚举所有盘符 + 全盘下钻搜索 ---
    Write-Warn '库清单里没找到，改为搜索本机所有磁盘...'
    $drives = @(Get-ReadyDriveLetters)

    if ($drives.Count -eq 0) {
        Write-Warn '没枚举到可访问的磁盘'
    } else {
        Write-Info "已就绪盘符 $($drives.Count) 个: $($drives -join ' ')"
    }

    foreach ($drive in $drives) {
        Write-Info "搜索 $drive ..."
        $found = @(Search-GameDirUnder -Root $drive -MaxDepth 4)
        if ($found.Count -gt 0) {
            Write-Ok "找到游戏目录: $($found[0])"
            return $found[0]
        }
    }

    Write-Err '自动定位失败'
    return $null
}


<#
    让用户手工输入目录，并验证有效性。
    重试上限 3 次 —— 无上限的 while(true) 在用户不知道路径、
    或粘贴了带引号的路径时会变成死循环，只能强杀窗口。
#>
function Read-GameDirManual {
    Write-Step '请手动输入游戏目录'

    Write-Host ''
    Write-Host '    获取方法：Steam 库 -> 右键游戏 -> 管理 -> 浏览本地文件'
    Write-Host '    打开的文件夹里应当能看到 LEGOIndy2.exe'
    Write-Host ''

    $maxTries = 3
    $tried = 0

    while ($tried -lt $maxTries) {
        $tried++
        $left = $maxTries - $tried
        if ($left -gt 0) {
            Write-Host "    （还可重试 $left 次）"
        }

        $input = Read-Host '    游戏目录路径'
        if (-not $input) {
            Write-Warn '没有输入内容。'
            continue
        }

        # 去掉常见的粘贴附带引号
        $input = $input.Trim().Trim('"').Trim("'")

        if (Test-Path -LiteralPath (Join-Path $input $script:LegoExeName)) {
            Write-Ok "确认: $input"
            return $input
        }

        Write-Err "该目录下没有 $($script:LegoExeName)"
    }

    Write-Host ''
    Write-Err '多次输入均无效，已放弃。'
    Write-Host '  请先确认游戏已安装在哪个盘，再重新运行本脚本；'
    Write-Host '  或直接用 Steam 的[属性 -> 本地文件 -> 验证游戏文件完整性]。'
    Write-Host ''
    return $null
}


<#
    比较两个文件是否一致：先比大小，再比 MD5。
    用来判断"汉化版 DAT 是否已经装好了"。
    没有这步的话，重复运行安装脚本会白白重拷2 GB。
#>
function Test-FileMatch {
    param(
        [string]$A,
        [string]$B
    )

    if (-not (Test-Path -LiteralPath $A)) { return $false }
    if (-not (Test-Path -LiteralPath $B)) { return $false }

    $fa = Get-Item -LiteralPath $A
    $fb = Get-Item -LiteralPath $B
    if ($fa.Length -ne $fb.Length) { return $false }

    return ((Get-FileHash -LiteralPath $A -Algorithm MD5).Hash -eq
            (Get-FileHash -LiteralPath $B -Algorithm MD5).Hash)
}


<#
    复制并校验。取代旧版 BAT 里的裸 copy —— 旧版不检查 errorlevel，
    失败时脚本继续往下跑，最后照样打印"安装完成"，
    用户只能从"游戏打不开"反过来猜是自己装漏了东西。
#>
function Copy-Verify {
    param(
        [string]$Source,
        [string]$Dest,
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $Source)) {
        throw "$Label 源文件不存在: $Source`n请确认补丁解压完整。"
    }

    Write-Info "写入 $Label （约 $([math]::Round((Get-Item -LiteralPath $Source).Length / 1GB, 2)) GB，请稍候）..."
    Copy-Item -LiteralPath $Source -Destination $Dest -Force

    if (-not (Test-Path -LiteralPath $Dest)) {
        throw "$Label 写入后目标文件不存在。`n常见原因：杀毒软件拦截、或磁盘空间不足。"
    }

    $srcSize = (Get-Item -LiteralPath $Source).Length
    $dstSize = (Get-Item -LiteralPath $Dest).Length
    if ($srcSize -ne $dstSize) {
        throw "$Label 写入不完整：源 $srcSize 字节，目标 $dstSize 字节。`n磁盘可能已满。"
    }

    Write-Ok "$Label 写入完成"
}


<#
    备份到 backup_chs，已存在则不覆盖。
    不覆盖很重要：第二次运行时备份里必须还是原版，
    若被汉化版覆盖，卸载就还原不回去了。
#>
function Backup-Once {
    param(
        [string]$GameDir,
        [string[]]$Names,
        # 补丁包里的同名文件，用来判断"已有备份"到底是原版还是汉化版
        [string]$PatchDir
    )

    $backupDir = Join-Path $GameDir 'backup_chs'
    if (-not (Test-Path -LiteralPath $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    }

    foreach ($name in $Names) {
        $src = Join-Path $GameDir $name
        $dst = Join-Path $backupDir $name

        if (Test-Path -LiteralPath $dst) {
            # 关键校验：已有备份若与补丁包完全一致，说明它是汉化版，
            # 不是原版。这种备份还原回去等于没卸载。
            # 成因：用户先装了汉化版（或用旧版脚本装过），之后才拿到本补丁，
            # 此时 backup_chs 里躺的是汉化版，而"已存在就跳过"会一直沿用。
            if ($PatchDir) {
                $patchFile = Join-Path (Join-Path $PatchDir 'data') $name
                if ((Test-Path -LiteralPath $patchFile) -and
                    (Test-FileMatch $patchFile $dst)) {
                    Write-Warn "$name 的已有备份与汉化补丁完全相同 —— 这不是原版，卸载会还原不出英文。"
                    Write-Info  "       请删除 $dst 后重新运行本脚本，"
                    Write-Info  '       或在 Steam 中[验证游戏文件完整性]拿回原版，再运行本脚本。'
                    continue
                }
            }
            Write-Info "$name 已有备份，跳过"
            continue
        }

        if (-not (Test-Path -LiteralPath $src)) {
            Write-Warn "$name 在游戏目录里不存在，跳过备份"
            continue
        }

        Write-Info "备份 $name ..."
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
}


<#
    游戏是否正在运行。运行中复制 DAT 会被占用或写坏。
#>
function Test-GameRunning {
    return [bool](Get-Process -Name 'LEGOIndy2' -ErrorAction SilentlyContinue)
}