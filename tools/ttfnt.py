"""Reader/writer for TT Games .FNT bitmap fonts.

Layout established empirically (documented in docs/FNT-format.md):

  0x00  u32  payloadSize        (= fileSize - 64)
  0x04  u32  12
  0x08  u32  ddsOffset - 8
  0x0c  u32  0
  0x10  u32  0
  0x14  u32  1
  0x18  u32  glyphTableEnd
  0x1c  u32  N1
  0x20  u32  N2
  0x24  f32  lineHeight        (grid "height")
  0x28  f32  base              (grid "base")
  0x2c  f32  12.0
  0x30..0x3f  zero
  0x40  u32  0
  0x44  u32  28
  0x48  u32  (middle-chunk value)
  0x4c  u32  checksum
  0x48  ->  glyph metric records, 12 bytes each = (x, y, advanceWidth) float32
  glyphTableEnd        -> middle chunk (contains an HLSL string)
  ddsOffset            -> embedded DDS (DXT5, full mip chain)
  fileSize - 64        -> 64-byte tail
"""
import struct

# 游戏资源目录。仓库不含游戏素材，必须由使用者自行准备：
#   GAME_ROOT 指向含 GAME2/ 子目录的目录（默认 ./game_files）
#   GAME_TEXT_DIR 等价于 $GAME_ROOT/GAME2/stuff/text
GAME_ROOT = os.environ.get('GAME_ROOT') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'game_files')
GAME_TEXT_DIR = os.path.join(GAME_ROOT, 'GAME2', 'stuff', 'text')

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bc3 import (parse_dds_header, dds_level_size, decode_bc3, encode_bc3,
                 find_dds, _fourcc_str)

GLYPH_REC_START = 72
GLYPH_REC_SIZE = 12
SENTINEL_ABS = 1e7   # |value| beyond this marks an unused metric slot


class FntFont:
    def __init__(self, path):
        self.path = path
        self.raw = bytearray(open(path, 'rb').read())
        self.size = len(self.raw)
        h = self.raw
        self.payload_size = struct.unpack_from('<I', h, 0x00)[0]
        self.f04 = struct.unpack_from('<I', h, 0x04)[0]
        self.f08 = struct.unpack_from('<I', h, 0x08)[0]
        self.table_end = struct.unpack_from('<I', h, 0x18)[0]
        self.n1 = struct.unpack_from('<I', h, 0x1c)[0]
        self.n2 = struct.unpack_from('<I', h, 0x20)[0]
        self.line_height = struct.unpack_from('<f', h, 0x24)[0]
        self.base = struct.unpack_from('<f', h, 0x28)[0]
        self.mid_chunk_val = struct.unpack_from('<I', h, 0x48)[0]
        self.checksum = struct.unpack_from('<I', h, 0x4c)[0]
        self.dds_offset = find_dds(bytes(h))
        self.dds = parse_dds_header(bytes(h), self.dds_offset)
        self.width = self.dds['width']
        self.height = self.dds['height']
        self.mips = self.dds['mips']
        self._read_metrics()

    # ----------------------------------------------------------------- metrics
    def _read_metrics(self):
        self.metrics = []
        end = self.table_end
        off = GLYPH_REC_START
        while off + GLYPH_REC_SIZE <= end:
            x, y, w = struct.unpack_from('<3f', self.raw, off)
            self.metrics.append((x, y, w))
            off += GLYPH_REC_SIZE
        self.metrics_tail_bytes = end - off

    def valid_metrics(self):
        out = []
        for i, (x, y, w) in enumerate(self.metrics):
            if abs(x) > SENTINEL_ABS or abs(y) > SENTINEL_ABS or abs(w) > SENTINEL_ABS:
                continue
            if x < 0 or y < 0 or w <= 0 or x > self.width or y > self.height:
                continue
            out.append(i)
        return out

    def row_index(self, y):
        pitch = self.line_height
        return int(round(y / pitch))

    # ----------------------------------------------------------------- texture
    def decode_atlas(self):
        return decode_bc3(bytes(self.raw), self.dds_offset + 128, self.width, self.height)

    def reencode_atlas(self, rgba, regenerate_mips=True):
        """Re-encode the main level (and mip chain) back into the file in place."""
        if (self.width != self.dds['width'] or self.height != self.dds['height']):
            raise ValueError('atlas size must stay constant for in-place patching')
        main = encode_bc3(rgba, self.width, self.height)
        chain = main
        if regenerate_mips:
            w, h = self.width, self.height
            cur = rgba
            while w > 1 or h > 1:
                nw, nh = max(1, w // 2), max(1, h // 2)
                nxt = bytearray(nw * nh * 4)
                for y in range(nh):
                    for x in range(nw):
                        r = g = b = a = 0
                        for dy in range(2):
                            for dx in range(2):
                                sx = min(w - 1, x * 2 + dx)
                                sy = min(h - 1, y * 2 + dy)
                                o = (sy * w + sx) * 4
                                r += cur[o]; g += cur[o + 1]
                                b += cur[o + 2]; a += cur[o + 3]
                        o2 = (y * nw + x) * 4
                        nxt[o2] = (r + 2) // 4; nxt[o2 + 1] = (g + 2) // 4
                        nxt[o2 + 2] = (b + 2) // 4; nxt[o2 + 3] = (a + 2) // 4
                cur, w, h = nxt, nw, nh
                chain += encode_bc3(cur, w, h)
        need = self.dds_offset + 128 + len(chain)
        if need > self.size:
            raise ValueError('new texture chain (%d) exceeds file size (%d)' % (need, self.size))
        self.raw[self.dds_offset + 128:need] = chain
        # keep the tail bytes (checksum block) intact
        return len(chain)

    def save(self, out_path):
        with open(out_path, 'wb') as f:
            f.write(bytes(self.raw))


def summarize(path):
    f = FntFont(path)
    valid = f.valid_metrics()
    print("=" * 88)
    print(os.path.basename(path))
    print("  size=%d payload=%d table_end=%#x N1=%d N2=%d" %
          (f.size, f.payload_size, f.table_end, f.n1, f.n2))
    print("  lineHeight=%.1f base=%.1f f08=%#x dds@%#x %dx%d mips=%d" %
          (f.line_height, f.base, f.f08, f.dds_offset, f.width, f.height, f.mips))
    print("  metric records=%d  valid=%d  trailing=%d bytes" %
          (len(f.metrics), len(valid), f.metrics_tail_bytes))
    rows = {}
    for i in valid:
        x, y, w = f.metrics[i]
        rows.setdefault(round(y / f.line_height), []).append((x, w))
    print("  rows=%d  glyphs/row=%s" % (len(rows), [len(rows[k]) for k in sorted(rows)]))
    print("  first 6 records: %s" % ['%.0f,%.0f,%.0f' % m for m in f.metrics[:6]])
    print("  first 6 valid  : %s" % ['#%d (x=%.0f y=%.0f w=%.0f)' % ((i,) + f.metrics[i]) for i in valid[:6]])
    return f


if __name__ == '__main__':
    base = os.path.normpath(GAME_TEXT_DIR)
    for fn in sys.argv[1:] or ['PS2_FONT_J_PC.FNT', 'font_pc.fnt', 'PC_FONT_PC.FNT']:
        summarize(os.path.join(base, fn))
