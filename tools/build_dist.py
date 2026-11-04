# -*- coding: utf-8 -*-
"""组装并打包 LEGO Indiana Jones 2 简体中文补丁的分发包。

分发包结构（与 patch/README.md 里的目录树一致）::

    LEGO_Indiana_Jones2_Simplified_Chinese_v<版本>/
    ├── 安装.ps1
    ├── 卸载.ps1
    ├── lib/Common.ps1
    ├── README.md
    ├── 安装说明.md
    ├── 安装说明.txt
    └── data/
        ├── GAME.dat
        ├── GAME2.dat
        ├── d3d9.dll
        └── Audio/_VO/**

仓库里 patch/ 是「staging 布局」：payload/lib 与 payload/data 会被提升到
分发包的根下。源数据（两个 DAT，合计约 1.86 GiB）不入库，从本机游戏目录取。

分卷
----
GitHub Release 单个附件上限 2 GB，而两个 DAT 压缩后仍逼近这条线，
因此默认拆成两个分卷，两个分卷解到同一个目录即可拼出完整包::

    LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0_part1.zip   脚本 + 文档 + GAME.dat + d3d9.dll + 语音
    LEGO_Indiana_Jones2_Simplified_Chinese_v2.0.0_part2.zip   GAME2.dat

用法::

    python tools/build_dist.py --game "D:\\SteamLibrary\\steamapps\\common\\Lego Indiana Jones 2"
    python tools/build_dist.py --game ... --out dist --level 1
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITHUB_ASSET_LIMIT = 2 * 1024 * 1024 * 1024 - 1   # GitHub Release 单附件 2 GB 上限


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_patch_version(patch_dir):
    """版本号的唯一来源是 payload/lib/Common.ps1 里的 $script:PatchVersion。"""
    common = os.path.join(patch_dir, "payload", "lib", "Common.ps1")
    with open(common, "r", encoding="utf-8-sig") as f:
        m = re.search(r"\$script:PatchVersion\s*=\s*'([^']+)'", f.read())
    if not m:
        raise SystemExit("在 %s 里找不到 $script:PatchVersion" % common)
    return m.group(1)


def collect(patch_dir, game_dir, vo_dir):
    """返回 [(zip 内路径, 磁盘来源)]，顺序即写入顺序。"""
    items = [
        ("安装.ps1", os.path.join(patch_dir, "安装.ps1")),
        ("卸载.ps1", os.path.join(patch_dir, "卸载.ps1")),
        ("lib/Common.ps1", os.path.join(patch_dir, "payload", "lib", "Common.ps1")),
        ("README.md", os.path.join(patch_dir, "README.md")),
        ("安装说明.md", os.path.join(patch_dir, "安装说明.md")),
        ("安装说明.txt", os.path.join(patch_dir, "安装说明.txt")),
        ("data/GAME.dat", os.path.join(game_dir, "GAME.dat")),
        ("data/GAME2.dat", os.path.join(game_dir, "GAME2.dat")),
        ("data/d3d9.dll", os.path.join(game_dir, "d3d9.dll")),
    ]
    # 角色语音修复（可选，但打包里有）
    vo_src = vo_dir or os.path.join(game_dir, "Audio", "_VO")
    if os.path.isdir(vo_src):
        for root, _dirs, files in os.walk(vo_src):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, vo_src).replace("\\", "/")
                items.append(("data/Audio/_VO/" + rel, full))
    return items


def write_zip(path, top, items, level):
    missing = [(arc, src) for arc, src in items if not os.path.exists(src)]
    if missing:
        for arc, src in missing:
            print("  缺少来源文件: %s  <- %s" % (arc, src))
        raise SystemExit("来源文件不全，已中止（未生成任何包）")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=level) as zf:
        for arc, src in items:
            zf.write(src, "%s/%s" % (top, arc))
    return os.path.getsize(path)


def main():
    ap = argparse.ArgumentParser(description="打包 LEGO Indiana Jones 2 汉化补丁分发包")
    ap.add_argument("--game", required=True, help="游戏目录（含 GAME.dat / GAME2.dat / d3d9.dll）")
    ap.add_argument("--patch", default=os.path.join(REPO, "patch"), help="patch 目录（staging 布局）")
    ap.add_argument("--out", default=os.path.join(REPO, "dist"), help="输出目录")
    ap.add_argument("--level", type=int, default=1, help="deflate 压缩级别 0-9（1 最快）")
    ap.add_argument("--vo-dir", default=None, help="角色语音目录，默认取游戏目录下的 Audio\\_VO")
    ap.add_argument("--no-split", action="store_true", help="不拆分卷，输出单个 zip（可能超 2 GB 上限）")
    a = ap.parse_args()

    version = read_patch_version(a.patch)
    top = "LEGO_Indiana_Jones2_Simplified_Chinese_v%s" % version
    items = collect(a.patch, a.game, a.vo_dir)
    os.makedirs(a.out, exist_ok=True)

    # 分卷：part1 带脚本与文档 + GAME.dat + d3d9.dll + 语音；part2 只带 GAME2.dat
    part1 = [it for it in items if it[0] != "data/GAME2.dat"]
    part2 = [it for it in items if it[0] == "data/GAME2.dat"]

    print("版本 %s    来源 %s" % (version, a.game))
    print("条目 %d 个" % len(items))
    print()

    outputs = []
    if a.no_split:
        outputs.append((os.path.join(a.out, top + ".zip"), items))
    else:
        outputs.append((os.path.join(a.out, top + "_part1.zip"), part1))
        outputs.append((os.path.join(a.out, top + "_part2.zip"), part2))

    for path, group in outputs:
        size = write_zip(path, top, group, a.level)
        flag = "OK" if size <= GITHUB_ASSET_LIMIT else "!! 超过 GitHub 2 GB 上限"
        print("  %-46s %9.1f MB   %s" % (os.path.basename(path), size / 1048576, flag))
        if size > GITHUB_ASSET_LIMIT:
            raise SystemExit("单包超过 GitHub Release 的 2 GB 上限，请改用分卷")

    total = sum(os.path.getsize(p) for p, _ in outputs)
    print()
    print("共 %d 个包，合计 %.1f MB" % (len(outputs), total / 1048576))
    print()
    print("上传命令：")
    for path, _ in outputs:
        print("  gh release upload 2.0.0 \"%s\"" % path)


if __name__ == "__main__":
    main()
