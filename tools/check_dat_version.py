# -*- coding: utf-8 -*-
"""判断游戏目录里的 DAT 是原版还是汉化版。

背景：发现补丁包里的 GAME.dat / GAME2.dat 与已安装到游戏目录的
体积不同（GAME.dat 差 5.37 MB，GAME2.dat 差 19.28 MB），导致
Test-FileMatch 判 False —— 但用户游戏里确实是中文在跑。

所以问题不是"已安装的不是汉化版"，而是"补丁包里的 DAT 与当初
部署到游戏目录的那份不是同一个产物"。必须查清楚，否则用户
重跑安装脚本会白拷 2 GB，或者更糟：把游戏里那份能跑的覆盖成
另一个版本。

判据：汉化版 DAT 里有大量中文字符，原版没有。
扫UTF-8 三字节序列（汉化时文本就是按 UTF-8 写进去的）。
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

GAME = r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2"
PATCH = (r"C:\Users\Janlhin\WorkBuddy\2026-09-30-22-09-12\work"
         r"\dist\LEGO_Indiana_Jones_2_CHS_v1.0\data")

# CJK 统一表意文字：基本汉字 + 扩展 A + 兼容汉字
#
# 这里踩过一个坑：不能把码点字符类直接 .encode() 后交给 bytes 正则。
# "[一-鿿]" 编码成字节是 [ E4 B8 80 - E9 BF BF ]，而字节正则里的
# "-" 是按**字节值**解释范围的，于是 E4..BF 之间几乎任意字节都命中 ——
# 实测 10亿 字节里报出 4 亿个"汉字"，完全是假阳性。
# 正确做法：用码点正则匹配已解码的字符串。
CJK_RE = re.compile("[一-鿿㐀-䶿豈-﫿]")


def count_cjk(path, label):
    """统计文件里 CJK 字符个数，分块读以免占用大内存。"""
    n = 0
    total = 0
    with open(path, "rb") as f:
        tail = b""
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            buf = tail + chunk
            total += len(chunk)
            try:
                text = buf.decode("utf-8", errors="ignore")
            except Exception:
                continue
            n += len(CJK_RE.findall(text))
            # UTF-8 汉字最长 4 字节，留 3 字节尾巴防止跨块截断
            tail = buf[-3:]
    print("  %-24s %10d B   CJK %d 个" % (label, total, n))
    return n


print("=" * 64)
print("DAT 版本判定：原版 vs 汉化版")
print("=" * 64)

for name in ("GAME.dat", "GAME2.dat"):
    print("\n%s" % name)
    a = os.path.join(PATCH, name)
    b = os.path.join(GAME, name)
    if not os.path.exists(b):
        print("  游戏目录里没有 %s，跳过" % name)
        continue

    na = count_cjk(a, "补丁包")
    print("  %-24s %10d B   (差 %+.2f MB)" % (
        "体积差", os.path.getsize(b) - os.path.getsize(a),
        (os.path.getsize(b) - os.path.getsize(a)) / 1048576))
    nb = count_cjk(b, "游戏目录(已装)")

    va = "汉化版" if na > 1000 else "无中文(原版?)"
    vb = "汉化版" if nb > 1000 else "无中文(原版?)"
    print("  => 补丁包: %s   游戏目录: %s" % (va, vb))