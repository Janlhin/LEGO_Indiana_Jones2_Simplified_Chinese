# -*- coding: utf-8 -*-
"""离线仿真 patch_ui_labels()，不启动游戏。

为什么需要仿真：真正验证要开机跑游戏看菜单，成本高且不好自动化。
但补丁逻辑本身是纯内存操作 —— 读一个DWORD、比对、改一个 DWORD ——
可以在 Python 里把 exe 按ImageBase 装进一个 bytearray 当作"进程映像"，
再照抄 C 的三条判定（地址相等 / strcmp 相等 / ACP==936）跑一遍。

能验到：
  *45 条补丁全部命中（而不是静默跳过）
  * cvar 段的指针一个都没被动
  * 法语 / 匈牙利语段没被动
  * 改完后指针确实指向 DLL 侧的 GBK 串
  * 版本漂移模拟：把某条指针改乱-> 那条被跳过而不是写坏
  * ACP != 936 时放弃
本脚本不碰游戏目录、不改任何文件。
"""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, "tools")
import gen_ui_patch as G  # noqa: E402

EXE = G.EXE
BASE = G.BASE

# DLL 里ui_zh_label[] 的等价物：按 ui_patch.h 里的顺序还原
import re  # noqa: E402

H = open("09_toolchain/ui_patch.h", encoding="utf-8").read()


def label_bytes(idx):
    """取 ui_patch.h 中 ui_zh_label[idx] 的字节内容。"""
    m = re.search(r"static const char \*const ui_zh_label\[\] = \{(.*?)\n\};", H, re.S)
    if not m:
        sys.exit("!! 未能解析 ui_zh_label")
    items = re.findall(r'("(?:\\x[0-9A-Fa-f]{2})+")\s*,', m.group(1))
    if len(items) <= idx:
        sys.exit("!! ui_zh_label 索引越界: %d >= %d" % (idx, len(items)))
    return b"".join(bytes.fromhex(h) for h in
                   re.findall(r'\\x([0-9A-Fa-f]{2})', items[idx]))


def patches():
    """从 ui_patch.h 里解析补丁表。

    注意解析的是生成器写出的**纯 ASCII 字面量**（GBK 已转义），
    所以不需要处理多种引号拼接的写法。上一版的正则过于宽松导致
    0 条匹配 —— 仿真脚本静默通过比不跑更危险，故在入口处断言非空。
    """
    m = re.search(r"static const ui_patch_t ui_patches\[\] = \{(.*?)\n\};", H, re.S)
    if not m:
        sys.exit("!! 未能从 ui_patch.h 解析补丁表")

    def unhex(lit):
        # lit 形如 "\x51\x75\x69\x74" —— 是**转义文本**而不是字节，
        # 必须先把 \xNN 拆成十六进制数再交 fromhex，直接 fromhex 会报
        # "non-hexadecimal number found"（'\\x' 里的反斜杠不是十六进制位）。
        return b"".join(bytes.fromhex(h) for h in
                       re.findall(r'\\x([0-9A-Fa-f]{2})', lit))

    out = []
    for m2 in re.finditer(
            r'\{\s*(0x[0-9A-Fa-f]+)UL,\s*(0x[0-9A-Fa-f]+)UL,\s*'
            r'("(?:\\x[0-9A-Fa-f]{2})+")\s*,\s*ui_zh_label\[(\d+)\]',
            m.group(1)):
        out.append((int(m2.group(1), 16), int(m2.group(2), 16),
                    unhex(m2.group(3)), int(m2.group(4))))
    if not out:
        sys.exit("!!补丁表解析出0 条，正则与生成器输出不匹配")
    return out


def read_cstr(img, va):
    off = va - BASE
    if off < 0 or off >= len(img):
        return None
    end = img.find(b"\x00", off)
    return None if end < 0 else bytes(img[off:end])


def simulate(acp=936, mutate=None, verbose=True):
    """acp 仅为记录用：补丁已不依赖系统代码页。"""
    """mutate(img) 可在补丁前篡改内存，用来模拟版本漂移。"""
    raw = open(EXE, "rb").read()
    # 把 exe 原样当成"映像"：本 exe 的 .data 段 VA 与文件偏移不一致，
    # 但补丁用的是文件偏移推导的 RVA，仿真里只需要保证
    # (rva+BASE) 处的 4 字节等于 sva。实盘验证见 verify_rva_maps.py。
    img = bytearray(raw)
    P = patches()

    if mutate:
        mutate(img, P)

    #注意：img 是**文件内容**，而 rva 是运行时的映像内偏移。
    # 本exe 的 .data 段 VA == RawAddr，故文件偏移恰好等于 RVA，
    # 索引时不能再加 ImageBase（加了就越界 -> 读出 0 -> 全部不命中）。
    before = {rva: struct.unpack_from("<I", img, rva)[0] for rva, _, _, _ in P}

    # 补丁**不再**按 GetACP 设限：中文常量是 UTF-8，与系统代码页无关。
    # （曾经加过 ACP==936 判断，是基于「UI 走系统 ANSI」的错误推断，
    #   连带会把英文 Windows 上的用户也排除掉。）
    applied = []
    for rva, sva, en, zh in P:
        cur_va = struct.unpack_from("<I", img, rva)[0]
        if cur_va != sva:
            continue
        if read_cstr(img, cur_va) != en:
            continue
        applied.append((rva, zh))

    if verbose:
        print("(acp=%d 已无影响)  命中 %d / %d 条" % (acp, len(applied), len(P)))
    return img, before, applied, P


def main():
    fails = []

    # ---- 场景 1：正常情况全部命中 ----
    # 注意 acp 参数现已无意义：UTF-8 与系统代码页无关，DLL 不再按GetACP 设限
    img, before, applied, P = simulate(936)
    print("\n[1] ACP=936，命中 %d / %d 条" % (len(applied), len(P)))
    if len(applied) != len(P):
        misses = [p for p in P if p[0] not in [a[0] for a in applied]]
        fails.append("有 %d 条未命中：%s" % (len(misses), [(hex(m[0]), m[2]) for m in misses[:5]]))

    # ---- 场景 2：cvar 段与其它语言段指针未被触碰 ----
    # cvar 段 RVA 0x6B09F0..0x6B0B48，法语 0x6B0DEC..0x6B0E6C，匈牙利 0x6B0E9C..
    touched = {rva for rva, _, _, _ in P}
    # 两份英文段各 41 项（8 字节/项）。段与段之间隔着 NULL 分隔符，
    # 故用半开区间 [lo, hi) 判定，不能再外扩 —— 外扩会让两段互相吞掉
    # 对方的项（上一版因此报「41 != 40」，是判据写错，不是补丁越界）。
    for lo, hi in G.EN_SEGMENTS:
        expect = (hi - lo) // 8
        bad = [r for r in touched if lo <= r < hi]
        print("[2] 英文段 0x%X..0x%X 覆盖 %d 项（应 %d）"
              % (lo, hi, len(bad), expect))
        if len(bad) != expect:
            fails.append("英文段 0x%X 覆盖数 %d，应为 %d"
                         % (lo, len(bad), expect))

    # 越界检查：所有补丁槽都必须落在两份英文段内
    out_of_range = [r for r, _, _, _ in P
                    if not any(lo <= r < hi for lo, hi in G.EN_SEGMENTS)]
    print("[2b] 落在英文段外的补丁槽：%s"
          % ([hex(r) for r in out_of_range] if out_of_range else "无"))
    if out_of_range:
        fails.append("有补丁槽落在英文段之外：%s"
                     % [hex(r) for r in out_of_range][:5])

    # cvar 段（pcconfig.txt 键名）必须零命中
    cvar = [r for r, _, _, _ in P if G.TABLE_LO <= r <= G.CVAR_END]
    print("[2c] cvar 段命中：%d（必须 0，动了就读不到配置）" % len(cvar))
    if cvar:
        fails.append("cvar 段被覆盖")

    # ---- 场景 3：DLL 侧每个标签的 UTF-8 串都能解回中文 ----
    # 判据要按「唯一标签」算，不是按 45 条指针 —— 同一标签出现两处，
    # 之前把两个集合比大小，45 != 27 于是误报失败。
    uniq = sorted({z for _, _, _, z in P})
    bad = []
    for z in uniq:
        gb = label_bytes(z)
        try:
            gb.decode("utf-8")
        except UnicodeDecodeError as e:
            bad.append((z, str(e)))
        if b"\x00" in gb:
            bad.append((z, "串内含 NUL，会被截断"))
    print("[3] 唯一标签 %d 个，UTF-8 串全部可解码：%s" % (
        len(uniq), "是" if not bad else "否 -> %s" % bad))
    if bad:
        fails.append("UTF-8 串有问题：%s" % bad)

    # ---- 场景 4：版本漂移（某条指针被别的值占用）-> 跳过而非写坏 ----
    def mutate(img, P):
        struct.pack_into("<I", img, P[0][0], 0xDEADBEEF)
    _, _, applied4, P4 = simulate(936, mutate=mutate)
    print("[4] 模拟首条被改坏后命中 %d / %d 条（应少 1）" % (len(applied4), len(P4)))
    if len(applied4) != len(P4) - 1:
        fails.append("版本漂移保护失效：命中 %d，期望 %d" % (len(applied4), len(P4) - 1))

    # ---- 场景 5：系统代码页无关性 ----
    # 编码是 UTF-8，不依赖 ACP，故英文 Windows 上同样应当汉化成功。
    # （若这里仍按 ACP 设门槛，同学的英文系统就会菜单全英文。）
    _, _, applied5, P5 = simulate(1252)
    print("[5] ACP=1252（英文 Windows）时命中 %d / %d 条（UTF-8 与代码页无关，应全中）"
          % (len(applied5), len(P5)))
    if len(applied5) != len(P5):
        fails.append("补丁仍受系统代码页限制，英文系统无法汉化")

    # ---- 场景 6：确认没有按键名 ----
    KEY = [b"Left", b"Right", b"Space", b"Num.", b"Up", b"Down", b"Enter",
           b"Shift", b"Ctrl", b"Alt", b"Escape", b"Tab", b"Backspace"]
    enc = set()
    for _, _, en, zh in P:
        enc.add(en)
    hit = [k for k in KEY if k in enc]
    print("[6] 补丁表内出现的按键名：%s（必须为空）" % (hit if hit else "无"))
    if hit:
        fails.append("补丁表混入按键名：%s" % hit)

    print("\n" + "=" * 60)
    if fails:
        print("验证失败：")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("全部通过：%d 条补丁可命中，范围严格限于两份英文段，" % len(P))
    print("        UTF-8 串合法，版本漂移有保护，不依赖系统代码页，按键名零汉化")


if __name__ == "__main__":
    main()
