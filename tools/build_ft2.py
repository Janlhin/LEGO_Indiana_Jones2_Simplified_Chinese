"""构建 TT Games NXG 引擎 .FT2 (NFNT) 字体（含中文字形）。

用法:
  python build_ft2.py --charset-file charset.txt --out font_chi.FT2 \
      [--face "Microsoft YaHei"] [--atlas 2048] [--em 44] [--preview atlas.png]

结构（大端，参考 NFNT.md）:
  头部: size(u32) unk(u32=1) "TNFN" type(u32=2) version(u32=0) flags(u16)
        size2(u32) numChars(u32) unicodeTableSize(u32) height(f32)
        baseline(f32) spaceWidth(f32) sendid(u32) icgap(f32)
  posTable:  size(u32) + size 条 {x:f32, y:f32, w:f32}
  charsTable: size(u32) + size 条 {codepoint:u16, index:u16}  末尾 ffff
  kerning:   size(u32) (0 条)
  texture:   DDS (DXT5, 无 mip)
"""
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc3

BE = '>'
DDS_HEADER_SIZE = 128


# --------------------------------------------------------------------- 栅格化（GDI32 变宽）
def rasterize_glyphs(chars, face, em, tex_w, tex_h, line_h, baseline,
                     pad=2, quality=4, weight=400, italic=0, space_width=12):
    """渲染 chars 到 RGBA 纹理，返回 (posTable, rgba, actual_h)。"""
    import ctypes
    from ctypes import wintypes

    gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG),
                    ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD)]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]

    class TEXTMETRICW(ctypes.Structure):
        _fields_ = [('tmHeight', wintypes.LONG), ('tmAscent', wintypes.LONG),
                    ('tmDescent', wintypes.LONG), ('tmInternalLeading', wintypes.LONG),
                    ('tmExternalLeading', wintypes.LONG), ('tmAveCharWidth', wintypes.LONG),
                    ('tmMaxCharWidth', wintypes.LONG), ('tmWeight', wintypes.LONG),
                    ('tmOverhang', wintypes.LONG), ('tmDigitizedAspectX', wintypes.LONG),
                    ('tmDigitizedAspectY', wintypes.LONG), ('tmFirstChar', wintypes.WCHAR),
                    ('tmLastChar', wintypes.WCHAR), ('tmDefaultChar', wintypes.WCHAR),
                    ('tmBreakChar', wintypes.WCHAR), ('tmItalic', ctypes.c_byte),
                    ('tmUnderlined', ctypes.c_byte), ('tmStruckOut', ctypes.c_byte),
                    ('tmPitchAndFamily', ctypes.c_byte), ('tmCharSet', ctypes.c_byte)]

    class SIZE(ctypes.Structure):
        _fields_ = [('cx', wintypes.LONG), ('cy', wintypes.LONG)]

    hdc = gdi32.CreateCompatibleDC(None)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = tex_w
    bmi.bmiHeader.biHeight = -tex_h          # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0          # BI_RGB
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    old_bmp = gdi32.SelectObject(hdc, hbmp)

    hfont = gdi32.CreateFontW(-em, 0, 0, 0, weight, italic, 0, 0, 1, 4, 0,
                              quality, 0, face)
    old_font = gdi32.SelectObject(hdc, hfont)
    tm = TEXTMETRICW()
    gdi32.GetTextMetricsW(hdc, ctypes.byref(tm))
    gdi32.SetTextColor(hdc, 0x00FFFFFF)
    gdi32.SetBkColor(hdc, 0x00000000)
    gdi32.SetBkMode(hdc, 1)                 # TRANSPARENT

    ascent = tm.tmAscent
    # 实际渲染用的行高与基线（若未指定则取 em 附近）
    pos_table = []
    x, y = pad, 0
    for ch in chars:
        s = ch
        sz = SIZE()
        gdi32.GetTextExtentPoint32W(hdc, ctypes.c_wchar_p(s), len(s), ctypes.byref(sz))
        w = sz.cx
        if w <= 0:
            w = em
        if x + w + pad > tex_w:
            x = pad
            y += line_h
        # 字形从行顶 y 处绘制（GDI 默认 TA_TOP：y=字形单元顶部）
        gdi32.TextOutW(hdc, x, y, ctypes.c_wchar_p(s), len(s))
        pos_table.append((float(x), float(y), float(w)))
        x += w + pad
    actual_h = y + line_h if pos_table else line_h

    # ---- 绘制全部完成后，统一测每字形墨迹宽，回填 advance ----
    # advance 用"墨迹宽+2"而非全角 em：全角宽让长文本总宽超 GUI 列宽，
    # 游戏压缩渲染导致"挤一块"；原版实测 advance≈墨迹+1（i=15/W=41）
    gdi32.GdiFlush()
    buf = ctypes.string_at(bits, tex_w * tex_h * 4)
    advs = []
    for (gx, gy, gw) in pos_table:
        ix, iy, iw = int(gx), int(gy), int(gw)
        ink = 0
        row_span = min(tm.tmHeight + 4, line_h, tex_h - iy)
        for dy in range(row_span):
            row = iy + dy
            for dx in range(iw - 1, -1, -1):
                o = (row * tex_w + ix + dx) * 4
                if buf[o] > 40 or buf[o + 1] > 40 or buf[o + 2] > 40:
                    if dx + 1 > ink:
                        ink = dx + 1
                    break
        advs.append(float(ink + 2) if ink > 1 else float(space_width))
    pos_table = [(gx, gy, adv) for (gx, gy, _), adv in zip(pos_table, advs)]

    # 拷贝 RGBA（BGRA -> RGBA）
    buf_size = tex_w * tex_h * 4
    raw = ctypes.string_at(bits, buf_size)
    rgba = bytearray(tex_w * tex_h * 4)
    for p in range(tex_w * tex_h):
        o = p * 4
        b, g, r = raw[o], raw[o + 1], raw[o + 2]
        a = max(r, g, b)
        rgba[p * 4] = r
        rgba[p * 4 + 1] = g
        rgba[p * 4 + 2] = b
        rgba[p * 4 + 3] = a

    gdi32.SelectObject(hdc, old_font)
    gdi32.SelectObject(hdc, old_bmp)
    gdi32.DeleteObject(hfont)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc)
    return pos_table, rgba, actual_h, {'ascent': tm.tmAscent, 'descent': tm.tmDescent, 'tmHeight': tm.tmHeight}


# --------------------------------------------------------------------- DDS 组装
def build_dds(rgba, w, h):
    """DXT5 单 mip DDS，返回字节。"""
    dxt = bc3.encode_bc3(rgba, w, h)
    pitch = w * h  # DXT5 每像素 1 字节
    flags = 0x81007  # CAPS|HEIGHT|WIDTH|PIXELFORMAT|LINEARSIZE
    pf_flags = 0x4   # DDPF_FOURCC
    fourcc = b'DXT5'
    header = bytearray(128)
    header[0:4] = b'DDS '
    struct.pack_into('<I', header, 4, 124)      # dwSize
    struct.pack_into('<I', header, 8, flags)
    struct.pack_into('<I', header, 12, h)       # height
    struct.pack_into('<I', header, 16, w)       # width
    struct.pack_into('<I', header, 20, pitch)   # pitch/linear size
    struct.pack_into('<I', header, 28, 0)       # mip count = 0
    struct.pack_into('<I', header, 76, 32)      # pf size
    struct.pack_into('<I', header, 80, pf_flags)
    header[84:88] = fourcc
    struct.pack_into('<I', header, 108, 0x1000)  # caps = TEXTURE
    return bytes(header) + dxt


# --------------------------------------------------------------------- FT2 组装
def build_ft2(chars, face, em, tex_w, tex_h, line_h, baseline, space_width, weight=400, italic=0):
    pos_table, rgba, actual_h, meta = rasterize_glyphs(
        chars, face, em, tex_w, tex_h, line_h, baseline, weight=weight,
        italic=italic, space_width=space_width)

    n = len(chars)
    num_chars = n + 1  # posTable 条数 = 1 个空字形 + n 个字符

    # 头部（大端）
    header = bytearray(0x36)
    # size 字段稍后回填（表区大小 = DDS 偏移 - 4）
    struct.pack_into(BE + 'I', header, 4, 1)          # unk
    header[8:12] = b'TNFN'
    struct.pack_into(BE + 'I', header, 12, 2)         # type
    struct.pack_into(BE + 'I', header, 16, 0)         # version
    struct.pack_into(BE + 'H', header, 20, 0)         # flags
    # size2 稍后回填
    struct.pack_into(BE + 'I', header, 26, num_chars)          # numChars
    struct.pack_into(BE + 'I', header, 30, num_chars)          # unicodeTableSize
    struct.pack_into(BE + 'f', header, 34, float(line_h))       # height = 行高
    struct.pack_into(BE + 'f', header, 38, float(meta['ascent']))  # baseline = ascent
    struct.pack_into(BE + 'f', header, 42, float(space_width))  # spaceWidth
    struct.pack_into(BE + 'I', header, 46, 0)          # sendid
    struct.pack_into(BE + 'f', header, 50, 0.0)        # icgap

    # posTable: size + 条目（index 0 是空字形）
    pos = bytearray()
    pos += struct.pack(BE + 'I', num_chars)
    pos += struct.pack(BE + '3f', 0.0, 0.0, 0.0)      # index 0 空
    for (x, y, w) in pos_table:
        pos += struct.pack(BE + '3f', x, y, w)

    # charsTable: size + 条目 + ffff
    chars_b = bytearray()
    chars_b += struct.pack(BE + 'I', num_chars)
    for i, ch in enumerate(chars):
        cp = ord(ch)
        if cp > 0xFFFF:
            cp = 0xFFFF  # 超出 BMP 的字符（一般不会）
        chars_b += struct.pack(BE + 'HH', cp, i + 1)
    chars_b += struct.pack(BE + 'HH', 0xFFFF, 0xFFFF)

    # kerning: 0 条
    kerning = struct.pack(BE + 'I', 0)

    # DDS
    dds = build_dds(rgba, tex_w, tex_h)

    body = bytes(header) + bytes(pos) + bytes(chars_b) + kerning
    dds_off = len(body)
    # 回填 size 和 size2
    struct.pack_into(BE + 'I', header, 0, dds_off - 4)
    struct.pack_into(BE + 'I', header, 22, num_chars * 16 + 96)
    body = bytes(header) + bytes(pos) + bytes(chars_b) + kerning
    return body + dds


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--charset-file', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--face', default='Microsoft YaHei')
    ap.add_argument('--atlas', type=int, default=2048)
    ap.add_argument('--atlas-h', type=int, default=None)
    ap.add_argument('--em', type=int, default=44)
    ap.add_argument('--line-h', type=int, default=56)
    ap.add_argument('--baseline', type=int, default=44)
    ap.add_argument('--space-width', type=int, default=12)
    ap.add_argument('--weight', type=int, default=400)
    ap.add_argument('--italic', type=int, default=0)
    ap.add_argument('--preview', default=None)
    a = ap.parse_args()

    # 读字符集（UTF-8）
    with open(a.charset_file, 'r', encoding='utf-8-sig') as f:
        chars = list(f.read())
    # 去重、排序（ASCII 在前，然后 Unicode 升序）
    chars = sorted(set(chars))
    # 确保空格和基本 ASCII 存在
    for c in ' ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789':
        if c not in chars:
            chars.append(c)
    chars = sorted(set(chars))

    data = build_ft2(chars, a.face, a.em, a.atlas, a.atlas_h or a.atlas,
                     a.line_h, a.baseline, a.space_width, a.weight, a.italic)
    with open(a.out, 'wb') as f:
        f.write(data)
    print('chars=%d  -> %s (%d 字节)' % (len(chars), a.out, len(data)))

    if a.preview:
        # 预览：解析出 DDS 解码 PNG
        dds_off = data.find(b'DDS ')
        h = struct.unpack_from('<I', data, dds_off + 12)[0]
        w = struct.unpack_from('<I', data, dds_off + 16)[0]
        rgba = bc3.decode_bc3(data, dds_off + 128, w, h)
        bc3.write_png(a.preview, w, h, rgba)
        print('preview -> %s (%dx%d)' % (a.preview, w, h))


if __name__ == '__main__':
    main()
