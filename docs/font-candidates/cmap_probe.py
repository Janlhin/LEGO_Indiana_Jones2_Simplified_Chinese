"""独立解析字体 cmap，绕开 fontTools 对某些子表的 IndexError。

用法: python cmap_probe.py <font> [<charset_file>]
"""
import struct
import sys
from fontTools.ttLib import TTFont


def raw_cmap(path):
    t = TTFont(path, fontNumber=0, lazy=True)
    return t.reader["cmap"], t


def parse_cmap(data):
    """返回 {codepoint} —— 只处理 format 4 / 12（Windows Unicode 子表）。"""
    if len(data) < 4:
        return set()
    _ver, n = struct.unpack(">HH", data[:4])
    cps = set()
    for i in range(n):
        off = 4 + i * 8
        pid, eid, sub = struct.unpack(">HHI", data[off:off + 8])
        if pid != 3:          # 只要 Windows 平台
            continue
        if sub + 2 > len(data):
            continue
        fmt = struct.unpack(">H", data[sub:sub + 2])[0]
        if fmt == 4:
            segx2 = struct.unpack(">H", data[sub + 6:sub + 8])[0]
            seg = segx2 // 2
            end_o = sub + 14
            start_o = end_o + segx2 + 2
            delta_o = start_o + segx2
            range_o = delta_o + segx2
            for s in range(seg):
                end = struct.unpack(">H", data[end_o + s * 2:end_o + s * 2 + 2])[0]
                start = struct.unpack(">H", data[start_o + s * 2:start_o + s * 2 + 2])[0]
                delta = struct.unpack(">h", data[delta_o + s * 2:delta_o + s * 2 + 2])[0]
                ro = struct.unpack(">H", data[range_o + s * 2:range_o + s * 2 + 2])[0]
                if start == 0xFFFF:
                    continue
                for c in range(start, end + 1):
                    if ro == 0:
                        g = (c + delta) & 0xFFFF
                    else:
                        gi = range_o + s * 2 + ro + (c - start) * 2
                        if gi + 2 > len(data):
                            continue
                        g = struct.unpack(">H", data[gi:gi + 2])[0]
                        if g:
                            g = (g + delta) & 0xFFFF
                    if g:
                        cps.add(c)
        elif fmt == 12:
            ngroups = struct.unpack(">I", data[sub + 12:sub + 16])[0]
            for k in range(ngroups):
                o = sub + 16 + k * 12
                sc, ec, _sg = struct.unpack(">III", data[o:o + 12])
                for c in range(sc, ec + 1):
                    cps.add(c)
    return cps


def main():
    path = sys.argv[1]
    data, t = raw_cmap(path)
    cps = parse_cmap(data)
    nm = {}
    for r in t["name"].names:
        if r.nameID in (1, 4, 16):
            try:
                nm.setdefault(r.nameID, r.toUnicode())
            except Exception:
                pass
    print(f"{path}")
    print(f"  族名: {nm.get(16) or nm.get(1)} | 字形 {t['maxp'].numGlyphs} | 码位 {len(cps)}")

    if len(sys.argv) > 2:
        need = sorted({c for c in open(sys.argv[2], encoding="utf-8").read() if not c.isspace()})
        miss = [c for c in need if ord(c) not in cps]
        cjk = [c for c in miss if "\u4e00" <= c <= "\u9fff"]
        print(f"  需要 {len(need)} | 缺 {len(miss)} | 缺汉字 {len(cjk)}")
        if miss:
            print(f"  缺字样例: {''.join(miss[:50])}")
    return cps


if __name__ == "__main__":
    main()
