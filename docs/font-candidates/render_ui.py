"""渲染游戏内 UI 场景模拟图：同一套菜单在四款字体下的观感。"""
import os
import random
import re
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
S = 2
PANEL_W, PANEL_H = 598, 430
GAP = 24
MARGIN = 40
HEAD = 92
W = MARGIN * 2 + PANEL_W * 2 + GAP
H = HEAD + PANEL_H * 4 + GAP * 3 + 46

FG = (255, 255, 255)
DIM = (168, 170, 176)
GOLD = (255, 207, 0)
YAHEI = "C:/Windows/Fonts/msyh.ttc"
YAHEIBD = "C:/Windows/Fonts/msyhbd.ttc"

CANDS = [
    ("微软雅黑  Microsoft YaHei", YAHEI, None, "现状·专有", 0),
    ("思源黑体  Noto Sans SC", os.path.join(HERE, "NotoSansSC.ttf"), [400], "OFL·同风格", 0),
    ("霞鹜文楷  LXGW WenKai", os.path.join(HERE, "LXGWWenKai-Regular.ttf"), None, "OFL·楷体", 0),
    ("方德楷体  FandolKai", os.path.join(HERE, "FandolKai-Regular.otf"), None, "GPL·楷体", 0),
    ("AR PL UKai  文鼎楷体（CN）", os.path.join(HERE, "ukai.ttc"), None, "APL·楷体", 0),
    ("AR PL KaitiM GB  文鼎楷体（GB）", os.path.join(HERE, "gkai00mp.ttf"), None, "APL·楷体", 0),
    ("思源宋体  Noto Serif SC", os.path.join(HERE, "NotoSerifSC.ttf"), [500], "OFL·宋体", 0),
]


def F(path, size, axes=None, index=0):
    f = ImageFont.truetype(path, size * S, index=index)
    if axes:
        f.set_variation_by_axes(axes)
    return f


def make_bg(w, h, seed):
    """模拟虚化的 3D 场景背景。"""
    rnd = random.Random(seed)
    small = Image.new("RGB", (w // 8, h // 8), (30, 24, 20))
    dd = ImageDraw.Draw(small)
    for _ in range(26):
        x, y = rnd.randrange(0, w // 8), rnd.randrange(0, h // 8)
        r = rnd.randrange(6, 30)
        c = rnd.choice([(96, 70, 38), (58, 52, 48), (120, 92, 52), (40, 46, 54)])
        dd.ellipse([x - r, y - r, x + r, y + r], fill=c)
    bg = small.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    # 压暗
    dark = Image.new("RGB", (w, h), (10, 9, 8))
    return Image.blend(bg, dark, 0.55)


MENU = ["继续游戏", "读取存档", "保存存档", "删除存档"]
SUB = "确定要覆盖这个存档吗？"
SUB2 = "该存档中的全部进度和建造关卡都将丢失。"


def panel(cand, seed):
    name, path, axes, tag, fidx = cand
    p = make_bg(PANEL_W * S, PANEL_H * S, seed)
    d = ImageDraw.Draw(p)

    # 外侧描边
    d.rectangle([0, 0, PANEL_W * S - 1, PANEL_H * S - 1], outline=(58, 58, 64), width=S)

    # 角落标签（用雅黑，避免干扰判断）
    d.text((16 * S, 12 * S), name, font=F(YAHEI, 12), fill=(190, 192, 198))
    tw = d.textlength(tag, font=F(YAHEI, 11))
    d.text((PANEL_W * S - 16 * S - tw, 13 * S), tag, font=F(YAHEI, 11), fill=(120, 124, 132))

    # 标题
    d.text((26 * S, 44 * S), "乐高印第安纳琼斯 2", font=F(path, 30, axes, fidx), fill=FG)
    d.text((28 * S, 90 * S), "冒险再续", font=F(path, 16, axes, fidx), fill=DIM)

    # 分隔线
    d.line([26 * S, 122 * S, (PANEL_W - 26) * S, 122 * S], fill=(70, 70, 76), width=S)

    # 菜单
    y = 140
    for i, item in enumerate(MENU):
        f = F(path, 21, axes, fidx)
        col = GOLD if i == 0 else (236, 238, 242)
        if i == 0:
            d.rectangle([24 * S, (y + 2) * S, 27 * S, (y + 26) * S], fill=GOLD)
        d.text((40 * S, y * S), item, font=f, fill=col)
        y += 38

    # 底部字幕条
    bar_y = PANEL_H - 84
    d.rectangle([0, bar_y * S, PANEL_W * S, PANEL_H * S], fill=(0, 0, 0))
    d.text((30 * S, (bar_y + 14) * S), SUB, font=F(path, 17, axes, fidx), fill=FG)
    d.text((30 * S, (bar_y + 42) * S), SUB2, font=F(path, 17, axes, fidx), fill=FG)
    return p


def make_note():
    """右下角说明卡（用雅黑渲染，不属于样本对比）。"""
    p = Image.new("RGB", (PANEL_W * S, PANEL_H * S), (26, 26, 31))
    d = ImageDraw.Draw(p)
    d.rectangle([0, 0, PANEL_W * S - 1, PANEL_H * S - 1], outline=(58, 58, 64), width=S)

    d.text((26 * S, 26 * S), "看图要点", font=F(YAHEIBD, 17), fill=(255, 207, 0))
    items = [
        ("笔画均匀度", "黑体（雅黑 / 思源黑体）笔画均匀，18–22 px 小字最稳；楷体和宋体笔画对比强，小字发虚。"),
        ("字面大小", "同字号下楷体字面明显更小。七款里 AR PL KaitiM GB 最细小，AR PL UKai 次之。"),
        ("文鼎两款", "UKai 是繁体字形规范（缺 ™），KaitiM GB 是简体字形（缺 ® ™ ©）；两者字形都比霞鹜文楷细一档。"),
        ("授权差异", "思源系与霞鹜文楷为 SIL OFL；方德为 GPLv3；文鼎两款为 Arphic Public License（copyleft 型）。"),
    ]
    y = 66
    for k, v in items:
        d.text((26 * S, y * S), "·", font=F(YAHEIBD, 14), fill=(255, 207, 0))
        d.text((40 * S, y * S), k, font=F(YAHEIBD, 13), fill=(236, 238, 242))
        # 自动折行（英文单词不拆开）
        f = F(YAHEI, 13)
        limit = (PANEL_W - 80) * S
        lines, line = [], ""
        for tok in re.findall(r"[A-Za-z0-9®]+|.", v):
            if d.textlength(line + tok, font=f) > limit and line:
                lines.append(line); line = tok
            else:
                line += tok
        lines.append(line)
        yy = y + 21
        for ln in lines:
            d.text((40 * S, yy * S), ln, font=f, fill=(168, 170, 176))
            yy += 20
        y = yy + 12
    return p


img = Image.new("RGB", (W * S, H * S), (16, 16, 20))
d = ImageDraw.Draw(img)
d.text((MARGIN * S, 30 * S), "同一套界面在七款字体下的观感", font=F(YAHEIBD, 22), fill=FG)
d.text((MARGIN * S, 64 * S), "模拟游戏内菜单与底部字幕；文案取自 translations/text.csv。灰字为面板说明，非游戏内容。",
       font=F(YAHEI, 13), fill=(140, 145, 155))

for idx, cand in enumerate(CANDS):
    p = panel(cand, 4000 + idx * 17)
    col, row = idx % 2, idx // 2
    x = MARGIN + col * (PANEL_W + GAP)
    y = HEAD + row * (PANEL_H + GAP)
    img.paste(p, (x * S, y * S))

img.paste(make_note(), ((MARGIN + PANEL_W + GAP) * S, (HEAD + 3 * (PANEL_H + GAP)) * S))

out = os.path.join(HERE, "font-demo-ui.png")
img.resize((W, H), Image.LANCZOS).save(out)
print("saved", out, W, H)
