"""渲染中文字体候选对比图（模拟游戏 UI 深底白字环境）。"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
S = 2  # 2x 超采样

W, H = 1240, 2406
BG = (16, 16, 20)
CARD = (23, 25, 30)
FG = (255, 255, 255)
DIM = (140, 145, 155)
ACCENT = (255, 207, 0)
YAHEI = "C:/Windows/Fonts/msyh.ttc"
YAHEIBD = "C:/Windows/Fonts/msyhbd.ttc"


def font(path, size, axes=None, index=0):
    f = ImageFont.truetype(path, size * S, index=index)
    if axes:
        try:
            f.set_variation_by_axes(axes)
        except Exception as e:
            print("variation fail", path, e)
    return f


CANDS = [
    {
        "name": "微软雅黑  Microsoft YaHei",
        "note": "当前构建所用 · 专有字体，字形位图随包分发有授权风险",
        "path": YAHEI, "axes": None, "index": 0, "tag": "现状",
    },
    {
        "name": "思源黑体  Noto Sans SC",
        "note": "SIL OFL 1.1 · 黑体，与雅黑同风格 · 字重 400 · 最稳的替换",
        "path": os.path.join(HERE, "NotoSansSC.ttf"), "axes": [400], "index": 0, "tag": "同风格",
    },
    {
        "name": "霞鹜文楷  LXGW WenKai",
        "note": "SIL OFL 1.1 · 楷体手写风 · 19 MB · 36498 字形 · 缺 ® 之外的拉丁扩展 0 个",
        "path": os.path.join(HERE, "LXGWWenKai-Regular.ttf"), "axes": None, "index": 0, "tag": "换风格",
    },
    {
        "name": "方德楷体  FandolKai",
        "note": "GPLv3 · 楷体 · 7.6 MB · 缺 65 字，含 ®",
        "path": os.path.join(HERE, "FandolKai-Regular.otf"), "axes": None, "index": 0, "tag": "换风格",
    },
    {
        "name": "AR PL UKai  文鼎楷体（CN 切版）",
        "note": "Arphic Public License · 繁体字形规范 · 17 MB · 缺 ™",
        "path": os.path.join(HERE, "ukai.ttc"), "axes": None, "index": 0, "tag": "换风格",
    },
    {
        "name": "AR PL KaitiM GB  文鼎楷体（GB 切版）",
        "note": "Arphic Public License · 简体字形 · 4.5 MB · 缺 ® ™ © 三个符号",
        "path": os.path.join(HERE, "gkai00mp.ttf"), "axes": None, "index": 0, "tag": "换风格",
    },
    {
        "name": "思源宋体  Noto Serif SC",
        "note": "SIL OFL 1.1 · 宋体衬线 · 字重 500（默认实例是极细，须显式指定）",
        "path": os.path.join(HERE, "NotoSerifSC.ttf"), "axes": [500], "index": 0, "tag": "换风格",
    },
]

LINES = [
    ("乐高印第安纳琼斯 2", 44),
    ("继续　读取存档　保存存档　删除存档", 30),
    ("正在保存游戏…　读取失败　空间不足　迷你套装　按 START 键", 22),
    ("LEGO® Indiana Jones™ 2", 26),          # 商标符号缺字检验行
    ("提示：迷你套装 3/10 已收集　得分 128,400　继续探索才能解锁隐藏关卡", 18),
]

img = Image.new("RGB", (W * S, H * S), BG)
d = ImageDraw.Draw(img)

d.text((40 * S, 34 * S), "LEGO 印第安纳琼斯 2 · 中文字体候选对比", font=font(YAHEIBD, 22), fill=FG)
d.text((40 * S, 68 * S),
       "深底白字，字号 44 / 30 / 22 / 26 / 18；第四行为商标符号缺字检验。GDI 栅格化，非矢量缩放。",
       font=font(YAHEI, 14), fill=DIM)

y = 108
for c in CANDS:
    top = y * S
    bh = 300 * S
    d.rounded_rectangle([40 * S, top, (W - 40) * S, top + bh], radius=10 * S, fill=CARD)
    d.rectangle([40 * S, top + 1, 44 * S, top + bh - 1], fill=ACCENT)

    d.text((62 * S, (y + 14) * S), c["name"], font=font(YAHEIBD, 15), fill=FG)
    d.text((62 * S, (y + 38) * S), c["note"], font=font(YAHEI, 13), fill=DIM)

    tagf = font(YAHEI, 11)
    tw = d.textlength(c["tag"], font=tagf)
    d.text(((W - 62) * S - tw, (y + 16) * S), c["tag"], font=tagf, fill=(110, 114, 122))

    ty = y + 68
    for text, size in LINES:
        d.text((62 * S, ty * S), text, font=font(c["path"], size, c["axes"], c["index"]), fill=FG)
        ty += int(size * 1.52)

    y += 322

d.text((40 * S, (y + 6) * S),
       "样本取自 translations/text.csv 的真实界面文案。可变字体已按标注字重实例化。缺字显示为空白或方框。",
       font=font(YAHEI, 12), fill=(100, 104, 112))

out = os.path.join(HERE, "font-demo.png")
img.resize((W, H), Image.LANCZOS).save(out)
print("saved", out, W, H)
