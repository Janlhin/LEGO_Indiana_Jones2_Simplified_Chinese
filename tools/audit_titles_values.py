# -*- coding: utf-8 -*-
import sys, os, csv, io, re
sys.path.insert(0, 'tools')
from ttdat import TTDat

G = r'D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2'

# 1. text.csv 里所有含 Settings/Video/Effects 的 label
d = TTDat(os.path.join(G, 'GAME2.dat'))
raw = d.read_file(d.by_name('stuff' + chr(92) + 'text' + chr(92) + 'text.csv')[0]).decode('utf-8-sig')
rows = list(csv.reader(io.StringIO(raw)))
i = {n: k for k, n in enumerate(rows[0])}
print('=== text.csv 里含 Settings/Video/Effects/Title 的 label ===')
for r in rows[1:]:
    if not r:
        continue
    lab = r[i['LABEL']]
    if any(k in lab.lower() for k in ['settings', 'video', 'effects', 'title', 'graphic']):
        print('  %-30r EN=%r CH=%r' % (lab, r[i['ENGLISH']][:24], r[i['CHINESE']][:16]))
d.close()

# 2. exe 里 "Video Settings" / "Effects Settings" 上下文
raw_exe = open(os.path.join(G, 'LEGOIndy2.exe'), 'rb').read()
print()
print('=== exe 里的标题字符串 ===')
for t in ['Video Settings', 'Effects Settings', 'Graphics Settings']:
    off = raw_exe.find(t.encode())
    if off >= 0:
        # 前 40 字节
        ctx = raw_exe[max(0, off-40):off+40]
        strs = [s.decode('latin-1') for s in ctx.split(b'\x00') if len(s) >= 1]
        print('  %r @ %#x  上下文: %s' % (t, off, strs))
    else:
        print('  %r 未找到' % t)

# 3. 值文本 On/Off/Low/High 的编码和位置
print()
print('=== exe 里的值文本（On/Off/Low/Medium/High）===')
for t in ['Off', 'On', 'Low', 'Medium', 'High', 'No Shadow', 'Externally Set']:
    # ASCII
    for m in re.finditer(rb'(?<=[\x00])' + re.escape(t.encode()) + rb'(?=[\x00])', raw_exe):
        pass
    cnt_ascii = len(re.findall(rb'(?<=[\x00])' + re.escape(t.encode()) + rb'(?=[\x00])', raw_exe))
    # UTF-16LE
    u16 = t.encode('utf-16-le')
    cnt_u16 = raw_exe.count(u16)
    print('  %-16r ASCII独立=%d  UTF-16LE=%d' % (t, cnt_ascii, cnt_u16))
