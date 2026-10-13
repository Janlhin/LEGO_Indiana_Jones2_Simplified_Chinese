# -*- coding: utf-8 -*-
"""分析原版 FT2 的 posTable.w 语义：advance 到底是什么"""
import sys, struct
sys.path.insert(0, 'tools')
from ft2 import FT2

BE = '>'
f = FT2('07_ref/orig_FONT_NXG.FT2')
print('原版 FONT_NXG: height=%g baseline=%g spaceWidth=%g numChars=%d'
      % (f.height, f.baseline, f.space_width if hasattr(f, 'space_width') else -1, f.num_chars))

# 建 codepoint -> pos 的映射
cp2pos = {}
for cp, ix in f.chars:
    if cp != 0xFFFF and ix < len(f.positions):
        cp2pos[cp] = f.positions[ix]

# 1) 空格 0x20 的 w vs spaceWidth 字段
sp = cp2pos.get(0x20)
print('space(0x20): pos=%r  spaceWidth字段=%.1f' % (sp, f.space_width))

# 2) 典型字母的 w
for ch in 'WMlilLoO':
    p = cp2pos.get(ord(ch))
    print('  %r -> %r' % (ch, p))

# 3) w 的分布
ws = [p[2] for p in f.positions[1:]]
import statistics
print('w 分布: min=%.1f max=%.1f mean=%.1f median=%.1f'
      % (min(ws), max(ws), statistics.mean(ws), statistics.median(ws)))

# 4) 关键问题：小写 i/l 的 w 是否明显小于大写 W？（验证 per-char advance）
wi = cp2pos.get(ord('i')); wW = cp2pos.get(ord('W'))
print('i 的 w=%.1f, W 的 w=%.1f  (比值 %.2f —— 接近真实字宽比则 w=advance)'
      % (wi[2], wW[2], wi[2]/wW[2]))

# 5) 字形墨迹宽度 vs posTable.w：从 DDS 投影测量几个字形
import bc3
raw = open('07_ref/orig_FONT_NXG.FT2','rb').read()
d = raw.find(b'DDS ')
tw = struct.unpack_from('<I', raw, d+16)[0]
th = struct.unpack_from('<I', raw, d+12)[0]
rgba = bc3.decode_bc3(raw, d+128, tw, th)
def ink_width(pos):
    x, y, w = int(pos[0]), int(pos[1]), int(round(pos[2]))
    maxdx = 0
    for dy in range(0, int(f.height)):
        for dx in range(w-1, -1, -1):
            px = ((y+dy)*tw + (x+dx))*4
            if px+3 < len(rgba) and rgba[px+3] > 40:
                maxdx = max(maxdx, dx)
                break
    return maxdx + 1
print()
print('字形墨迹宽度 vs posTable.w:')
for ch in 'WMilO ':
    p = cp2pos.get(ord(ch))
    if p:
        print('  %r pos.w=%.1f  墨迹宽=%d' % (ch, p[2], ink_width(p)))
