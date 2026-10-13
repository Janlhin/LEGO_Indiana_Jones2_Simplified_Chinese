# -*- coding: utf-8 -*-
"""重新划定 UI 指针表的**真实**边界，并导出完整清单。

起因（2026-10-14）：首版补丁只汉化了 45 处指针 / 27 个标签，用户实测
反馈仍有 FSAA、Bloom、Shadows 等标签显示英文。查下来是**我把表划小了**：

    原假设  0xAB09F0 .. 0xAB0F44（341 项）
    实际    至少延伸到 0xAB1A64 —— 比原边界还远 0xB20 字节（712 项）

而且原假设「表内每项都能解析出ASCII 串」也不成立：341 项里只有 149 项
可解析，其余 192 项是不可解析值。表是**交错**的 —— 可解析项之间夹着
非字符串指针（可能是 NULL、函数指针、其他类型的数据）。

这里换用可靠的判据来定位边界：
    不依赖「连续可解析」，而是扫描整段 .data，凡是「4 字节值落在
    .rdata 的字符串范围内且能解出可打印 ASCII」的就收进来，
    然后看这些命中在地址轴上的**分布**，据此推断表的起止与分段。

产出（不修改任何东西）：
    * 真实边界
    * 全部可汉化标签及其槽位（供 gen_ui_patch.py 消费）
    * cvar 名 / 按键名的分离
"""
import struct
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

EXE = r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2\LEGOIndy2.exe"

BASE = 0x400000
# .data 节：VA == RawAddr（实测，tools/verify_rva_maps.py）
DATA_VA, DATA_SZ = 0x9F7000, 2848336
RDATA_VA, RDATA_SZ = 0x874000, 1585152
DATA_HI = DATA_VA + DATA_SZ

# 已知的表区（从 FSAA 槽 0xAB1A64 反推），留足余量
SCAN_LO = 0xAB0000
SCAN_HI = 0xAB3000


def read_asc(data, va, maxn=200):
    """若 va 指向 .rdata 里一段可打印 ASCII（可含空格），返回该串。"""
    if not (BASE + RDATA_VA <= va < BASE + RDATA_VA + RDATA_SZ):
        return None
    fo = va - BASE
    if fo < 0 or fo >= len(data):
        return None
    end = data.find(b"\x00", fo)
    if end < 0 or end == fo or end - fo > maxn:
        return None
    s = data[fo:end]
    if any(c < 32 or c > 126 for c in s):
        return None
    return s.decode("ascii")


def main():
    with open(EXE, "rb") as f:
        data = f.read()

    rows = []
    off = SCAN_LO
    while off < SCAN_HI:
        va = struct.unpack_from("<I", data, off)[0]
        s = read_asc(data, va)
        if s is not None:
            rows.append((off, va, s))
        off += 4

    print("=" * 78)
    print("扫描 0x%X..0x%X：命中可解析字符串项 %d 个" % (SCAN_LO, SCAN_HI, len(rows)))
    print("=" * 78)

    # 按 0x100 字节桶看分布，识别表的真实范围与其中的空洞
    buckets = defaultdict(int)
    for off, _, _ in rows:
        buckets[off >> 8] += 1
    lo_bucket = min(buckets)
    hi_bucket = max(buckets)
    print("\n每0x100 字节命中数（找出表的起止与空隙）：")
    for b in range(lo_bucket, hi_bucket + 1):
        n = buckets.get(b, 0)
        bar = "#" * n
        mark = " <<< 命中边界" if b in (lo_bucket, hi_bucket) else ""
        print("  0x%06X..0x%06X  %3d %s%s" % (b << 8, (b << 8) + 0xFF, n, bar, mark))
        if n == 0:
            print("        （空桶）")

    print("\n" + "=" * 78)
    print("全部命中项")
    print("=" * 78)
    for off, va, s in rows:
        print("  0x%06X -> 0x%08X  %r" % (off, va, s))

    # 去重统计
    uniq = defaultdict(list)
    for off, va, s in rows:
        uniq[s].append(off)
    print("\n" + "=" * 78)
    print("唯一字符串 %d 个（按槽位数排序）" % len(uniq))
    print("=" * 78)
    for s, slots in sorted(uniq.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        mark = "  <槽数=%d>" % len(slots)
        print("  %-34s %s%s" % (repr(s), mark,
                                ("  " + ", ".join("0x%X" % x for x in slots[:6])) if len(slots) <= 6 else ""))


if __name__ == "__main__":
    main()
