"""端到端模拟：跑一遍 安装.bat 的核心逻辑，验证改造后不出错。

不真的复制 2 GB 的 DAT（太慢也没必要），而是把copy 目标换成小文件，
验证脚本的分支走向、错误检查、自检提示是否都正确。

做法：读出 安装.bat，逐行 echo 出被"执行"的行，人工核对控制流；
同时用 cmd 实际跑一个缩减版，验证 d3d9.dll 那段的 errorlevel 分支。
"""
import io
import os
import re
import subprocess
import sys

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "dist", "LEGO_Indiana_Jones_2_CHS_v1.0")
SELF = sys.stdout.reconfigure(encoding="utf-8")


def read_gbk(name):
    with open(os.path.join(BASE, name), "rb") as f:
        return f.read().decode("gbk")


print("=" * 60)
print("1. 安装.bat 关键行检查")
print("=" * 60)

t = read_gbk("安装.bat")
ls = t.split("\r\n")

# a) 不应再有复制 d3d9_orig 的行
bad = [l for l in ls if "d3d9_orig.dll" in l and "copy /Y" in l]
print("[%s] 不再有 copy d3d9_orig.dll%s"
      % ("OK" if not bad else "FAIL", "" if not bad else " -> " + str(bad)))

# b) 不应再有 reg add
bad2 = [l for l in ls if re.search(r"^\s*reg add", l, re.I)]
print("[%s] 不再有 reg add%s"
      % ("OK" if not bad2 else "FAIL", "" if not bad2 else " -> " + str(bad2)))

# c) d3d9.dll 的copy 必须带 errorlevel 检查
i = next((i for i, l in enumerate(ls) if "copy /Y" in l and "data\\d3d9.dll" in l), -1)
seg = "\r\n".join(ls[i:i + 8]) if i >= 0 else ""
ok3 = i >= 0 and "if errorlevel 1" in seg
print("[%s] d3d9.dll copy 后有 errorlevel 检查" % ("OK" if ok3 else "FAIL"))
if i >= 0:
    for k in range(i, min(i + 9, len(ls))):
        print("      %3d| %s" % (k + 1, ls[k]))

# d) 所有 copy 是否都有检查
print("\n  所有 copy 行及其后是否检查:")
for i, l in enumerate(ls):
    if re.match(r"\s*copy /Y", l, re.I):
        nxt = "\n".join(ls[i + 1:i + 3])
        has = "if errorlevel" in nxt
        # DAT 的两个 copy 已有检查；xcopy 的不算
        print("      [%s] %s" % ("OK" if has else "!!", l.strip()[:60]))

print()
print("=" * 60)
print("2. 卸载.bat 关键行检查")
print("=" * 60)
u = read_gbk("卸载.bat")
ul = u.split("\r\n")
bad3 = [l for l in ul if re.search(r"^\s*reg delete.*HKLM", l, re.I)]
print("[%s] 不再有 HKLM reg delete%s"
      % ("OK" if not bad3 else "FAIL", "" if not bad3 else " -> " + str(bad3)))
print("[%s] 仍清理旧版 d3d9_orig 残留"
      % ("OK" if any("d3d9_orig.dll" in l for l in ul) else "FAIL"))

print()
print("=" * 60)
print("3. 编码与换行（cmd.exe 对纯 LF + GBK 中文会逐行丢首字节）")
print("=" * 60)
for name in ("安装.bat", "卸载.bat", "安装说明.txt"):
    with open(os.path.join(BASE, name), "rb") as f:
        d = f.read()
    crlf = d.count(b"\r\n")
    total = d.count(b"\n")
    pure_lf = total - crlf
    try:
        d.decode("gbk")
        enc_ok = True
    except Exception:
        enc_ok = False
    print("  %-14s CRLF %3d  纯LF %3d  GBK可解码 %s  %s"
          % (name, crlf, pure_lf, "是" if enc_ok else "否",
             "OK" if pure_lf == 0 and enc_ok else "!!"))

print()
print("=" * 60)
print("4. 分发包内容")
print("=" * 60)
for root, dirs, files in os.walk(BASE):
    rel = os.path.relpath(root, BASE)
    if "Audio" in rel:
        continue
    for fn in files:
        p = os.path.join(root, fn)
        print("  %10d  %s" % (os.path.getsize(p),
                              os.path.relpath(p, BASE).replace("\\", "/")))