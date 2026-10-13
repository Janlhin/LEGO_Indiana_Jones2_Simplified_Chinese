# -*- coding: utf-8 -*-
import sys, os, csv, io
sys.path.insert(0, 'tools')
from ttdat import TTDat

G = r'D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2'
d = TTDat(os.path.join(G, 'GAME2.dat'))
raw = d.read_file(d.by_name('stuff' + chr(92) + 'text' + chr(92) + 'text.csv')[0]).decode('utf-8-sig')
rows = list(csv.reader(io.StringIO(raw)))
i = {n: k for k, n in enumerate(rows[0])}
labs = ['MUSIC', 'AUDIO_VOLUME', 'SCREEN_BRIGHTNESS', 'VSync', 'FE_BLUR',
        'PC_CONTROL_CONFIG', 'PC_SETTINGS_VIDEO', 'PC_SETTINGS_EFFECTS']
print('=== OPTIONSMENU 8个label 翻译状态 ===')
for lab in labs:
    hit = [r for r in rows[1:] if r and r[i['LABEL']] == lab]
    if hit:
        r = hit[0]
        print('  %-22r EN=%r CH=%r PF=%s' % (lab, r[i['ENGLISH']][:24], r[i['CHINESE']][:16], r[i['PLATFORM']].strip()))
    else:
        print('  %-22r <<< 缺失' % lab)
d.close()
