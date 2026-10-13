"""Locate and parse the embedded DDS texture inside a TT Games .FNT font file."""
import sys, os, struct

# 游戏资源目录。仓库不含游戏素材，必须由使用者自行准备：
#   GAME_ROOT 指向含 GAME2/ 子目录的目录（默认 ./game_files）
#   GAME_TEXT_DIR 等价于 $GAME_ROOT/GAME2/stuff/text
GAME_ROOT = os.environ.get('GAME_ROOT') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'game_files')
GAME_TEXT_DIR = os.path.join(GAME_ROOT, 'GAME2', 'stuff', 'text')


DDS_FOURCC = {
    b'DXT1': 'DXT1 (BC1)',
    b'DXT2': 'DXT2',
    b'DXT3': 'DXT3 (BC2)',
    b'DXT4': 'DXT4',
    b'DXT5': 'DXT5 (BC3)',
    b'ATI1': 'BC4',
    b'BC5U': 'BC5',
    b'\x00\x00\x00\x00': 'uncompressed (RGB/A masks)',
    b'DX10': 'DX10 extended header',
}


def parse(path):
    d = open(path, 'rb').read()
    i = d.find(b'DDS ')
    print("=" * 84)
    print("file: %s  (size %d)" % (path, len(d)))
    if i < 0:
        print("  no DDS found")
        return None
    print("  DDS at file offset %#x (%d)" % (i, i))
    h = d[i:i + 128]
    magic = h[0:4]
    dwSize, dwFlags, height, width = struct.unpack_from('<IIII', h, 4)
    pitch, depth, mips = struct.unpack_from('<III', h, 20)
    pf_size, pf_flags, fourcc, rgbbits = struct.unpack_from('<IIII', h, 76)
    rmask, gmask, bmask, amask = struct.unpack_from('<IIII', h, 92)
    caps, caps2 = struct.unpack_from('<II', h, 108)
    print("    magic=%r dwSize=%d flags=%#x" % (magic, dwSize, dwFlags))
    print("    width=%d height=%d pitchOrLinear=%d depth=%d mips=%d"
          % (width, height, pitch, depth, mips))
    print("    pfFlags=%#x fourCC=%r (%s) rgbBits=%d"
          % (pf_flags, fourcc, DDS_FOURCC.get(fourcc, '?'), rgbbits))
    print("    masks R=%#x G=%#x B=%#x A=%#x  caps=%#x caps2=%#x"
          % (rmask, gmask, bmask, amask, caps, caps2))

    # expected payload size
    def bc_size(w, h, block):
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * block
    if fourcc in (b'DXT1',):
        exp = bc_size(width, height, 8)
    elif fourcc in (b'DXT3', b'DXT5'):
        exp = bc_size(width, height, 16)
    elif fourcc == b'\x00\x00\x00\x00':
        exp = width * height * (rgbbits // 8)
    else:
        exp = None
    avail = len(d) - (i + 128)
    print("    payload available = %d bytes; expected main level = %s" % (avail, exp))
    if exp:
        print("    -> leftover after main level: %d" % (avail - exp))
    print("    DDS ends at %#x ; file size %#x" % (i + 128 + (exp or 0), len(d)))
    return {'offset': i, 'width': width, 'height': height, 'fourcc': fourcc}


if __name__ == '__main__':
    base = os.path.normpath(GAME_TEXT_DIR)
    for f in ['font_pc.fnt', 'PC_FONT_PC.FNT', 'PS2_FONT_J_PC.FNT', 'PS2_FONT_PC.FNT',
              'font3_pc.fnt', 'font2_pc.fnt', 'font_russian_pc.fnt']:
        p = os.path.join(base, f)
        if os.path.exists(p):
            parse(p)
