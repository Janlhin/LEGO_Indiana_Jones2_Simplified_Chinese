# -*- coding: utf-8 -*-
"""评估给 FT2 字体补字形的可行性：atlas 剩余空间、各表增长量、重建后体积变化。"""
import os
import struct as _s
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttdat import TTDat
from ft2 import FT2

G = r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2"
FONT_KEY = "gui\\Font\\FONT_NXG.FT2"

WANT = "缘采说明材"


def main():
    for dat_name in ("GAME.dat", "GAME2.dat"):
        dp = os.path.join(G, dat_name)
        if not os.path.exists(dp):
            continue
        d = TTDat(dp)
        rec = None
        for r in d.files:
            if (r["name"] or "").lower() == FONT_KEY.lower():
                rec = r
                break
        if rec is None:
            continue

        raw = d.read_file(rec)
        f = FT2(raw)
        b = f.raw
        H = int(round(f.height))

        print("=== %s / %s ===" % (dat_name, FONT_KEY))
        print("FT2 总长 %d 字节 (0x%X)   DAT 记录原大小 %s" % (len(raw), len(raw), rec.get("size")))
        print("numChars=%d  height=%s  baseline=%s  spaceWidth=%s"
              % (f.num_chars, f.height, f.baseline, f.space_width))
        print("posTable %d 项 / charsTable %d 项 / kerning %d 项"
              % (len(f.positions), len(f.chars), len(f.kerning)))
        print("表结束 @0x%X   DDS @0x%X   间隙 %d 字节"
              % (f.table_end, f.dds_off, f.dds_off - f.table_end))

        dds = raw[f.dds_off:]
        w, h = _s.unpack_from('<II', dds, 12)
        print("DDS 尺寸 %dx%d   字格边长 %d" % (w, h, H))

        cols = w // H
        rows = h // H
        total = cols * rows
        used = len(f.positions)
        print("字格布局 %d 列 x %d 行 = %d 格   已用 %d   剩余 %d"
              % (cols, rows, total, used, total - used))

        xs = [p[0] for p in f.positions]
        ys = [p[1] for p in f.positions]
        print("posTable x %.0f..%.0f   y %.0f..%.0f   w 最大 %.0f"
              % (min(xs), max(xs), min(ys), max(ys), max(p[2] for p in f.positions)))

        # 现有字形索引最大值 —— 决定新字形能否续编
        idxs = [c[1] for c in f.chars if c[1] != 0xFFFF]
        print("字形索引范围 %d..%d（末位 ffff 为结束符）" % (min(idxs), max(idxs)))
        print("codepoint 为 u16 —— 补字不受码位上限限制")

        # 增长量估算
        grow = len(WANT) * (12 + 4)   # posTable 12B + charsTable 4B 每字
        print()
        print("补 %d 字（%s）需要：" % (len(WANT), WANT))
        print("  posTable   +%d 字节" % (len(WANT) * 12))
        print("  charsTable +%d 字节" % (len(WANT) * 4))
        print("  头部 numChars/unicodeTableSize/各表 size 字段需同步 +4 处")
        print("  合计约 +%d 字节（间隙 %d 字节，当前够用：%s）"
              % (grow, f.dds_off - f.table_end,
                 "是" if f.dds_off - f.table_end >= grow else "否，需重排"))
        print("  atlas 剩余 %d 格，补 %d 字：%s"
              % (total - used, len(WANT), "空间充足" if total - used >= len(WANT) else "不足"))
        return 0

    print("未找到字体记录")
    return 1


if __name__ == "__main__":
    sys.exit(main())
