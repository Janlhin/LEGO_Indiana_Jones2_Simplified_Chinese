"""LEGO Indiana Jones 2 存档管理工具。

存档位置: %APPDATA%\\LucasArts\\LEGO® Indiana Jones™ 2\\SavedGames\\
存档文件名: SaveGame<N>.<语言名>_SavedGame  （语言名由 LanguageVal 决定）

用法:
  python saves.py list                 列出存档
  python saves.py backup               备份全部存档到 work/saves_backup/<时间戳>
  python saves.py rename <from> <to>   把语言后缀 from 改成 to（如 english japanese）
"""
import os
import sys
import shutil
import time

SAVE_DIR = os.path.join(os.environ['APPDATA'], 'LucasArts',
                        'LEGO® Indiana Jones™ 2', 'SavedGames')
BAK_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                        'saves_backup')


def list_saves():
    if not os.path.isdir(SAVE_DIR):
        print('存档目录不存在:', SAVE_DIR)
        return
    print('存档目录:', SAVE_DIR)
    files = sorted(os.listdir(SAVE_DIR))
    if not files:
        print('  (空)')
    for f in files:
        p = os.path.join(SAVE_DIR, f)
        print('  %-50s %8d 字节  %s' % (f, os.path.getsize(p),
                                        time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p)))))


def backup():
    if not os.path.isdir(SAVE_DIR):
        print('存档目录不存在')
        return
    dst = os.path.join(BAK_ROOT, time.strftime('%Y%m%d_%H%M%S'))
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in os.listdir(SAVE_DIR):
        shutil.copy2(os.path.join(SAVE_DIR, f), os.path.join(dst, f))
        n += 1
    print('已备份 %d 个文件 -> %s' % (n, dst))


def rename_lang(src, dst):
    if not os.path.isdir(SAVE_DIR):
        print('存档目录不存在')
        return
    n = 0
    for f in os.listdir(SAVE_DIR):
        if ('.%s_' % src) in f:
            nf = f.replace('.%s_' % src, '.%s_' % dst)
            os.rename(os.path.join(SAVE_DIR, f), os.path.join(SAVE_DIR, nf))
            print('%s -> %s' % (f, nf))
            n += 1
    print('共重命名 %d 个存档 (%s -> %s)' % (n, src, dst))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
    if cmd == 'list':
        list_saves()
    elif cmd == 'backup':
        backup()
    elif cmd == 'rename':
        rename_lang(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
