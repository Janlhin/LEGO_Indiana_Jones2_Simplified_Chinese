# -*- coding: utf-8 -*-
"""导出 .data 节里那张 UI 字符串指针表的完整结构，供实现补丁时使用。

已经查清的机制（这是本项目最重要的一次逆向结论）：

    exe .data 节（原始偏移 0xAB09F0 起）有一张 **字符串指针表**，
    每项 4 字节，内容是 .rdata 里某个 ASCII 字符串的 VA。

    表的布局（关键：三类东西挤在同一张表里）：

      0xAB09F0 .. 0xAB0B48  cvar 名   ScreenWidth / ShadowMethod /
                                        MusicEnabled / ...
                                        —— 这些是 pcconfig.txt 的键名，
                                           改了游戏读不到配置，**绝对不能动**

      0xAB0B5C .. 0xAB0C24  英文 UI   Quit / Back / OK / Cancel /
                                        Video Settings / Vertical Sync / ...
                                        —— **汉化目标就是这一段**

      0xAB0CA4 .. 0xAB0D24  英文 UI 的第二份副本（Builder 菜单）
      0xAB0DEC .. 0xAB0E6C  法语
      0xAB0E9C .. 0xAB0F34  匈牙利语

    为什么之前两条路都失败：
      1. 原地改字符串内容 -> 零余量，且 UI 走 CP1252/1254 解码，
         UTF-8 字节会被逐字节拆成西欧字符（乱码）
      2. 硬改 exe 文件 -> 触发 Steam DRM（.bind 节可执行 + STEAM 标记）

    为什么这次可行：
      指针表在 .data 节，**运行时可写**。只需在 DLL 里把英文那几项
      的指针改指向我们自己准备的 GBK 字符串缓冲区，
      指针本身的 4 字节大小不变 —— 不碰文件、不碰字符串内容、
      不影响 cvar、不影响其他语言。

本脚本只导出信息，不改任何东西。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")

EXE = r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2\LEGOIndy2.exe"

BASE = 0x400000
RDATA_VA = 0x874000
RDATA_RA = 0x874000          # .rdata 的 VA == RawAddr（实测）
RDATA_SZ = 1585152

TABLE_LO = 0xAB09F0
TABLE_HI = 0xAB0F34 + 16

# 段落边界（实测得出）
CVAR_END = 0xAB0B48           # 此前的都是 cvar
EN_UI_1 = (0xAB0B5C, 0xAB0C24)
EN_UI_2 = (0xAB0CA4, 0xAB0D24)
FR_UI = (0xAB0DEC, 0xAB0E6C)
HU_UI = (0xAB0E9C, 0xAB0F34)


def load():
    with open(EXE, "rb") as f:
        return f.read()


def read_str(data, fo):
    end = data.find(b"\x00", fo)
    if end < 0:
        return None
    s = data[fo:end]
    if not s or any(c < 32 or c > 126 for c in s):
        return None
    return s.decode("ascii")


def walk(data):
    """把表里每一项解析成 (文件偏移, VA, 字符串)。"""
    out = []
    off = TABLE_LO
    while off < TABLE_HI:
        va = struct.unpack_from("<I", data, off)[0]
        rec = None
        if BASE + RDATA_VA <= va < BASE + RDATA_VA + RDATA_SZ:
            fo = va - BASE + (RDATA_RA - RDATA_VA)
            s = read_str(data, fo)
            if s and len(s) < 120:
                rec = (off, va, fo, s)
        out.append((off, va, rec))
        off += 4
    return out


def seg_name(off):
    if off <= CVAR_END:
        return "CVAR"
    for name, (a, b) in (("EN-1", EN_UI_1), ("EN-2", EN_UI_2),
                         ("FR", FR_UI), ("HU", HU_UI)):
        if a <= off <= b + 8:
            return name
    return "?"


def main():
    data = load()
    items = walk(data)

    print("=" * 76)
    print("UI 字符串指针表  (exe .data 节, 文件偏移 0x%X..0x%X)" % (TABLE_LO, TABLE_HI))
    print("=" * 76)
    print("映像基址 0x%08X   .rdata VA=RawAddr=0x%X" % (BASE, RDATA_VA))
    print()

    buckets = {}
    for off, va, rec in items:
        s = seg_name(off)
        buckets.setdefault(s, []).append((off, va, rec[2], rec[3]) if rec else (off, va, None, None))

    for seg in ("CVAR", "EN-1", "EN-2", "FR", "HU"):
        rows = buckets.get(seg, [])
        good = [r for r in rows if r[3]]
        print("-" * 76)
        print("[%s]  %d 项（其中 %d 项可解析出字符串）" % (seg, len(rows), len(good)))
        print("-" * 76)
        for off, va, fo, s in good:
            print("  ptr@0x%08X -> str@0x%08X  %r" % (off, va, s))
        print()

    # 汉化目标汇总
    en_rows = buckets.get("EN-1", []) + buckets.get("EN-2", [])
    en_rows = [r for r in en_rows if r[3]]
    seen = {}
    for off, va, fo, s in en_rows:
        seen.setdefault(s, []).append(off)

    print("=" * 76)
    print("汉化目标：英文 UI 标签 %d 条（去重后 %d 个）" % (len(en_rows), len(seen)))
    print("=" * 76)
    for s, ptrs in sorted(seen.items()):
        print("  %-34r 出现 %d 处  ptr@%s" % (s, len(ptrs),
                                              ", ".join("0x%X" % p for p in ptrs)))


if __name__ == "__main__":
    main()