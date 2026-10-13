# -*- coding: utf-8 -*-
"""校验：版本号只在 Common.ps1 定义一次，各处引用一致，且 PS1 保持 UTF-8 with BOM。"""
import os
import re
import sys

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                 "dist", "LEGO_Indiana_Jones_2_CHS_v2.0.0")

ok = True


def fail(msg):
    global ok
    ok = False
    print("  [FAIL] " + msg)


def good(msg):
    print("  [ok]   " + msg)


print("=== 1. 版本号唯一来源 ===")
common = os.path.join(D, "lib", "Common.ps1")
with open(common, encoding="utf-8-sig") as fh:
    src = fh.read()
m = re.search(r"\$script:PatchVersion\s*=\s*'([0-9]+\.[0-9]+\.[0-9]+)'", src)
if not m:
    fail("Common.ps1 里找不到 $PatchVersion 定义")
    ver = None
else:
    ver = m.group(1)
    good("Common.ps1 定义 $PatchVersion = %s" % ver)

# SemVer 官方校验正则
if ver:
    pat = re.compile(r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\."
                     r"(?P<patch>0|[1-9]\d*)"
                     r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
                     r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
                     r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")
    if pat.match(ver):
        good("%s 符合 SemVer 2.0.0 官方校验正则" % ver)
    else:
        fail("%s 不符合 SemVer 校验正则" % ver)

print("\n=== 2. 脚本引用版本号而非硬编码 ===")
for name in ("安装.ps1", "卸载.ps1"):
    p = os.path.join(D, name)
    with open(p, encoding="utf-8-sig") as fh:
        s = fh.read()
    uses = "$PatchVersion" in s
    # 匹配形如 v1.0 / v2.0.0 的硬编码字面量
    hard = re.findall(r"(?<!\$)\bv?\d+\.\d+(?:\.\d+)?\b(?!\s*:)", s)
    hard = [h for h in hard if h not in ("1.0",)]
    if uses:
        good("%s 引用了 $PatchVersion" % name)
    else:
        fail("%s 未引用 $PatchVersion" % name)
    if hard:
        print("         其它数字字面量（多为步骤号/版本要求，非版本号）: %s" % sorted(set(hard))[:6])

print("\n=== 3. 文档版本号与定义一致 ===")
for name in ("README.md", "安装说明.md"):
    p = os.path.join(D, name)
    with open(p, encoding="utf-8") as fh:
        s = fh.read()
    if ver and ver in s:
        good("%s 含版本号 %s" % (name, ver))
    else:
        fail("%s 未含版本号 %s" % (name, ver))
    stale = re.findall(r"CHS_v(\d+\.\d+(?:\.\d+)?)", s)
    stale = [x for x in stale if x != ver]
    if stale:
        fail("%s 仍引用旧目录名版本: %s" % (name, stale))
    else:
        good("%s 无残留的旧目录名版本引用" % name)

print("\n=== 4. 目录名与版本号一致 ===")
dname = os.path.basename(D)
if ver and dname.endswith("_v" + ver):
    good("目录名 %s 与 $PatchVersion 一致" % dname)
else:
    fail("目录名 %s 与 $PatchVersion %s 不一致" % (dname, ver))

print("\n=== 5. PowerShell 5.1 编码铁律：.ps1 必须 UTF-8 with BOM ===")
for rel in ("安装.ps1", "卸载.ps1", "lib/Common.ps1"):
    p = os.path.join(D, rel.replace("/", os.sep))
    raw = open(p, "rb").read()
    if raw[:3] == b"\xef\xbb\xbf":
        good("%s 带 BOM（%d 字节）" % (rel, len(raw)))
    else:
        fail("%s 缺少 UTF-8 BOM —— Windows PowerShell 5.1 会按 ANSI 解码，中文将乱码" % rel)

print("\n=== 6. 包内文件完整性 ===")
for rel in ("data/GAME.dat", "data/GAME2.dat", "data/d3d9.dll",
            "lib/Common.ps1", "安装.ps1", "卸载.ps1", "README.md", "安装说明.md"):
    p = os.path.join(D, rel.replace("/", os.sep))
    if os.path.exists(p):
        good("%s（%.1f MB）" % (rel, os.path.getsize(p) / 1048576.0))
    else:
        fail("缺少 %s" % rel)

print("\n" + "=" * 60)
print("结果：" + ("全部通过" if ok else "存在问题"))
sys.exit(0 if ok else 1)
