# -*- coding: utf-8 -*-
"""实跑 PowerShell dot-source Common.ps1，确认 $PatchVersion 真的能取到值。"""
import os
import subprocess
import sys

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                 "dist", "LEGO_Indiana_Jones_2_CHS_v2.0.0")

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
) % D

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

ok = "VER=[2.0.0]" in out
print("\n结果:", "版本号可正确取用" if ok else "未能取到预期版本号")
sys.exit(0 if ok else 1)
