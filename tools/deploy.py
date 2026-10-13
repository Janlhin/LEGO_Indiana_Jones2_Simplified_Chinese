"""Deploy / restore the LEGO Indiana Jones 2 Chinese patch.

  python deploy.py --game "D:\\...\\Lego Indiana Jones 2" --build <dir> --backup <dir>
  python deploy.py --restore --game ... --backup ...
"""
import argparse
import os
import shutil
import sys

FILES = ['GAME.dat', 'GAME2.dat', 'LEGOIndy2.exe']


def deploy(game, build, backup):
    os.makedirs(backup, exist_ok=True)
    for f in FILES:
        src = os.path.join(game, f)
        dst = os.path.join(backup, f)
        if not os.path.exists(dst):
            print('备份  %s  (%.1f MB)' % (f, os.path.getsize(src) / 1048576))
            shutil.copy2(src, dst)
        else:
            print('备份已存在，跳过  %s' % f)
    for f in FILES:
        src = os.path.join(build, f)
        dst = os.path.join(game, f)
        print('写入  %s  (%.1f MB)' % (f, os.path.getsize(src) / 1048576))
        shutil.copy2(src, dst)
    print('完成。如需还原: python deploy.py --restore --game "%s" --backup "%s"' % (game, backup))


def restore(game, backup, only=None):
    files = only or FILES
    for f in files:
        src = os.path.join(backup, f)
        dst = os.path.join(game, f)
        if not os.path.exists(src):
            print('!! 备份缺失: %s' % src)
            continue
        print('还原  %s' % f)
        shutil.copy2(src, dst)
    print('已还原为原始英文版。')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('--build', default=os.environ.get('BUILD_DIR') or
                    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build'))
    ap.add_argument('--backup', default=os.environ.get('BACKUP_DIR') or
                    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backup_chs'))
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--only', nargs='*', default=None,
                    help='只处理指定文件，如 --only LEGOIndy2.exe')
    a = ap.parse_args()
    if a.restore:
        restore(a.game, a.backup, a.only)
    else:
        deploy(a.game, a.build, a.backup)
