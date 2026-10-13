#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""游戏目录状态跟踪 —— 大文件不入库时，用 md5 清单替代 git 快照。

为什么需要这个
--------------
游戏目录约 4.1 GB，其中四个 .dat 占绝大部分。git 每次 commit 会存一份完整
快照，来回改几次磁盘就撑不住。所以 .dat 不入库，改用本工具记录 md5 值，
照样能精确回答「这一步到底改了哪个文件、内容变没变」。

用法
----
    python game_state.py scan                 生成/更新 md5manifest.txt + install_state.txt
    python game_state.py diff                 与上一次 commit 的清单对比，报告变化
    python game_state.py verify               只比对不写入，有差异时退出码非 0

只读游戏文件，本工具不修改、不删除任何游戏内容。
"""

import hashlib
import os
import subprocess
import sys

try:
    import winreg
except ImportError:
    winreg = None

# 游戏目录：可用环境变量覆盖，便于在副本上测试
GAME_DIR = os.environ.get("CHS_GAMEDIR") or r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2"

MANIFEST = "md5manifest.txt"
STATE = "install_state.txt"

# 大文件只算 md5 不算 sha1，这些是原版数据文件与安装产物
BIG_FILE_THRESHOLD = 8 * 1024 * 1024  # 8 MB

# 需要跳过的目录（Steam 缓存等噪声）
SKIP_DIRS = {".git"}


def md5_of(path, chunk=4 * 1024 * 1024):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def scan_game_dir(root):
    """返回 [(相对路径, 大小, md5), ...]，按路径排序。"""
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            try:
                size = os.path.getsize(full)
                rows.append((rel, size, md5_of(full)))
            except OSError as e:
                rows.append((rel, -1, "ERR:%s" % e))
    rows.sort()
    return rows


def write_manifest(rows, path):
    lines = [
        "# 游戏目录 md5 清单 —— 由 work/tools/game_state.py 自动生成，请勿手改",
        "# 格式: 相对路径<TAB>字节数<TAB>md5",
        "# 大文件（四个 .dat）不入 git，用本清单跟踪变化",
        "",
    ]
    for rel, size, digest in rows:
        lines.append("%s\t%d\t%s" % (rel, size, digest))
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    return path


def read_manifest(path):
    """读回清单，返回 {rel: (size, md5)}；文件不存在返回 None。"""
    if not os.path.exists(path):
        return None
    out = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            out[parts[0]] = (int(parts[1]), parts[2])
    return out


def git_manifest(prev_commit="HEAD", path=MANIFEST):
    """从 git 里取出上一版清单；首次提交返回 None。"""
    try:
        blob = subprocess.run(
            ["git", "show", "%s:%s" % (prev_commit, path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except (OSError, ValueError):
        return None
    if blob.returncode != 0:
        return None
    out = {}
    for line in blob.stdout.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        try:
            out[parts[0]] = (int(parts[1]), parts[2])
        except ValueError:
            continue
    return out


def dump_registry():
    """导出 LucasArts 相关注册表，作为安装状态的一部分。

    git 管不到注册表，所以转成文本文件入库。
    """
    if winreg is None:
        return ["# winreg unavailable (non-Windows)"]

    targets = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\LucasArts", "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\LucasArts", "HKLM"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\LucasArts", "HKLM32"),
    ]
    lines = [
        "# 注册表状态快照 —— 由 work/tools/game_state.py 自动生成，请勿手改",
        "# 说明：游戏自身启动即会写 LanguageVal=1033（英文槽位），非汉化补丁所为。",
        "# 汉化文本已同时写入 ENGLISH 列，故注册表语言值对显示无影响。",
        "",
    ]
    for hive, path, label in targets:
        try:
            root = winreg.OpenKey(hive, path)
        except OSError:
            lines.append("[%s] %s  -> 不存在" % (label, path))
            lines.append("")
            continue
        lines.append("[%s] %s" % (label, path))
        for sub in enumerate_subkeys(root):
            dump_key(hive, path + "\\" + sub, lines, indent=1)
        lines.append("")
    return lines


def enumerate_subkeys(key):
    out = []
    i = 0
    while True:
        try:
            out.append(winreg.EnumKey(key, i))
        except OSError:
            return out
        i += 1


def dump_key(hive, path, lines, indent=0):
    pad = "  " * indent
    try:
        k = winreg.OpenKey(hive, path)
    except OSError:
        return
    i = 0
    while True:
        try:
            name, value, _ = winreg.EnumValue(k, i)
        except OSError:
            break
        lines.append("%s%-24s = %s" % (pad, name, value))
        i += 1
    for sub in enumerate_subkeys(k):
        lines.append("%s[%s]" % (pad, sub))
        dump_key(hive, path + "\\" + sub, lines, indent + 1)


def write_state(path=STATE):
    lines = dump_registry()
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    return path


def do_scan(root):
    print("扫描 %s ..." % root)
    rows = scan_game_dir(root)
    big = [r for r in rows if r[1] > BIG_FILE_THRESHOLD]
    print("文件总数 %d（大文件 %d）" % (len(rows), len(big)))
    for rel, size, _ in big:
        print("  大文件 %-16s %13d B" % (rel, size))
    m = write_manifest(rows, os.path.join(root, MANIFEST))
    print("已写入 %s" % m)
    s = write_state(os.path.join(root, STATE))
    print("已写入 %s" % s)


def do_diff(root):
    cur = read_manifest(os.path.join(root, MANIFEST))
    if cur is None:
        print("当前目录没有 %s，请先运行 scan" % MANIFEST)
        return 2
    prev = git_manifest()
    if prev is None:
        print("git 里还没有 %s（首次提交），无对比基准" % MANIFEST)
        return 0

    added = sorted(set(cur) - set(prev))
    removed = sorted(set(prev) - set(cur))
    modified = sorted(
        k for k in set(cur) & set(prev) if cur[k][1] != prev[k][1]
    )

    if not (added or removed or modified):
        print("与上次 commit 完全一致，无变化")
        return 0

    for k in added:
        print("+ 新增    %-40s %13d B" % (k, cur[k][0]))
    for k in removed:
        print("- 删除    %-40s" % k)
    for k in modified:
        print("~ 修改    %-40s %d -> %d B" % (k, prev[k][0], cur[k][0]))
        if k.lower().endswith(".dat") or prev[k][0] > BIG_FILE_THRESHOLD:
            print("          md5 %s -> %s" % (prev[k][1], cur[k][1]))
    return 0


def do_verify(root):
    on_disk = {r[0]: (r[1], r[2]) for r in scan_game_dir(root)}
    recorded = read_manifest(os.path.join(root, MANIFEST))
    if recorded is None:
        print("没有 %s，无法校验" % MANIFEST)
        return 2
    bad = []
    for k, v in recorded.items():
        if k not in on_disk:
            bad.append("缺失    %s" % k)
        elif on_disk[k][1] != v[1]:
            bad.append("md5变化 %s" % k)
    for line in bad:
        print(line)
    if bad:
        print("共 %d 项与清单不符" % len(bad))
        return 1
    print("全部 %d 个文件与清单一致" % len(recorded))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    root = sys.argv[2] if len(sys.argv) > 2 else GAME_DIR
    if not os.path.isdir(root):
        print("目录不存在: %s" % root)
        return 2
    if cmd == "scan":
        do_scan(root)
        return 0
    if cmd == "diff":
        return do_diff(root)
    if cmd == "verify":
        return do_verify(root)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())