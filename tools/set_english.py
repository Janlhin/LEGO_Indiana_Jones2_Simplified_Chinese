# -*- coding: utf-8 -*-
"""把语言槽位从日语(1041)改回英文(1033)：注册表 + pcconfig.txt。"""
import winreg
import os

EN = 1033  # 英文(美国)

keys = [
    (winreg.HKEY_CURRENT_USER, r'SOFTWARE\LucasArts\LEGOIndy2'),
    (winreg.HKEY_CURRENT_USER, r'SOFTWARE\LucasArts\LEGO\u00ae Indiana Jones\u2122 2'),
]

for hive, sub in keys:
    try:
        k = winreg.OpenKey(hive, sub, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, 'LanguageVal', 0, winreg.REG_DWORD, EN)
        winreg.CloseKey(k)
        print('已设置 %s\\LanguageVal = %d (英文)' % (sub, EN))
    except Exception as e:
        print('跳过 %s: %s' % (sub, e))

# pcconfig.txt
p = os.path.join(os.environ['APPDATA'], 'LucasArts',
                 'LEGO\u00ae Indiana Jones\u2122 2', 'pcconfig.txt')
if os.path.exists(p):
    txt = open(p, encoding='utf-8').read()
    txt = txt.replace('LanguageVal 1041', 'LanguageVal 1033')
    open(p, 'w', encoding='utf-8').write(txt)
    print('pcconfig.txt LanguageVal 已改为 1033')
else:
    print('pcconfig.txt 不存在')
