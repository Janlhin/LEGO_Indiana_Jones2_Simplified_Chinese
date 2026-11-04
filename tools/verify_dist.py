# -*- coding: utf-8 -*-
"""校验分发包（两个分卷 zip）是否符合发布要求。

v2.0.0 起分发包由 tools/build_dist.py 打成两个分卷，取代了 v1.0 时代
「dist/ 单目录 + .bat」的结构。本脚本直接读 zip 内容做端到端校验：

  1. 分卷齐备、命名与 $script:PatchVersion 一致
  2. 每个分卷都在 GitHub Release 的 2 GB 单附件上限内
  3. 两个分卷解到同一目录后，包内容完整（脚本/文档/lib/data）
  4. 包内 .ps1 带 UTF-8 BOM、.txt 带 BOM 且全 CRLF
  5. 包内不再残留任何 .bat
"""
import os
import re
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
GITHUB_ASSET_LIMIT = 2 * 1024 * 1024 * 1024 - 1

ok = True


def fail(msg):
    global ok
    ok = False
    print("  [FAIL] " + msg)


def good(msg):
    print("  [ok]   " + msg)


def skip(msg):
    print("  [--]   " + msg)


# ---------------------------------------------------------------- 版本号
common = os.path.join(REPO, "patch", "payload", "lib", "Common.ps1")
with open(common, encoding="utf-8-sig") as fh:
    m = re.search(r"\$script:PatchVersion\s*=\s*'([0-9]+\.[0-9]+\.[0-9]+)'", fh.read())
ver = m.group(1) if m else None
top = "LEGO_Indiana_Jones2_Simplified_Chinese_v%s" % ver if ver else None

print("=== 1. 分卷齐备 ===")
if ver is None:
    fail("读不到 $script:PatchVersion")
    sys.exit(1)
good("版本 %s" % ver)

zips = []
for suffix in ("_part1.zip", "_part2.zip"):
    p = os.path.join(DIST, top + suffix)
    if os.path.exists(p):
        zips.append(p)
        good("%s（%.1f MB）" % (os.path.basename(p), os.path.getsize(p) / 1048576.0))
    else:
        fail("缺少 %s —— 先跑 python tools/build_dist.py --game \"<游戏目录>\"" % (top + suffix))

if len(zips) < 2:
    print("\n" + "=" * 60)
    print("结果：存在问题")
    sys.exit(1)

print("\n=== 2. GitHub Release 2 GB 单附件上限 ===")
for p in zips:
    size = os.path.getsize(p)
    if size <= GITHUB_ASSET_LIMIT:
        good("%s 未超限（余量 %.0f MB）"
             % (os.path.basename(p), (GITHUB_ASSET_LIMIT - size) / 1048576.0))
    else:
        fail("%s 超过 2 GB 上限，GitHub 会拒绝上传" % os.path.basename(p))

print("\n=== 3. 两个分卷的顶层目录一致 ===")
tops = set()
for p in zips:
    with zipfile.ZipFile(p) as zf:
        names = zf.namelist()
    if not names:
        fail("%s 是空包" % os.path.basename(p))
        continue
    tops.add(names[0].split("/")[0])
if len(tops) == 1:
    good("顶层目录统一为 %s" % tops.pop())
else:
    fail("顶层目录不一致：%s —— 两个分卷必须解到同一目录" % sorted(tops))

print("\n=== 4. 包内容完整性（两个分卷合并后）===")
allnames = []
for p in zips:
    with zipfile.ZipFile(p) as zf:
        allnames.extend(zf.namelist())

# 去掉顶层目录后比较
stripped = [n.split("/", 1)[1] for n in allnames if "/" in n]
REQUIRED = ["安装.ps1", "卸载.ps1", "lib/Common.ps1", "README.md",
            "安装说明.md", "安装说明.txt",
            "data/GAME.dat", "data/GAME2.dat", "data/d3d9.dll"]
for rel in REQUIRED:
    if rel in stripped:
        good(rel)
    else:
        fail("缺少 %s" % rel)

vo = [n for n in stripped if n.startswith("data/Audio/_VO/")]
if len(vo) >= 46:
    good("data/Audio/_VO/ %d 个文件（角色语音修复）" % len(vo))
else:
    fail("data/Audio/_VO/ 只有 %d 个文件，应为 46 个" % len(vo))

print("\n=== 5. 包内编码 ===")
for p in zips:
    with zipfile.ZipFile(p) as zf:
        for rel in REQUIRED:
            hit = [n for n in zf.namelist() if n.endswith("/" + rel)]
            if not hit:
                continue
            raw = zf.read(hit[0])
            if rel.endswith(".ps1"):
                if raw[:3] == b"\xef\xbb\xbf":
                    good("%s 带 UTF-8 BOM" % rel)
                else:
                    fail("%s 缺少 UTF-8 BOM" % rel)
                crlf = raw.count(b"\r\n")
                lf = raw.count(b"\n") - crlf
                if crlf > 0 and lf == 0:
                    good("%s 全部 CRLF 换行（%d 行）" % (rel, crlf))
                else:
                    fail("%s 换行不是纯 CRLF（CRLF %d / 纯 LF %d）"
                         % (rel, crlf, lf))
            elif rel.endswith(".txt"):
                crlf = raw.count(b"\r\n")
                lf = raw.count(b"\n") - crlf
                if raw[:3] == b"\xef\xbb\xbf":
                    good("%s 带 UTF-8 BOM" % rel)
                else:
                    fail("%s 缺少 UTF-8 BOM" % rel)
                if lf == 0:
                    good("%s 全部 CRLF 换行（%d 行）" % (rel, crlf))
                else:
                    fail("%s 混有 %d 个纯 LF 换行" % (rel, lf))

print("\n=== 6. 不应再有 .bat ===")
bats = [n for n in allnames if n.lower().endswith(".bat")]
if bats:
    fail("包内仍有 .bat：%s" % bats)
else:
    good("包内无任何 .bat（v2.0.0 起纯 PowerShell）")

print("\n" + "=" * 60)
print("结果：" + ("全部通过" if ok else "存在问题"))
sys.exit(0 if ok else 1)
