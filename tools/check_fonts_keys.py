# -*- coding: utf-8 -*-
"""综合检查：字体槽位覆盖、键名来源、补丁状态"""
import sys, os, csv, io
sys.path.insert(0, 'tools')
from ttdat import TTDat
from ft2 import FT2

G = r'D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2'

print('=== 1. 两个 DAT 里全部字体/网格文件及替换状态 ===')
for dat in ['GAME.dat', 'GAME2.dat']:
    d = TTDat(os.path.join(G, dat))
    new_names = {'gui\\Font\\FONT_NXG.FT2', 'gui\\Font\\font_pc.fnt', 'gui\\Font\\font.txt'}
    for r in d.files:
        nm = r['name'] or ''
        low = nm.lower()
        if low.endswith(('.ft2', '.fnt')) or ('font' in low and low.endswith('.txt')):
            data = d.read_file(r)
            replaced = '替换过' if nm in new_names else '** 未替换 **'
            info = ''
            if low.endswith('.ft2'):
                try:
                    f = FT2(data)
                    info = 'height=%g baseline=%g n=%d' % (f.height, f.baseline, f.num_chars)
                except Exception as e:
                    info = '解析失败: %s' % e
            print('  [%s] %-44s %9d  %s  %s' % (dat, nm, r['size'], replaced, info))
    d.close()

print()
print('=== 2. text.csv 里是否有键名类 label ===')
d = TTDat(os.path.join(G, 'GAME2.dat'))
raw = d.read_file(d.by_name('stuff\\text\\text.csv')[0]).decode('utf-8-sig')
rows = list(csv.reader(io.StringIO(raw)))
i = {n: k for k, n in enumerate(rows[0])}
keys = {'Left', 'Right', 'Up', 'Down', 'Space', 'Enter', 'Insert', 'Tab', 'Escape'}
hits = 0
for r in rows[1:]:
    if not r:
        continue
    lab = r[i['LABEL']]
    en = r[i['ENGLISH']]
    if lab in keys or en in keys:
        print('  LABEL=%-24r EN=%r ZH=%r PF=%s' % (lab, en, r[i['CHINESE']][:12], r[i['PLATFORM']].strip()))
        hits += 1
print('  精确命中: %d' % hits)
d.close()

print()
print('=== 3. 当前 d3d9.dll 补丁状态 ===')
src = open('09_toolchain/d3d9proxy.c', encoding='utf-8').read()
import re
active = re.findall(r'^\s*\{(0x[0-9a-fA-F]+),', src, re.M)
print('  当前源码活动补丁条数: %d' % len(active))
raw_dll = open(os.path.join(G, 'd3d9.dll'), 'rb').read()
print('  游戏 d3d9.dll 含中文字节(数0):', '数0'.encode('utf-8') in raw_dll)
