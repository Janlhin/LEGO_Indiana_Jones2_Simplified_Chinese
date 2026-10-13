# -*- coding: utf-8 -*-
"""精确对照 视频/图形设置 .GIP 引用的 label 与 text.csv（大小写敏感）"""
import sys, os, re, csv, io
sys.path.insert(0, 'tools')
from ttdat import TTDat

G = r'D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2'

# 1. 提取两个 GIP 的 label
d = TTDat(os.path.join(G, 'GAME.dat'))
labels = {}
for r in d.files:
    nm = r['name'] or ''
    if nm.upper().endswith(('VIDEOSETTINGS.GIP', 'EFFECTSSETTINGS.GIP')):
        txt = d.read_file(r).decode('latin-1')
        for l in re.findall(r'String\s+"([^"]+)"', txt):
            labels.setdefault(l, set()).add(nm.split(chr(92))[-1])
d.close()

# 2. text.csv
d = TTDat(os.path.join(G, 'GAME2.dat'))
raw = d.read_file(d.by_name('stuff' + chr(92) + 'text' + chr(92) + 'text.csv')[0]).decode('utf-8-sig')
rows = list(csv.reader(io.StringIO(raw)))
i = {n: k for k, n in enumerate(rows[0])}
# LABEL 精确映射 + 忽略大小写映射
l2r = {r[i['LABEL']]: r for r in rows[1:] if r}
l2r_lower = {}
for r in rows[1:]:
    if r:
        l2r_lower.setdefault(r[i['LABEL']].lower(), r)
d.close()

def has_cjk(s):
    return any('\u4e00' <= c <= '\u9fff' for c in s)

print('=== 精确对照（大小写敏感）===')
need_fix = []
for lab in sorted(labels):
    where = '/'.join(labels[lab])
    if lab in l2r:
        r = l2r[lab]
        en = r[i['ENGLISH']]
        zh = r[i['CHINESE']]
        ok = has_cjk(en)  # 英文槽位(实际显示的)是否已中文
        mark = 'OK' if ok else '<<< 英文槽位未译'
        if not ok:
            need_fix.append((lab, en, zh, where))
        print('  [精确] %-18r EN=%r ZH=%r %s  [%s]' % (lab, en[:20], zh[:12], mark, where))
    else:
        # 找忽略大小写的
        lower = lab.lower()
        if lower in l2r_lower:
            r = l2r_lower[lower]
            en = r[i['ENGLISH']]
            ok = has_cjk(en)
            mark = 'OK' if ok else '<<< 未译'
            print('  [大小写不同] %-18r 实际LABEL=%-18r EN=%r %s' % (lab, r[i['LABEL']], en[:20], mark))
            if not ok:
                need_fix.append((lab, en, r[i['CHINESE']], where))
        else:
            print('  [缺失] %-18r  text.csv 里完全没有  [%s]' % (lab, where))
            need_fix.append((lab, '', '', where))

print()
print('需处理 label 数: %d' % len(need_fix))
