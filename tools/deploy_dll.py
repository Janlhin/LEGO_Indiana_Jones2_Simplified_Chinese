"""d3d9 代理 DLL 部署/卸载（存档代码页修复）。

作用：让游戏在中文系统区域(ACP=936)下也能正常存档，无需改系统区域为土耳其语。
用法:
  python deploy_dll.py --game "D:\\SteamLibrary\\steamapps\\common\\Lego Indiana Jones 2"    # 部署
  python deploy_dll.py --game "..." --remove                                                  # 卸载
"""
import os
import sys
import shutil

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '09_toolchain')


def deploy(game):
    d3d9_proxy = os.path.join(SRC_DIR, 'd3d9.dll')
    sys_d3d9 = r'C:\Windows\SysWOW64\d3d9.dll'
    dst_proxy = os.path.join(game, 'd3d9.dll')
    dst_orig = os.path.join(game, 'd3d9_orig.dll')

    if not os.path.exists(d3d9_proxy):
        print('找不到代理 d3d9.dll:', d3d9_proxy)
        return
    shutil.copy2(sys_d3d9, dst_orig)
    shutil.copy2(d3d9_proxy, dst_proxy)
    print('已部署:')
    print('  %s' % dst_proxy)
    print('  %s' % dst_orig)


def remove(game):
    for f in ['d3d9.dll', 'd3d9_orig.dll']:
        p = os.path.join(game, f)
        if os.path.exists(p):
            os.remove(p)
            print('已删除:', p)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('--remove', action='store_true')
    a = ap.parse_args()
    if a.remove:
        remove(a.game)
    else:
        deploy(a.game)
