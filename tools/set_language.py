# -*- coding: utf-8 -*-
"""Write the language override registry value used by LEGO Indiana Jones 2.

The game keys its language off `LanguageVal` (a Windows LANGID DWORD) under
SOFTWARE\\LucasArts\\LEGOIndy2 (documented by PCGamingWiki). We set it to the
Japanese LANGID (0x0411 = 1041) because that is the game's only multi-byte text
path (japanese.txt + a CJK font), which we repurpose for Chinese.
"""
import winreg

LANGID_JP = 1041
SUBKEYS = [
    r'SOFTWARE\LucasArts\LEGOIndy2',
    r'SOFTWARE\LucasArts\LEGO® Indiana Jones™ 2',
]


def write(hive, hname):
    for sub in SUBKEYS:
        try:
            k = winreg.CreateKeyEx(hive, sub, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, 'LanguageVal', 0, winreg.REG_DWORD, LANGID_JP)
            winreg.CloseKey(k)
            print('  OK   %s\\%s  LanguageVal = %d (REG_DWORD)' % (hname, sub, LANGID_JP))
        except Exception as e:
            print('  FAIL %s\\%s  %s: %s' % (hname, sub, type(e).__name__, e))


print('写入 HKCU:')
write(winreg.HKEY_CURRENT_USER, 'HKCU')
print('写入 HKLM:')
write(winreg.HKEY_LOCAL_MACHINE, 'HKLM')


def read():
    for hive, hname in [(winreg.HKEY_CURRENT_USER, 'HKCU'),
                        (winreg.HKEY_LOCAL_MACHINE, 'HKLM')]:
        for sub in SUBKEYS:
            try:
                k = winreg.OpenKey(hive, sub)
                v = winreg.QueryValueEx(k, 'LanguageVal')
                winreg.CloseKey(k)
                print('  读取 %s\\%s = %r' % (hname, sub, v))
            except Exception:
                pass


print('\n回读确认:')
read()
