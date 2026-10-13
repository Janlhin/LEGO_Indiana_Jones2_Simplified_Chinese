import hashlib
import winreg


def hp(p):
    m = hashlib.md5()
    f = open(p, 'rb')
    for c in iter(lambda: f.read(1 << 22), b''):
        m.update(c)
    return m.hexdigest()[:12]


G = r'D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2'
for f, t in [('GAME.dat', '08_ft2/GAME.dat'), ('GAME2.dat', '08_ft2/GAME2.dat')]:
    a, b = hp(G + '\\' + f), hp(t)
    print('%-10s 游戏内=%s 目标=%s 一致=%s' % (f, a, b, a == b))

k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'SOFTWARE\LucasArts\LEGOIndy2')
print('LanguageVal =', winreg.QueryValueEx(k, 'LanguageVal')[0])
