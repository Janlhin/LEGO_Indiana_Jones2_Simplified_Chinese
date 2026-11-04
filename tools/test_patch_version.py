# -*- coding: utf-8 -*-
"""实跑 PowerShell dot-source 校验**真实发布包**里的 Common.ps1。

原先这个脚本指向 `dist/LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0` 目录，
但 v2.0.0 起分发件改成了两个分卷 zip，那个目录根本不存在 —— 脚本一直是失效状态。

现在改为：把 `dist/<包名>_part1.zip` 解到临时目录，对**玩家真正拿到的那份**
`lib/Common.ps1` 做 dot-source，确认 $PatchVersion、$script:LegoAppId 与
几个关键函数都取得到值。包本身就是脚本的运行环境，比在仓库里跑更贴近实况。

用法:
    python tools/test_patch_version.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
EXPECTED_VERSION = "2.0.0"


def find_package():
    """在 dist/ 里找 part1 分卷（名字带版本号，由 build_dist.py 产出）。"""
    if not os.path.isdir(DIST):
        return None, 'dist/ 不存在，先跑 python tools/build_dist.py --game "<游戏目录>"'
    cands = [f for f in sorted(os.listdir(DIST))
             if f.endswith("_part1.zip")
             and f.startswith("LEGO_Indiana_Jones2_Simplified_Chinese")]
    if not cands:
        return None, "dist/ 里没有 LEGO_Indiana_Jones2_Simplified_Chinese_*_part1.zip"
    return os.path.join(DIST, cands[-1]), None


def main():
    pkg, err = find_package()
    if err:
        print("[错误] %s" % err)
        return 1
    print("发布包:", os.path.basename(pkg))

    tmp = tempfile.mkdtemp(prefix="patchver-")
    try:
        with zipfile.ZipFile(pkg) as z:
            z.extractall(tmp)
        tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
        if not tops:
            print("[错误] 包里没有顶层目录")
            return 1
        root = os.path.join(tmp, tops[0])
        common = os.path.join(root, "lib", "Common.ps1")
        if not os.path.exists(common):
            print("[错误] 包内找不到 lib/Common.ps1")
            return 1
        print("包顶层:", tops[0])

        # 用单引号包住整段 -Command，避免 Bash 层把 $PatchVersion 展开掉
        ps = (
            "$ErrorActionPreference='Stop';"
            "$OutputEncoding=[Text.Encoding]::UTF8;"
            "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
            "Set-Location -LiteralPath '%s';"
            ". '.\\lib\\Common.ps1';"
            "Write-Output ('VER=[' + $PatchVersion + ']');"
            "Write-Output ('APPID=[' + $script:LegoAppId + ']');"
            "Write-Output ('FIND=' + [bool](Get-Command Find-LegoGameDir -ErrorAction SilentlyContinue));"
            "Write-Output ('COPYV=' + [bool](Get-Command Copy-Verify -ErrorAction SilentlyContinue))"
        ) % root.replace("'", "''")

        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        print("returncode:", r.returncode)
        print("stdout:")
        print(out or "(空)")
        if err:
            print("stderr:")
            print(err)

        m = re.search(r"VER=\[([^\]]*)\]", out)
        got = m.group(1) if m else None
        ok = got == EXPECTED_VERSION and "APPID=[32450]" in out and "FIND=True" in out
        print()
        print("包内 Common.ps1 版本号:", got, "（期望 %s）" % EXPECTED_VERSION)
        print("结果:", "版本号可正确取用" if ok else "未能取到预期版本号")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
