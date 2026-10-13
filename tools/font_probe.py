"""Reverse-engineer the TT Games .FNT bitmap-font container.

Pairs a grid definition (<name>.txt) with its atlas (<name>_pc.fnt) and works out
the glyph record layout by cross-checking record counts against the character
count and by looking at metric plausibility.
"""
import sys, os, struct

# 游戏资源目录。仓库不含游戏素材，必须由使用者自行准备：
#   GAME_ROOT 指向含 GAME2/ 子目录的目录（默认 ./game_files）
#   GAME_TEXT_DIR 等价于 $GAME_ROOT/GAME2/stuff/text
GAME_ROOT = os.environ.get('GAME_ROOT') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'game_files')
GAME_TEXT_DIR = os.path.join(GAME_ROOT, 'GAME2', 'stuff', 'text')


TEXTDIR = GAME_TEXT_DIR


def parse_grid(path):
    """Parse a .txt grid file -> (header dict, ordered list of chars)."""
    hdr = {}
    chars = []
    with open(path, 'rb') as f:
        raw = f.read()
    txt = raw.decode('utf-8', 'replace')
    for line in txt.splitlines():
        line = line.rstrip('\r')
        if not line.strip():
            continue
        low = line.lstrip()
        if low.startswith('chars'):
            rest = line[line.index('chars') + 5:].strip()
            if rest.startswith('"'):
                rest = rest[1:]
            if rest.endswith('"'):
                rest = rest[:-1]
            for ch in rest:
                chars.append(ch)
        else:
            parts = low.split()
            if len(parts) >= 2 and parts[0] in ('name', 'height', 'base', 'trans'):
                hdr[parts[0]] = parts[1]
    return hdr, chars


def analyze(grid_name, fnt_name):
    gp = os.path.join(TEXTDIR, grid_name)
    fp = os.path.join(TEXTDIR, fnt_name)
    hdr, chars = parse_grid(gp)
    size = os.path.getsize(fp)
    data = open(fp, 'rb').read()

    print("=" * 86)
    print("grid=%s (%d chars)  header=%s" % (grid_name, len(chars), hdr))
    print("fnt =%s  size=%d" % (fnt_name, size))
    fields = struct.unpack_from('<8I', data, 0)
    print("  u32@0x00..0x1c: " + ' '.join('%d' % v for v in fields))
    print("  u32@0x40,0x44,0x48: %d %d %d" % struct.unpack_from('<3I', data, 0x40))
    print("  f32@0x24..0x2c: %s" % [struct.unpack_from('<f', data, o)[0] for o in (0x24, 0x28, 0x2c)])
    payload = fields[0]
    print("  payload=size-64 ? %s   (size-64=%d)" % (payload == size - 64, size - 64))

    table_end = fields[6]          # 0x18
    table_start = 64
    span = table_end - table_start
    print("  glyph table span = %#x - 64 = %d bytes" % (table_end, span))
    for rec in (8, 12, 16, 20, 24):
        if span % rec == 0:
            print("     record %2d bytes -> %d records  (grid chars = %d) %s"
                  % (rec, span // rec, len(chars),
                     'MATCH' if span // rec == len(chars) else ''))

    print("  --- 前 8 条 16 字节记录，按 4 个 float 解读 ---")
    for i in range(8):
        o = table_start + i * 16
        vals = struct.unpack_from('<4f', data, o)
        ints = struct.unpack_from('<4I', data, o)
        ch = chars[i] if i < len(chars) else '?'
        print("     #%d  %-34s  u32=%s   char=%r" % (
            i,
            ' '.join('%9.2f' % v for v in vals),
            ' '.join('%-9d' % v for v in ints), ch))

    print("  --- 前 8 条 12 字节记录，按 (float,float,float) 解读 ---")
    for i in range(8):
        o = table_start + i * 12
        vals = struct.unpack_from('<3f', data, o)
        ch = chars[i] if i < len(chars) else '?'
        print("     #%d  %-34s  char=%r" % (i, ' '.join('%9.2f' % v for v in vals), ch))

    print("  --- 数据区起始 %#x 处 32 字节 ---" % table_end)
    d = data[table_end:table_end + 32]
    print("     " + d.hex(' '))
    print("  字节尾部 32 字节:")
    print("     " + data[-32:].hex(' '))


if __name__ == '__main__':
    pairs = [
        ('PC_font.txt', 'PC_FONT_PC.FNT'),
        ('font.txt', 'font_pc.fnt'),
        ('PS2_font_j.txt', 'PS2_FONT_J_PC.FNT'),
        ('PS2_font.txt', 'PS2_FONT_PC.FNT'),
        ('font3.txt', 'font3_pc.fnt'),
    ]
    for g, f in pairs:
        if os.path.exists(os.path.join(TEXTDIR, g)) and os.path.exists(os.path.join(TEXTDIR, f)):
            analyze(g, f)
        else:
            print("missing pair:", g, f)
