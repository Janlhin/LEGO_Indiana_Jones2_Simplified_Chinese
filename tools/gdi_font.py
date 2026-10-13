"""Rasterise arbitrary Unicode glyphs to an 8-bit alpha bitmap using GDI32.

Pure ctypes - no third-party dependency. Works on any Windows Python.

Renders a whole charset into a fixed-pitch grid so every glyph shares one
baseline, then returns (alpha_bytes, advances) where alpha is width*height bytes.
"""
import ctypes
from ctypes import wintypes

gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
user32 = ctypes.WinDLL('user32', use_last_error=True)

BI_RGB = 0
DIB_RGB_COLORS = 0
TRANSPARENT = 1
FW_NORMAL, FW_BOLD = 400, 700
ANTIALIASED_QUALITY = 4
CLEARTYPE_QUALITY = 5
DEFAULT_CHARSET = 1
OUT_TT_PRECIS = 4
CLIP_DEFAULT_PRECIS = 0
DEFAULT_PITCH = 0
FF_DONTCARE = 0


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


def render_charset(chars, cols, pitch, face=b'Microsoft YaHei', bold=True,
                   quality=CLEARTYPE_QUALITY, em=None):
    """Render `chars` into a grid of `cols` columns, cell = pitch x pitch.

    Returns (width, height, alpha, advances, rows, meta) where
      alpha    : bytearray(width*height) 8-bit coverage
      advances : list of per-char advance widths in pixels
      meta     : dict with ascent/descent/tmHeight actually used
    """
    n = len(chars)
    rows = (n + cols - 1) // cols
    W, H = cols * pitch, rows * pitch
    em = em or pitch

    hdc = gdi32.CreateCompatibleDC(None)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = W
    bmi.bmiHeader.biHeight = -H          # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), DIB_RGB_COLORS,
                                  ctypes.byref(bits), None, 0)
    old_bmp = gdi32.SelectObject(hdc, hbmp)

    weight = FW_BOLD if bold else FW_NORMAL
    hfont = gdi32.CreateFontW(-em, 0, 0, 0, weight, 0, 0, 0, DEFAULT_CHARSET,
                              OUT_TT_PRECIS, CLIP_DEFAULT_PRECIS, quality,
                              DEFAULT_PITCH | FF_DONTCARE, face)
    old_font = gdi32.SelectObject(hdc, hfont)

    tm = TEXTMETRICW()
    gdi32.GetTextMetricsW(hdc, ctypes.byref(tm))
    gdi32.SetTextColor(hdc, 0x00FFFFFF)
    gdi32.SetBkColor(hdc, 0x00000000)
    gdi32.SetBkMode(hdc, TRANSPARENT)
    gdi32.SetTextAlign(hdc, 0)

    linebox = tm.tmAscent + tm.tmDescent
    top_pad = max(0, (pitch - linebox) // 2)

    advances = []
    for i, ch in enumerate(chars):
        col, row = i % cols, i // cols
        x = col * pitch
        y = row * pitch + top_pad + tm.tmAscent
        s = ch
        gdi32.TextOutW(hdc, x, y, ctypes.c_wchar_p(s), len(s))
        sz = SIZE()
        gdi32.GetTextExtentPoint32W(hdc, ctypes.c_wchar_p(s), len(s), ctypes.byref(sz))
        advances.append(sz.cx)

    # copy DIB bits out and convert BGRA -> alpha (max channel)
    buf_size = W * H * 4
    raw = ctypes.string_at(bits, buf_size)
    alpha = bytearray(W * H)
    for p in range(W * H):
        o = p * 4
        v = raw[o] if raw[o] >= raw[o + 1] else raw[o + 1]
        if raw[o + 2] > v:
            v = raw[o + 2]
        alpha[p] = v

    gdi32.SelectObject(hdc, old_font)
    gdi32.SelectObject(hdc, old_bmp)
    gdi32.DeleteObject(hfont)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc)

    meta = {'ascent': tm.tmAscent, 'descent': tm.tmDescent,
            'tmHeight': tm.tmHeight, 'linebox': linebox, 'top_pad': top_pad,
            'em': em, 'cols': cols, 'rows': rows, 'width': W, 'height': H}
    return W, H, alpha, advances, rows, meta


def list_font_faces():
    """Enumerate installed font face names via GDI."""
    out = []

    class LOGFONTW(ctypes.Structure):
        _fields_ = [('lfHeight', wintypes.LONG), ('lfWidth', wintypes.LONG),
                    ('lfEscapement', wintypes.LONG), ('lfOrientation', wintypes.LONG),
                    ('lfWeight', wintypes.LONG), ('lfItalic', ctypes.c_byte),
                    ('lfUnderline', ctypes.c_byte), ('lfStrikeOut', ctypes.c_byte),
                    ('lfCharSet', ctypes.c_byte), ('lfOutPrecision', ctypes.c_byte),
                    ('lfClipPrecision', ctypes.c_byte), ('lfQuality', ctypes.c_byte),
                    ('lfPitchAndFamily', ctypes.c_byte), ('lfFaceName', wintypes.WCHAR * 32)]

    class ENUMLOGFONTEXW(ctypes.Structure):
        _fields_ = [('elfLogFont', LOGFONTW), ('elfFullName', wintypes.WCHAR * 64),
                    ('elfStyle', wintypes.WCHAR * 32), ('elfScript', wintypes.WCHAR * 32)]

    hdc = gdi32.CreateCompatibleDC(None)
    CB = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                            wintypes.DWORD, wintypes.LPARAM)

    def cb(lf, tm, fonttype, lp):
        e = ctypes.cast(lf, ctypes.POINTER(ENUMLOGFONTEXW)).contents
        out.append((e.elfLogFont.lfFaceName, e.elfStyle))
        return 1

    gdi32.EnumFontFamiliesExW(hdc, None, CB(cb), 0, 0)
    gdi32.DeleteDC(hdc)
    return out


if __name__ == '__main__':
    import sys
    faces = list_font_faces()
    want = sys.argv[1] if len(sys.argv) > 1 else 'yahei'
    for f, s in faces:
        if want.lower() in f.lower() or want.lower() in s.lower():
            print("%-34s | %s" % (f, s))
