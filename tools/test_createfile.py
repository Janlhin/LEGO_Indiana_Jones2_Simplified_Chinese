# -*- coding: utf-8 -*-
"""验证 CreateDirectoryA/CreateFileA 在 GBK 下对 0xAE/0x99 的实际转换。"""
import ctypes
import os
import shutil

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

test_root = os.path.join(os.environ['TEMP'], 'indy2_codepage_test')
if os.path.isdir(test_root):
    shutil.rmtree(test_root)
os.makedirs(test_root)
# 父目录用 Unicode 正确创建（模拟 Steam 已建好的 LucasArts）
parent = os.path.join(test_root, 'LucasArts')
os.makedirs(parent)

ansi_name = b'LEGO\xae Indiana Jones\x99 2'
ansi_path = parent.encode('gbk', 'replace') + b'\\' + ansi_name
print('传给 CreateDirectoryA 的字节:', ansi_path.hex())

ok = k32.CreateDirectoryA(ansi_path, None)
err = ctypes.get_last_error()
print('CreateDirectoryA 返回:', bool(ok), ' 错误码=%d' % err)

print('LucasArts 下实际存在的目录:')
for name in os.listdir(parent):
    print('  [%r]' % name)
