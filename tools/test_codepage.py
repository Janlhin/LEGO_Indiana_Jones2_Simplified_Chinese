# -*- coding: utf-8 -*-
"""验证 exe 里 ANSI 目录名在不同代码页下的解码结果。"""
import ctypes

raw = b'LEGO\xae Indiana Jones\x99 2'  # exe 0x8934e8 处硬编码的目录名

print('exe 原始字节:', raw.hex())

# 1) GBK（中文系统 ANSI 代码页）解码
for cp in ['gbk', 'cp1252', 'cp1254', 'latin-1']:
    try:
        s = raw.decode(cp)
        print('  %-8s -> %r' % (cp, s))
    except Exception as e:
        print('  %-8s -> 解码失败 %r' % (cp, e))

# 2) 用 Windows API 模拟 ANSI -> Unicode (GBK 代码页 = 936)
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
for cpid, name in [(936, 'GBK'), (1254, 'Turkish'), (1252, 'CP1252')]:
    n = k32.MultiByteToWideChar(cpid, 0, raw, len(raw), None, 0)
    buf = ctypes.create_unicode_buffer(n)
    k32.MultiByteToWideChar(cpid, 0, raw, len(raw), buf, n)
    print('  Windows CP%-5d(%s) -> %r' % (cpid, name, buf.value))
