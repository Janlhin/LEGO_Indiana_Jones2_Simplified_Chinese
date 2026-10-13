"""Recover the glyph packing grid of a .FNT atlas by alpha projection."""
import sys, os

# 游戏资源目录。仓库不含游戏素材，必须由使用者自行准备：
#   GAME_ROOT 指向含 GAME2/ 子目录的目录（默认 ./game_files）
#   GAME_TEXT_DIR 等价于 $GAME_ROOT/GAME2/stuff/text
GAME_ROOT = os.environ.get('GAME_ROOT') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'game_files')
GAME_TEXT_DIR = os.path.join(GAME_ROOT, 'GAME2', 'stuff', 'text')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bc3 import find_dds, parse_dds_header, decode_bc3, write_png

base = os.path.normpath(GAME_TEXT_DIR)
outdir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       '..', '03_atlas'))

fn = sys.argv[1] if len(sys.argv) > 1 else 'PS2_FONT_J_PC.FNT'
crop_h = int(sys.argv[2]) if len(sys.argv) > 2 else 320
raw = open(os.path.join(base, fn), 'rb').read()
off = find_dds(raw)
info = parse_dds_header(raw, off)
w, h = info['width'], info['height']
rgba = decode_bc3(raw, off + 128, w, h)
print("atlas %s  %dx%d" % (fn, w, h))

ALPHA_T = 8


def bands(vals, thresh, minlen=1):
    out = []
    start = None
    for i, v in enumerate(vals):
        if v > thresh:
            if start is None:
                start = i
        else:
            if start is not None and i - start >= minlen:
                out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(vals)))
    return out


rowsum = [0] * h
for y in range(h):
    s = 0
    base_o = y * w * 4
    for x in range(w):
        s += rgba[base_o + x * 4 + 3]
    rowsum[y] = s

print("\n--- 行投影（非零连续区段）---")
rb = bands(rowsum, 0)
print("  行带数: %d" % len(rb))
for i, (a, b) in enumerate(rb[:40]):
    print("    band %2d: y=%4d..%4d  height=%d" % (i, a, b, b - a))

print("\n--- 每个行带内的字形列位置 ---")
total_glyphs = 0
for i, (a, b) in enumerate(rb):
    colsum = [0] * w
    for y in range(a, b):
        o = y * w * 4
        for x in range(w):
            colsum[x] += rgba[o + x * 4 + 3]
    cb = bands(colsum, 0)
    widths = [e - s for s, e in cb]
    total_glyphs += len(cb)
    print("    row %2d (h=%d): %3d glyphs  x0=%s  widths[:14]=%s"
          % (i, b - a, len(cb), [s for s, e in cb[:6]], widths[:14]))
print("\n总字形数（按投影）= %d" % total_glyphs)

# crop for visual confirmation
cw = min(w, 1024)
crop = bytearray(cw * crop_h * 4)
for y in range(crop_h):
    for x in range(cw):
        so = (y * w + x) * 4
        do = (y * cw + x) * 4
        crop[do:do + 4] = rgba[so:so + 4]
write_png(os.path.join(outdir, fn + '.crop.png'), cw, crop_h, crop)
print("crop -> %s" % os.path.join(outdir, fn + '.crop.png'))
