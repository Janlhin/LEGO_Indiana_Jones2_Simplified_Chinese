# -*- coding: utf-8 -*-
"""检测当前系统 ACP 与汉化部署状态。"""
import os
import ctypes
import hashlib
import winreg

def h(p):
    m = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''):
            m.update(c)
    return m.hexdigest()[:12]

G = r'D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2'
BUILD = r'C:\Users\Janlhin\WorkBuddy\2026-09-30-22-09-12\work\08_ft2'

# 1. ACP
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
acp = k32.GetACP()
oem = k32.GetOEMCP()
names = {936: '简体中文 GBK', 1254: '土耳其语', 1252: '西欧', 65001: 'UTF-8'}
print('ACP   = %d  (%s)' % (acp, names.get(acp, '其他')))
print('OEMCP = %d' % oem)

# 2. 注册表 LanguageVal
print('\n--- 注册表 LanguageVal ---')
for sub in [r'SOFTWARE\LucasArts\LEGOIndy2']:
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub)
        v = winreg.QueryValueEx(k, 'LanguageVal')[0]
        winreg.CloseKey(k)
        tag = {1033: '英文槽位(读中文内容)', 1041: '日语槽位', 936: '中文'}.get(v, '未知')
        print('HKCU\\%s\\LanguageVal = %d  (%s)' % (sub, v, tag))
    except Exception as e:
        print('HKCU\\%s 未找到: %s' % (sub, e))

# 3. 游戏目录部署状态
print('\n--- 游戏目录文件 ---')
for f in ['GAME.dat', 'GAME2.dat', 'GAME0.dat', 'GAME1.dat', 'd3d9.dll', 'd3d9_orig.dll']:
    p = os.path.join(G, f)
    if os.path.exists(p):
        print('  %-14s %10d 字节' % (f, os.path.getsize(p)))
    else:
        print('  %-14s 缺失' % f)

# 4. MD5 一致性
print('\n--- 与构建产物一致性 ---')
for f in ['GAME.dat', 'GAME2.dat']:
    gp = os.path.join(G, f)
    bp = os.path.join(BUILD, f)
    if os.path.exists(gp) and os.path.exists(bp):
        print('  %-10s 游戏=%s 构建=%s 一致=%s' % (f, h(gp), h(bp), h(gp) == h(bp)))

# 5. DLL 一致性
sysd3d9 = r'C:\Windows\SysWOW64\d3d9.dll'
if os.path.exists(os.path.join(G, 'd3d9_orig.dll')) and os.path.exists(sysd3d9):
    print('  d3d9_orig 与系统一致=%s' % (h(os.path.join(G, 'd3d9_orig.dll')) == h(sysd3d9)))

# 6. 游戏内 text.csv 是否含中文
print('\n--- 游戏内中文内容 ---')
import sys
sys.path.insert(0, r'C:\Users\Janlhin\WorkBuddy\2026-09-30-22-09-12\work\tools')
from ttdat import TTDat
import csv, io
d = TTDat(os.path.join(G, 'GAME2.dat'))
en = d.read_file(d.by_name('stuff\\text\\english.txt')[0]).decode('utf-8-sig')
print('  english.txt 含汉字:', any(0x4E00 <= ord(c) <= 0x9FFF for c in en))
rows = list(csv.reader(io.StringIO(d.read_file(d.by_name('stuff\\text\\text.csv')[0]).decode('utf-8-sig'))))
i = {n: k for k, n in enumerate(rows[0])}
zh = sum(1 for r in rows[1:] if r and any(0x4E00 <= ord(c) <= 0x9FFF for c in r[i['ENGLISH']]))
print('  text.csv ENGLISH 列含中文行数:', zh)
fnt = d.by_name('stuff\\text\\FONT2_NXG.FT2')
if fnt:
    print('  FONT2_NXG.FT2:', fnt[0]['size'], '字节')
d.close()
print('\n结论：')
print('  - 系统区域 =', '土耳其语(改过)' if acp == 1254 else ('中文GBK(原始)' if acp == 936 else '其他'))
print('  - DLL 存档修复 =', '已就位' if os.path.exists(os.path.join(G, 'd3d9.dll')) and os.path.exists(os.path.join(G, 'd3d9_orig.dll')) else '未就位')
