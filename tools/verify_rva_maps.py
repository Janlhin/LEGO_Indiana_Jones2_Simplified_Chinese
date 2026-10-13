# -*- coding: utf-8 -*-
"""核对 UI 指针表的 RVA 换算：文件偏移 / 节内偏移 / 运行时虚拟地址 三者关系。

这是一个**关乎补丁是否写错位置**的核对，必须查实。

背景：.rdata 段实测 VA == RawAddr（0x874000），所以早先脚本用
    fo = va - BASE + (RDATA_RA - RDATA_VA)
把「字符串 VA」换成「文件偏移」是对的。但这只对 .rdata 成立。

指针表本身在 .data 段。.data 段的 VA 与 RawAddr **未必**相等：
PE 加载时按 VirtualAddress 放置，RawAddr 只是文件里的位置。
所以若直接把文件偏移当 RVA 用，补丁会写到错误的内存地址。

本脚本实读节表，输出三者的精确关系，并给出正确 RVA。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")

EXE = r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2\LEGOIndy2.exe"
TABLE_LO = 0xAB09F0
TABLE_HI = 0xAB0F34 + 16


def sections(raw):
    e_lfanew = struct.unpack_from("<I", raw, 0x3C)[0]
    assert raw[e_lfanew:e_lfanew + 4] == b"PE\x00\x00"
    coff = e_lfanew + 4
    nsec, = struct.unpack_from("<H", raw, coff + 2)
    optsz, = struct.unpack_from("<H", raw, coff + 16)
    opt = coff + 20
    magic, = struct.unpack_from("<H", raw, opt)
    assert magic == 0x10B, "不是 PE32"
    base, = struct.unpack_from("<I", raw, opt + 28)
    secoff = opt + optsz
    out = []
    for i in range(nsec):
        o = secoff + i * 40
        name = raw[o:o + 8].rstrip(b"\x00").decode("ascii", "replace")
        vsz, va, rsz, ra = struct.unpack_from("<IIII", raw, o + 8)
        out.append((name, vsz, va, rsz, ra))
    return base, out


def main():
    raw = open(EXE, "rb").read()
    base, secs = sections(raw)

    print("=" * 74)
    print("ImageBase = 0x%08X" % base)
    print("=" * 74)
    print("%-10s %10s %10s %10s %10s  %s" % ("节", "VirtSize", "VA", "RawSize", "RawAddr", "VA==Raw?"))
    holder = None
    for name, vsz, va, rsz, ra in secs:
        eq = "同" if va == ra else "不同 <<<"
        print("%-10s %10d 0x%08X %10d 0x%08X  %s" % (name, vsz, va, rsz, ra, eq))
        if ra <= TABLE_LO < ra + rsz:
            holder = (name, vsz, va, rsz, ra)
    print()

    if not holder:
        print("!! 指针表文件偏移 0x%X 不在任何节内" % TABLE_LO)
        sys.exit(1)

    name, vsz, va, rsz, ra = holder
    delta_va = va - ra
    print("指针表所在节：%s   VA=0x%X  RawAddr=0x%X  VA-RawAddr=%d" % (name, va, ra, delta_va))
    print()
    print("指针表首项：")
    print("  文件偏移0x%X" % TABLE_LO)
    print("  节内偏移      0x%X" % (TABLE_LO - ra))
    print("  正确 RVA      0x%X   (= VA + 节内偏移)" % (va + (TABLE_LO - ra)))
    print("  错误 RVA      0x%X   (= 文件偏移 - ImageBase，会写错位置)" % (TABLE_LO - base))
    print()

    if delta_va == 0:
        print(">>> 本exe 该节 VA == RawAddr，两种算法结果相同，补丁位置正确。")
    else:
        print(">>> VA != RawAddr，必须改用 0x%X 作为 RVA 基址" % va)
        print(">>> gen_ui_patch.py 目前算的是文件偏移-ImageBase = 0x%X —— 需要修" % (TABLE_LO - base))

    print()
    print("跨度校验：")
    print("  表末文件偏移  0x%X" % TABLE_HI)
    print("  节末文件偏移  0x%X" % (ra + rsz))
    if TABLE_HI > ra + rsz:
        print("  !! 超出节范围")
        # 用 VirtualSize 再判
        print("  节末内存偏移  0x%X(= VA+VSZ，内存里比文件里长)" % (va + vsz))


if __name__ == "__main__":
    main()
