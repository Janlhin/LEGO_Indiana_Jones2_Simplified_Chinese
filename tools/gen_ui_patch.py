# -*- coding: utf-8 -*-
"""生成 d3d9proxy.c 用的 UI 补丁表头 ui_patch.h。

为什么需要生成而不是手写：
  * 中文必须以 **UTF-8 字节** 进 DLL 缓冲区。
    依据是实测（tools/probe_ui_encoding.py）：exe 的 UI 语言区里俄语
    «Вернуть» / «Качество» / «Использовать» 等串全部是合法 UTF-8，
    按 CP1252 / CP1254 解全是乱码；DAT 里的中文文本同样是 UTF-8。
    也就是说 UI 文本管线吃 UTF-8，不是系统 ANSI。
    （中途曾误判为 GBK，实际注入 GBK 后菜单全是问号 —— 问号正是严格
    UTF-8 解码器把非法字节逐个替换成 '?' 的表现，反过来印证了这条。）
    本脚本把中文 encode('utf-8') 后转成 \\xNN 转义，编译进 DLL 的
    就是正确的 UTF-8 字节，且不受源文件编码 / 编辑器影响。
  * 指针表偏移必须来自对 exe 的实测解析，不能手抄。

安全设计（每一处都是为了「补丁不匹配就宁可不改」）：
  1. 只改 .data 里 4 字节的指针，不碰字符串内容、不碰 exe 文件
     -> 不触发 Steam DRM
  2. 每条补丁带 expected_str_va 与 expected_en，运行时先读回该 VA
     的字符串比对，不同就直接跳过 -> 换版本 / Steam 更新后自动失效而非写坏
  3. 只覆盖 EN-1 / EN-2 两段英文 UI。cvar 段（0xAB09F0..0xAB0B48）
     完全不碰，pcconfig.txt 的键名保持原样
  4. 按键名不在表内（表里没有任何 Left / Space / Num.3 之类），
     所以「按键不汉化」是结构上成立的，不靠人工筛

本脚本只生成头文件，不编译、不部署。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")

EXE = r"D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2\LEGOIndy2.exe"
OUT = r"09_toolchain\ui_patch.h"

BASE = 0x400000
RDATA_VA = 0x874000
RDATA_RA = 0x874000
RDATA_SZ = 1585152

# 整张表的范围（含 cvar 名 + 全部语言段）。实测见 tools/rescan_ui_table.py。
# 首版把表尾误设为 0xAB0F44，实际延伸到 0xAB17FF —— 因为每种语言都有
# 一份完整并行的翻译（英/法/德/意/西/丹/波/俄/捷…），远比想象的长。
# 0xAB2C08 之后已是着色器语义名（viewProj / SEMANTIC_*），属另一张表。
TABLE_LO = 0xAB09F0
TABLE_HI = 0xAB17DC + 8

# cvar 名段：pcconfig.txt 的键名，绝对不能动
CVAR_END = 0xAB0B48

# 英文段有**两份**（主菜单 / 关卡编辑器 Builder），每份 41 项。
# 表项是 8 字节结构 {char* text; uint32 id;}，不是首版假设的 4 字节纯指针。
# 首版只覆盖到 0xAB0C24/0xAB0D24，漏掉了 id>=0x24 的图形设置标签
# （FSAA / Externally Set / Shadows / Bloom / Depth of Field / Speed Blur /
#  Dynamic Light Quality / Edge AA / Ambient Occlusion / Show Game Controls），
# 用户实测反馈正是这些没汉化。
EN_SEGMENTS = [
    (0xAB0B5C, 0xAB0C9C),   # 主菜单英文段，41 项
    (0xAB0CA4, 0xAB0DE4),   # Builder 英文段，41 项
]

# 27 个英文标签的中文译名。只译 UI 标签，不含任何按键名。
ZH = {
    "Accept": "接受",
    "Aspect Ratio": "宽高比",
    "Back": "返回",
    "Cancel": "取消",
    "Decline": "拒绝",
    "Enhanced Graphics": "增强画质",
    "From Screen-Res": "跟随分辨率",
    "High": "高",
    "Low": "低",
    "Medium": "中",
    "No": "否",
    "OK": "确定",
    "Off": "关",
    "On": "开",
    "Quit": "退出",
    "Quit to Demos Menu": "退出到演示菜单",
    "Quit to Windows": "退出到 Windows",
    "Refresh Rate": "刷新率",
    "Reset To Defaults": "恢复默认设置",
    "Resume": "继续游戏",
    "Return to game": "返回游戏",
    "Screen Resolution": "屏幕分辨率",
    "Texture Quality": "纹理质量",
    "Use current settings": "使用当前设置",
    "Vertical Sync": "垂直同步",
    "Video Settings": "画面设置",
    "Yes": "是",

    # ---- 以下为首版遗漏的图形/效果设置标签（用户实测反馈未汉化）----
    # 注意「Texture Quality」原译「材质质量」导致首字缺字形，
    # 改为「纹理质量」——更准确，且「纹」字在字体里存在。
    "Revert": "还原",
    "You must restart the game for these changes to take effect!":
        "需要重启游戏才能让这些设置生效",
    "Effects Settings": "特效设置",
    # FSAA = Full Screen Anti-Aliasing，全屏抗锯齿。「采」「缘」缺字形，
    # 故不用「多重采样」「边缘」等更长的等价说法
    "FSAA": "全屏抗锯齿",
    "Externally Set": "外部设置",
    "Shadows": "阴影",
    "Bloom": "泛光",
    "Depth of Field": "景深",
    "Speed Blur": "速度模糊",
    "Dynamic Light Quality": "动态光影质量",
    "Edge AA": "边角抗锯齿",   # 字体缺「缘」字，「边角」等价且全字形可用
    "Ambient Occlusion": "环境光遮蔽",
    "Show Game Controls": "显示游戏按键",   # 字体缺「说明」两字
}


def read_str(data, fo):
    end = data.find(b"\x00", fo)
    if end < 0:
        return None
    s = data[fo:end]
    if not s or any(c < 32 or c > 126 for c in s):
        return None
    return s.decode("ascii")


def collect():
    """按 8 字节项遍历两份英文段，收集 (槽偏移, 串VA, 原文)。"""
    with open(EXE, "rb") as f:
        data = f.read()

    rows = []
    unmapped = []
    for lo, hi in EN_SEGMENTS:
        off = lo
        while off < hi:
            va = struct.unpack_from("<I", data, off)[0]
            # 同项的第二个 DWORD 是 id（0x00..0x28），用于确认 8 字节步进没错位
            ident = struct.unpack_from("<I", data, off + 4)[0]
            if BASE + RDATA_VA <= va < BASE + RDATA_VA + RDATA_SZ:
                fo = va - BASE + (RDATA_RA - RDATA_VA)
                s = read_str(data, fo)
                if s:
                    if s in ZH:
                        rows.append((off, va, s))
                    else:
                        unmapped.append((off, s, ident))
            off += 8
    return rows, unmapped


def cesc(s):
    """把 GBK 字节写成 C 的 \\xNN 转义串。

    一律逐字节转义、不混用可打印字符直写，这样有两个好处：
      * GBK 字节不受源文件编码 / locale / 编辑器影响；
      * 每个 token 恰好是 \\xNN（占满 2 位十六进制），C 的十六进制
        贪婪匹配无从发生 —— 若写成 "\\xNN" 后面紧跟字符 'a' 会被并成
        0xNNа。上一版混写时就踩过这个坑（"退出到 Windows" 里的
        空格虽安全，但任何中文后跟数字/字母的组合都会炸）。
    """
    return '"' + "".join("\\x%02x" % c for c in s.encode("utf-8")) + '"'


def main():
    rows, unmapped = collect()

    print("英文 UI 标签指针：%d 条" % len(rows))
    if unmapped:
        print("\n!! 以下指针在 EN 段但没有译名（将跳过，请补进 ZH 表）：")
        for off, s, ident in unmapped:
            print("   ptr@0x%X id=0x%X  %r" % (off, ident, s))
        if not ZH:
            sys.exit(1)

    labels = []
    label_index = {}
    for _, _, s in rows:
        if s not in label_index:
            label_index[s] = len(labels)
            labels.append(s)

    lines = []
    w = lambda *a: lines.append(a[0] % a[1:] if len(a) > 1 else a[0])
    w("/* 本文件由 tools/gen_ui_patch.py 自动生成，请勿手改。")
    w(" * 源 exe: %s" % EXE)
    w(" * 指针表: .data 原始偏移 0x%X..0x%X" % (TABLE_LO, TABLE_HI))
    w(" *   cvar 名段   0x%X 之前（pcconfig.txt 键名，不汉化）" % CVAR_END)
    for i, (lo, hi) in enumerate(EN_SEGMENTS, 1):
        w(" *   英文段 %d0x%X..0x%X（%d 项）" % (i, lo, hi, (hi - lo) // 8))
    w(" * 映像基址 0x%08X", BASE)
    w(" *")
    w(" * 注意中文常量存的是 **UTF-8** 字节 —— 实测 exe 的 UI 文本管线")
    w(" * 吃 UTF-8（俄语/法语等语言串全为合法 UTF-8）。写 GBK 会全屏问号，")
    w(" * 因为严格 UTF-8 解码器会把非法字节逐个替换成 '?'。")
    w(" */")
    w("#ifndef UI_PATCH_H")
    w("#define UI_PATCH_H")
    w("")
    w("/* %d 个标签的 UTF-8 字节串（供补丁做运行时比对，也可单独用于自检） */" % len(labels))
    w("static const char *const ui_zh_label[] = {")
    for s in labels:
        w("    %s,   /* %s */" % (cesc(ZH[s]), s))
    w("};")
    w("#define UI_ZH_COUNT %d" % len(labels))
    w("")
    w("/* 每条补丁：")
    w(" *   rva   = 指针项自身在映像内的偏移（改的是这 4 个字节）")
    w(" *   sva   = 该指针当前应指向的英文串 VA（比对用）")
    w(" *   en    = 该英文串（比对用）")
    w(" *   zh    = 自备 UTF-8 串（改指向它）")
    w(" *")
    w(" * rva 的算法：指针表在 .data 节，实测该节 VA == RawAddr（见")
    w(" * tools/verify_rva_maps.py），所以文件偏移**本身就是 RVA**，")
    w(" * 不能减 ImageBase。早先写成 off-ImageBase 会整体偏 0x400000，")
    w(" * 补丁会写到完全无关的内存地址上。")
    w(" */")
    w("typedef struct {")
    w("    unsigned long rva;")
    w("    unsigned long sva;")
    w("    const char *en;")
    w("    const char *zh;")
    w("} ui_patch_t;")
    w("")
    w("/* 整张指针表（含未涉及的 cvar 与其它语言段）的范围，")
    w(" * 供一次性 VirtualProtect 用。 */")
    w("#define UI_TABLE_RVA_LO 0x%XUL" % TABLE_LO)
    w("#define UI_TABLE_RVA_HI 0x%XUL" % TABLE_HI)
    w("")
    w("static const ui_patch_t ui_patches[] = {")
    for off, va, s in rows:
        idx = label_index[s]
        w("    { 0x%06XUL, 0x%08XUL, %s, ui_zh_label[%d] },  /* %s */" % (
            off, va, cesc(s), idx, s))
    w("};")
    w("#define UI_PATCH_COUNT %d" % len(rows))
    w("")
    w("#endif /* UI_PATCH_H */")

    with open(OUT, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")

    print("\n已写出 %s" % OUT)
    print("  补丁条数 %d，唯一标签 %d" % (len(rows), len(labels)))
    for s in labels:
        print("    %-22r -> %s" % (s, ZH[s]))


if __name__ == "__main__":
    main()
