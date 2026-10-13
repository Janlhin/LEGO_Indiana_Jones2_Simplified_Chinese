# -*- coding: utf-8 -*-
"""逐个检查候选译名的字形覆盖，用于在不重建字体的前提下挑出可用的更准确译名。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttdat import TTDat
from ft2 import FT2

G = r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2"
FONT_KEY = "gui\\Font\\FONT_NXG.FT2"

CANDS = [
    # Edge AA 系
    "边缘抗锯齿", "边角抗锯齿", "边缘锯齿", "边角锯齿", "抗锯齿",
    "边缘平滑", "边角平滑", "多采样抗锯齿",
    # Show Game Controls 系
    "显示操作说明", "显示游戏按键", "显示控制说明", "显示按键说明",
    "显示按键表", "按键表", "按键说明", "显示操作键位", "显示按键",
    "游戏按键说明", "显示按键列表", "查看按键表",
    # Texture Quality 系
    "材质质量", "纹理质量", "材质细节", "纹理细节", "贴图质量",
    # Ambient Occlusion 系
    "边缘光遮蔽", "环境光遮蔽",
    # 其他易缺字标签的候选
    "动态光影质量", "动态阴影质量", "光影质量",
    "需要重启游戏才能让这些设置生效", "重启游戏后设置生效",
    # FSAA = Full Screen Anti-Aliasing
    "全屏抗锯齿", "全屏边缘抗锯齿", "全屏边角抗锯齿", "全屏多采样抗锯齿",
    "多重采样抗锯齿", "全屏锯齿",
]


def main():
    for dat_name in ("GAME.dat", "GAME2.dat"):
        dp = os.path.join(G, dat_name)
        if not os.path.exists(dp):
            continue
        d = TTDat(dp)
        for r in d.files:
            if (r["name"] or "").lower() != FONT_KEY.lower():
                continue
            f = FT2(d.read_file(r))
            cps = set()
            for it in f.chars:
                if isinstance(it, (list, tuple)) and it:
                    cps.add(it[0])
                elif isinstance(it, int):
                    cps.add(it)
            break
        if cps:
            break
    if cps is None:
        print("!! 未找到字体记录")
        return 1
    print("字形数 %d\n" % len(cps))
    for c in CANDS:
        miss = [ch for ch in c if ord(ch) not in cps]
        print(("OK   " if not miss else "MISS ") + c + ("" if not miss else "   缺:" + "".join(miss)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
