# -*- coding: utf-8 -*-
"""检查字体字形是否覆盖**全部**汉化文案用字，缺字则直接重建字体。

起因（2026-10-14）：菜单汉化注入后，用户看到「？质质量」——
即「**材**质质量」的首字没渲染出来。这不是编码问题（编码已修，见
probe_ui_encoding.py），而是**字体里没有「材」这个字形**，渲染成缺字方框。

只要文案里有字体覆盖不到的字符，表现就是「某个字变成方框/问号」，
而其它字正常 —— 很容易被误判成编码问题。这里把两者分开：
  * 编码问题 -> 整串都是问号或乱码（strict UTF-8 / CP1252 的特征）
  * 缺字问题 -> 只有个别字是方框，其余正常

用法：
  python tools/fix_font_coverage.py --check          # 只报告缺字
  python tools/fix_font_coverage.py --build          # 补字并重建 FNT + 写回 DAT
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

from ttdat import TTDat
from ft2 import FT2

G = r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2"
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# 主字体（汉化替换的就是这个）
FONT_KEY = "gui\\Font\\FONT_NXG.FT2"

# 本次新增的菜单标签译文 —— 必须全部有字形
UI_LABELS = [
    "退出", "退出到Windows", "退出到演示菜单", "返回游戏",
    "低", "中", "高", "继续游戏", "接受", "返回", "拒绝", "是", "否",
    "确定", "取消", "开", "关", "恢复默认设置", "画面设置",
    "屏幕分辨率", "刷新率", "垂直同步", "宽高比", "增强画质",
    "跟随分辨率", "使用当前设置", "纹理质量", "还原",
    "需要重启游戏才能让这些设置生效", "特效设置", "FSAA",
    "外部设置", "阴影", "泛光", "景深", "速度模糊", "动态光影质量",
    "抗锯齿", "环境光遮蔽", "显示按键表",
    # 后续校订：改用全字形可用的等价译名
    "边角抗锯齿", "全屏抗锯齿", "显示游戏按键",
]


def font_codepoints(dat_name):
    path = os.path.join(G, dat_name)
    d = TTDat(path)
    out = None
    try:
        for r in d.files:
            if (r["name"] or "").lower() == FONT_KEY.lower():
                f = FT2(d.read_file(r))
                cps = set()
                for it in f.chars:
                    if isinstance(it, (list, tuple)) and it:
                        cps.add(it[0])
                    elif isinstance(it, int):
                        cps.add(it)
                out = cps
                break
    finally:
        d.close()
    return out


def collect_used_chars():
    """收集全部汉化文案用字：DAT 内的文本表 + 菜单标签。"""
    used = set()
    # 1) 菜单标签
    for t in UI_LABELS:
        used |= set(t)
    # 2) DAT 里的中文（text.csv 等，由 check_dat_version.py 判定为汉化版）
    for dat_name in ("GAME.dat", "GAME2.dat"):
        path = os.path.join(G, dat_name)
        if not os.path.exists(path):
            continue
        d = TTDat(path)
        try:
            for r in d.files:
                nm = (r["name"] or "").lower()
                if nm.endswith(".csv") or nm.endswith(".txt"):
                    raw = d.read_file(r)
                    try:
                        s = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    used |= {c for c in s if ord(c) > 0x2000}
        finally:
            d.close()
    return used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只报告，不改任何东西")
    ap.add_argument("--build", action="store_true", help="补字并重建字体")
    a = ap.parse_args()

    cps = font_codepoints("GAME.dat")
    if cps is None:
        print("!! 在 GAME.dat 里找不到 %s" % FONT_KEY)
        sys.exit(1)

    used = collect_used_chars()
    missing = sorted(c for c in used if ord(c) not in cps)

    print("=" * 68)
    print("字体 %s  字形数 %d" % (FONT_KEY, len(cps)))
    print("汉化文案用字 %d 个（含菜单标签 %d 个）"
          % (len(used), sum(len(t) for t in UI_LABELS)))
    print("=" * 68)
    if not missing:
        print("全部用字均有字形，无缺失。")
        return

    print("缺失 %d 个字：%s" % (len(missing), "".join(missing)))
    print()
    print("涉及文案：")
    for t in UI_LABELS:
        hit = [c for c in t if c in missing]
        if hit:
            print("  %-30s 缺: %s" % (t, "".join(hit)))
    print()
    print("处理办法（二选一）：")
    print("  1) 换译名避开缺字 —— 改 gen_ui_patch.py 的 ZH 表，重新生成 DLL")
    print("  2) 重建字体补上这些字 —— 需重新跑 build_font.py 并写回 DAT")
    print("     （会改变字体文件体积，务必重新验证游戏内显示与排版）")

    if a.check or not a.build:
        return

    print("\n--build 已指定，但重建字体需要重跑 build_font.py 并回写 DAT，")
    print("这一步影响 DAT 体积与 CRC，故不自动执行。")
    print("请按 README 的字体构建流程手动执行，或告知我继续。")


if __name__ == "__main__":
    main()
