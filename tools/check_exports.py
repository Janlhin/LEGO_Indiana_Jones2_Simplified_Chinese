#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""校验 d3d9 代理 DLL 的导出表。

核心目的
--------
新旧两版代理的 16 个导出在 PE 层面长得不一样：

- **旧版**用 forwarder：`Direct3DCreate9 = d3d9_orig.Direct3DCreate9`。
  导出表里每一项的函数地址不是代码地址，而是指向 `.rdata` 里
  字符串 `"d3d9_orig.Direct3DCreate9"` 的 RVA。游戏调用时由Windows
  加载器直接转发，**不经过代理的代码**，因此代理必须依赖同目录的
  `d3d9_orig.dll`，该文件缺失时进程初始化直接失败。

- **新版**用显式桩函数：导出表的每一项指向 `.text` 里的真实代码，
  桩内部自己 `GetSystemDirectoryW` + `LoadLibraryW` 加载系统 d3d9。
  游戏目录里只需要代理一个文件。

判断方法：若某个导出的函数地址落在「导出目录」范围内，它就是
forwarder（字符串）；否则是真实代码地址。

用法
----
    python check_exports.py <dll路径>

退出码 0 = 全部通过；1 = 有问题。
"""

import struct
import sys

# 期望的 16 个导出名。
#
# 这份清单曾经是 17 个，其中第 15 项写作 Direct3D9ShaderValidatorCreate9 ——
# 但这个名字**不存在于任何 d3d9.dll 里**（实测：SysWOW64 版d3d9.dll 的
# 具名导出中没有任何含 "Shader" 的项），是早期凭想象补上去的。
# 它会导致 bind_real() 的「导出绑不全」检查永远失败，代理 DLL 弹框退场。
#
# 另一个关键事实：游戏实际只 GetProcAddress 一个 Direct3DCreate9。
# exe 里 LoadLibraryA 与 "d3d9.dll"、"Direct3DCreate9" 三个字符串相邻，
# 导入表根本没有 d3d9.dll 条目 —— 是运行时动态加载，不是静态导入。
# 之所以仍导出全套 16 个：与旧转发方案保持一致，多导出不加载的符号
# 零成本，少导出则会让「万一被查」变成硬失败。
EXPECT = [
    "D3DPERF_BeginEvent",
    "D3DPERF_EndEvent",
    "D3DPERF_GetStatus",
    "D3DPERF_QueryRepeatFrame",
    "D3DPERF_SetMarker",
    "D3DPERF_SetOptions",
    "D3DPERF_SetRegion",
    "DebugSetLevel",
    "DebugSetMute",
    "Direct3D9EnableMaximizedWindowedModeShim",
    "Direct3DCreate9",
    "Direct3DCreate9Ex",
    "Direct3DCreate9On12",
    "Direct3DCreate9On12Ex",
    "PSGPError",
    "PSGPSampleTexture",
]


class PEError(Exception):
    pass


class PE(object):
    """极简 PE 解析器，只取导出表所需信息。不用第三方库。"""

    def __init__(self, path):
        with open(path, "rb") as f:
            self.d = f.read()
        self.path = path
        if self.d[:2] != b"MZ":
            raise PEError("不是 PE 文件（缺 MZ）")
        self.pe = struct.unpack_from("<I", self.d, 0x3C)[0]
        if self.d[self.pe:self.pe + 4] != b"PE\0\0":
            raise PEError("PE 签名无效")
        nsec = struct.unpack_from("<H", self.d, self.pe + 6)[0]
        self.opt = self.pe + 24
        magic = struct.unpack_from("<H", self.d, self.opt)[0]
        if magic == 0x10B:
            self.dd = self.opt + 96          # PE32
        elif magic == 0x20B:
            self.dd = self.opt + 112# PE32+
        else:
            raise PEError("未知可选头魔数 0x%X" % magic)
        opt_size = struct.unpack_from("<H", self.d, self.pe + 20)[0]
        so = self.pe + 24 + opt_size
        self.sections = []
        for i in range(nsec):
            b = so + i * 40
            name = self.d[b:b + 8].rstrip(b"\0").decode("latin1")
            vs, va, rs, ra = struct.unpack_from("<IIII", self.d, b + 8)
            self.sections.append((name, vs, va, rs, ra))

    def rva2off(self, rva):
        for _n, vs, va, rs, ra in self.sections:
            if va <= rva < va + max(vs, rs):
                return ra + (rva - va)
        return None

    def cstr(self, off):
        end = self.d.index(b"\0", off)
        return self.d[off:end].decode("latin1")

    def exports(self):
        """返回 {name: ('CODE', rva) | ('FORWARDER', 'target')}。"""
        exp_rva, exp_sz = struct.unpack_from("<II", self.d, self.dd)
        if not exp_rva:
            raise PEError("无导出表")
        eo = self.rva2off(exp_rva)
        if eo is None:
            raise PEError("导出表 RVA 无法映射")
        (_fl, _ts, _maj, _mnr, _nm, _ob,
         nfuncs, nnames, af, an, ao) = struct.unpack_from("<IIHHIIIIIII", self.d, eo)
        off_af = self.rva2off(af)
        off_an = self.rva2off(an)
        off_ao = self.rva2off(ao)
        out = {}
        for i in range(nnames):
            name_rva = struct.unpack_from("<I", self.d, off_an + 4 * i)[0]
            nm = self.cstr(self.rva2off(name_rva))
            ordi = struct.unpack_from("<H", self.d, off_ao + 2 * i)[0]
            if ordi >= nfuncs:
                continue
            frva = struct.unpack_from("<I", self.d, off_af + 4 * ordi)[0]
            # 落在导出目录内 => 指向字符串，即 forwarder
            if exp_rva <= frva < exp_rva + exp_sz:
                fo = self.rva2off(frva)
                out[nm] = ("FORWARDER", self.cstr(fo) if fo is not None else "?")
            elif frva == 0:
                out[nm] = ("EMPTY", "0")
            else:
                out[nm] = ("CODE", "0x%08X" % frva)
        return out, exp_rva, exp_sz


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    try:
        pe = PE(path)
        exp, exp_rva, exp_sz = pe.exports()
    except PEError as e:
        print("FAIL 解析失败: %s" % e)
        return 1

    print("文件 %s" % path)
    print("大小 %d B   导出目录 RVA 0x%X大小 %d" % (len(pe.d), exp_rva, exp_sz))
    print("")

    bad = 0
    fwd = 0
    for name in EXPECT:
        kind, val = exp.get(name, ("MISSING", ""))
        if kind != "CODE":
            fwd += 1 if kind == "FORWARDER" else 0
            print("FAIL  %-42s %s %s" % (name, kind, val))
            bad += 1
        else:
            print("ok    %-42s -> %s" % (name, val))

    extra = sorted(set(exp) - set(EXPECT))
    if extra:
        print("")
        print("多余导出 %d 个: %s" % (len(extra), ", ".join(extra)))

    print("")
    print("-" * 60)
    print("期望导出 %d   实际导出 %d   非 CODE %d" % (len(EXPECT), len(exp), bad))

    # 旧版特有：产物中不应再出现 d3d9_orig 字符串
    has_orig = b"d3d9_orig" in pe.d
    if has_orig:
        print("产物中仍含 'd3d9_orig' 字符串 -> 仍是转发版")
        bad += 1
    else:
        print("产物中无 'd3d9_orig' 字符串")

    # 只扫 .rdata / .data，不能全文件盲扫 —— x86 机器码里偶然凑出合法
    # UTF-8 三字节序列的概率不低（实测 .text 段就有 400+ 处命中）。
    #
    # 判定 GBK 不能只看「高位字节对」：UTF-8 三字节序列的后两字节本身就
    # 落在 0x80..0xBF/0xBF 区间，二进制数据里更是到处都是这种字节对。
    # 上一版用字节对判定，误报 248 处。正确做法是**尝试解码**：
    # 把只读段里像中文的片段真正按 GBK 解一次，解不出合法汉字才算。
    # 更省事也更可靠的做法是直接找「已知标签的 GBK 编码字节序列」。
    utf8_cjk = 0
    for name, _vs, _va, rs, ra in pe.sections:
        if name not in (".rdata", ".data"):
            continue
        raw = pe.d[ra:ra + rs]
        i = 0
        while i < len(raw) - 2:
            b0 = raw[i]
            if 0xE0 <= b0 <= 0xEF and (raw[i + 1] & 0xC0) == 0x80 and (raw[i + 2] & 0xC0) == 0x80:
                utf8_cjk += 1
            i += 1

    # 已知标签的两种编码，直接查有无 —— 无歧义，不靠启发式
    whole = pe.d          # 全文件字节：标签常量应在其中
    probe_zh = ["画面设置", "屏幕分辨率", "垂直同步", "恢复默认设置",
                "宽高比", "使用当前设置", "退出到演示菜单"]
    utf8_hit = [z for z in probe_zh if z.encode("utf-8") in whole]
    gbk_hit = [z for z in probe_zh if z.encode("gbk") in whole]

    print("只读段 UTF-8 中文三字节序列：%d 处" % utf8_cjk)
    print("抽样标签以 UTF-8 存在：%d / %d %s"
          % (len(utf8_hit), len(probe_zh), utf8_hit))
    print("抽样标签以 GBK  存在：%d / %d %s"
          % (len(gbk_hit), len(probe_zh), gbk_hit))

    gbk_cjk = len(gbk_hit)
    if gbk_cjk:
        print("!! 检出 GBK 中文常量 —— UI 文本管线要 UTF-8，GBK 会显示成满屏问号")

    print("")
    if bad:
        print("结果：不通过（%d 项问题）" % bad)
        return 1
    print("结果：通过 —— 16 个导出全部为真实代码，无 forwarder 残留")
    return 0


if __name__ == "__main__":
    sys.exit(main())