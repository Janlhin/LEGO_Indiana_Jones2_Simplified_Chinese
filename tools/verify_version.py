# -*- coding: utf-8 -*-
"""校验：版本号只在 Common.ps1 定义一次，各处引用一致，且 PS1 保持 UTF-8 with BOM。

v2.0.0 起校验对象是仓库里的 patch/ staging 布局（不是旧的 dist 单目录）——
分发包已改为由 tools/build_dist.py 打成两个分卷 zip，包内结构的校验
移到 verify_dist.py。
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(REPO, "patch")

ok = True


def fail(msg):
    global ok
    ok = False
    print("  [FAIL] " + msg)


def good(msg):
    print("  [ok]   " + msg)


print("=== 1. 版本号唯一来源 ===")
common = os.path.join(D, "payload", "lib", "Common.ps1")
with open(common, encoding="utf-8-sig") as fh:
    src = fh.read()
m = re.search(r"\$script:PatchVersion\s*=\s*'([0-9]+\.[0-9]+\.[0-9]+)'", src)
if not m:
    fail("Common.ps1 里找不到 $PatchVersion 定义")
    ver = None
else:
    ver = m.group(1)
    good("Common.ps1 定义 $script:PatchVersion = %s" % ver)

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
DOCS = [
    ("patch/README.md", os.path.join(D, "README.md")),
    ("patch/安装说明.md", os.path.join(D, "安装说明.md")),
    ("patch/安装说明.txt", os.path.join(D, "安装说明.txt")),
    ("README.md", os.path.join(REPO, "README.md")),
    ("CHANGELOG.md", os.path.join(REPO, "CHANGELOG.md")),
]
for label, p in DOCS:
    if not os.path.exists(p):
        fail("缺少 %s" % label)
        continue
    with open(p, encoding="utf-8-sig") as fh:
        s = fh.read()
    if ver and ver in s:
        good("%s 含版本号 %s" % (label, ver))
    else:
        fail("%s 未含版本号 %s" % (label, ver))
    stale = re.findall(r"CHS_v(\d+\.\d+(?:\.\d+)?)", s)
    stale = [x for x in stale if x != ver]
    if stale:
        fail("%s 仍引用旧目录名版本: %s" % (label, stale))
    else:
        good("%s 无残留的旧目录名版本引用" % label)

print("\n=== 4. PowerShell 5.1 编码铁律：.ps1 必须 UTF-8 with BOM ===")
for rel in ("安装.ps1", "卸载.ps1", "payload/lib/Common.ps1"):
    p = os.path.join(D, rel.replace("/", os.sep))
    raw = open(p, "rb").read()
    if raw[:3] == b"\xef\xbb\xbf":
        good("%s 带 BOM（%d 字节）" % (rel, len(raw)))
    else:
        fail("%s 缺少 UTF-8 BOM —— Windows PowerShell 5.1 会按 ANSI 解码，中文将乱码" % rel)

print("\n=== 5. staging 布局完整性 ===")
STAGING = [
    "安装.ps1",
    "卸载.ps1",
    "README.md",
    "安装说明.md",
    "安装说明.txt",
    "payload/lib/Common.ps1",
]
for rel in STAGING:
    p = os.path.join(D, rel.replace("/", os.sep))
    if os.path.exists(p):
        good("%s（%.1f KB）" % (rel, os.path.getsize(p) / 1024.0))
    else:
        fail("缺少 %s" % rel)

print("\n=== 6. 安装说明.txt 编码（纯文本版：UTF-8 BOM + CRLF）===")
txt = os.path.join(D, "安装说明.txt")
if os.path.exists(txt):
    raw = open(txt, "rb").read()
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    if raw[:3] == b"\xef\xbb\xbf":
        good("安装说明.txt 带 UTF-8 BOM")
    else:
        fail("安装说明.txt 缺少 UTF-8 BOM —— 部分记事本会把中文显示为乱码")
    if lf == 0:
        good("安装说明.txt 全部为 CRLF 换行（%d 行）" % crlf)
    else:
        fail("安装说明.txt 混有 %d 个纯 LF 换行" % lf)
else:
    fail("缺少 安装说明.txt")

print("\n=== 7. 安装说明.md 与 安装说明.txt 同源 ===")
md = os.path.join(D, "安装说明.md")
if os.path.exists(md) and os.path.exists(txt):
    with open(md, encoding="utf-8-sig") as fh:
        s_md = fh.read()
    with open(txt, encoding="utf-8-sig") as fh:
        s_txt = fh.read()
    for probe in ("安装.ps1", "卸载.ps1", "backup_chs", "d3d9.dll", "GAME2.dat"):
        if probe in s_md and probe in s_txt:
            good("两份说明都覆盖 %s" % probe)
        else:
            fail("两份说明对 %s 的覆盖不一致" % probe)

print("\n" + "=" * 60)
print("结果：" + ("全部通过" if ok else "存在问题"))
sys.exit(0 if ok else 1)
