"""Patch LEGOIndy2.exe so the CHINESE language slot uses the default font.

The language/font table sits in .rdata. Record layout (40 bytes):
    u32 languageId, ptr displayName, ptr lowerName, ptr fontName, f32 x6
For languageId 19 (CHINESE) the fontName pointer targets the string "font_chi",
for which the game ships no files. We repoint it at "font", whose files
(gui\\Font\\font_pc.fnt + gui\\Font\\font.txt) we replace inside GAME.dat.
"""
import struct
import sys

PTR_FONT_CHI = 0x904054      # file offset of the fontName pointer for CHINESE
VA_FONT = 0x00D03C48         # -> "font"
OLD = 0x00D03AA4             # -> "font_chi"


def patch(src, dst):
    data = bytearray(open(src, 'rb').read())
    cur = struct.unpack_from('<I', data, PTR_FONT_CHI)[0]
    if cur == VA_FONT:
        print('already patched')
    elif cur != OLD:
        raise SystemExit('unexpected value at %#x: %#x (expected %#x)' % (PTR_FONT_CHI, cur, OLD))
    else:
        struct.pack_into('<I', data, PTR_FONT_CHI, VA_FONT)
        print('patched %#x: %#x -> %#x  (font_chi -> font)' % (PTR_FONT_CHI, cur, VA_FONT))
    with open(dst, 'wb') as f:
        f.write(bytes(data))
    print('wrote %s (%d bytes)' % (dst, len(data)))


if __name__ == '__main__':
    patch(sys.argv[1], sys.argv[2])
