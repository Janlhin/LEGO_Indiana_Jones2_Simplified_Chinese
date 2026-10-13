# -*- coding: utf-8 -*-
"""全量核对：找出游戏里仍然显示英文的文本来源。"""
import sys, os, csv, io
sys.path.insert(0, r'C:\Users\Janlhin\WorkBuddy\2026-09-30-22-09-12\work\tools')
from ttdat import TTDat

G = r'D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2'
def has_cjk(s):
    return any(0x4E00 <= ord(c) <= 0x9FFF for c in s)

d = TTDat(os.path.join(G, 'GAME2.dat'))

# 1. 列出 GAME2.dat 里所有文本类文件
print('=== GAME2.dat 中 stuff\\text 下所有文件 ===')
for r in d.files:
    nm = r['name'] or ''
    if 'text' in nm.lower() and (nm.lower().endswith('.txt') or nm.lower().endswith('.csv')):
        print('  %-40s %d 字节' % (nm, r['size']))

# 2. english.txt 核对
print('\n=== english.txt 中仍为英文的行 ===')
en = d.read_file(d.by_name('stuff\\text\\english.txt')[0]).decode('utf-8-sig')
en_lines = en.splitlines()
en_eng = []
for ln in en_lines:
    ln = ln.strip()
    if not ln or ln.startswith(';'):
        continue
    # 格式: ID "文本"  或  ID 文本
    # 提取引号内或 tab 后文本
    if not has_cjk(ln):
        en_eng.append(ln)
print('english.txt 总行数(非空非注释):', sum(1 for l in en_lines if l.strip() and not l.strip().startswith(';')))
print('仍为英文的行数:', len(en_eng))
for l in en_eng[:60]:
    print('  ', l[:80])

# 3. american.txt
print('\n=== american.txt 仍为英文的行 ===')
try:
    am = d.read_file(d.by_name('stuff\\text\\american.txt')[0]).decode('utf-8-sig')
    for l in am.splitlines():
        if l.strip() and not l.strip().startswith(';') and not has_cjk(l):
            print('  ', l[:80])
except Exception as e:
    print('读取失败', e)

# 4. text.csv 按平台核对 ENGLISH 列
print('\n=== text.csv ENGLISH 列仍为英文(按平台统计) ===')
rows = list(csv.reader(io.StringIO(d.read_file(d.by_name('stuff\\text\\text.csv')[0]).decode('utf-8-sig'))))
i = {n: k for k, n in enumerate(rows[0])}
from collections import Counter
plat_counter = Counter()
samples = []
for r in rows[1:]:
    if not r or len(r) <= i['ENGLISH']:
        continue
    lab = r[i['LABEL']]
    en = r[i['ENGLISH']]
    pf = r[i['PLATFORM']].strip()
    if not en or not lab:
        continue
    if not has_cjk(en):
        plat_counter[pf] += 1
        if pf == 'All' and len(samples) < 40:
            samples.append((lab, en))
print('仍为英文的行数(按平台):', dict(plat_counter))
print('\nAll 平台(PC 会显示)仍为英文的样本:')
for lab, en in samples:
    print('  %-32s %s' % (lab, en[:50]))

d.close()
