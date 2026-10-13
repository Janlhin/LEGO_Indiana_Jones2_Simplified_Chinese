"""TT Games NXG 引擎 .FT2 (NFNT) 字体 — 完整解析器（大端）。

结构（参考 lego-tt-nxg-formats/NFNT.md，Indy2 实测校准）：
  头部:
    size(u32) unk(u32=1) "TNFN"(4cc) type(u32) version(u32)
    flags(u16) size2(u32) numChars(u32) unicodeTableSize(u32)
    height(f32) baseline(f32) spaceWidth(f32) sendid(u32) icgap(f32)
  posTable:  size(u32) + size 条 {x:f32, y:f32, w:f32}
  charsTable: size(u32) + size 条 {codepoint:u16, index:u16}  (末尾 ffff 结束)
  kerning:   size(u32) + size 条 {charA:u16, charB:u16, gap:f32}
  texture:   DDS
"""
import struct

BE = '>'


def u32(b, o):
    return struct.unpack_from(BE + 'I', b, o)[0]


def u16(b, o):
    return struct.unpack_from(BE + 'H', b, o)[0]


def f32(b, o):
    return struct.unpack_from(BE + 'f', b, o)[0]


class FT2:
    def __init__(self, path_or_bytes):
        self.raw = bytes(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) \
            else open(path_or_bytes, 'rb').read()
        self.parse()

    def parse(self):
        b = self.raw
        assert b[8:12] == b'TNFN', 'not FT2'
        self.size = u32(b, 0)
        self.unk = u32(b, 4)
        self.type = u32(b, 12)
        self.version = u32(b, 16)
        self.flags = u16(b, 20)
        self.size2 = u32(b, 22)
        self.num_chars = u32(b, 26)
        self.unicode_table_size = u32(b, 30)
        self.height = f32(b, 34)
        self.baseline = f32(b, 38)
        self.space_width = f32(b, 42)
        self.sendid = u32(b, 46)
        self.icgap = f32(b, 50)

        # posTable 从 0x36 开始（0x2e sendid + 0x32 icgap）
        off = 0x36
        self.pos_size = u32(b, off)
        off += 4
        self.positions = []
        for _ in range(self.pos_size):
            x = f32(b, off); y = f32(b, off + 4); w = f32(b, off + 8)
            self.positions.append((x, y, w))
            off += 12

        # charsTable
        self.chars_size = u32(b, off)
        off += 4
        self.chars = []
        for _ in range(self.chars_size):
            cp = u16(b, off); ix = u16(b, off + 2)
            self.chars.append((cp, ix))
            off += 4

        # kerning
        self.kerning_size = u32(b, off)
        off += 4
        self.kerning = []
        for _ in range(self.kerning_size):
            a = u16(b, off); bb = u16(b, off + 2); gap = f32(b, off + 4)
            self.kerning.append((a, bb, gap))
            off += 8

        self.dds_off = b.find(b'DDS ')
        self.table_end = off

    def info(self):
        print('size=%d unk=%d type=%d ver=%d flags=%d size2=%d' %
              (self.size, self.unk, self.type, self.version, self.flags, self.size2))
        print('numChars=%d unicodeTableSize=%d' % (self.num_chars, self.unicode_table_size))
        print('height=%g baseline=%g spaceWidth=%g' % (self.height, self.baseline, self.space_width))
        print('posTable: %d 条, charsTable: %d 条, kerning: %d 条' %
              (self.pos_size, self.chars_size, self.kerning_size))
        print('表结束@0x%x, DDS@0x%x, 差=%d 字节' % (self.table_end, self.dds_off, self.dds_off - self.table_end))
        # 前 8 个字符
        print('  字符前 8: %s' % ['%04x->%d' % c for c in self.chars[:8]])
        print('  字符后 4: %s' % ['%04x->%d' % c for c in self.chars[-4:]])
        # 位置前 3 条
        print('  位置前 3: %s' % ['(%.1f,%.1f,%.1f)' % p for p in self.positions[:3]])


if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        print('===== %s =====' % p)
        FT2(p).info()
