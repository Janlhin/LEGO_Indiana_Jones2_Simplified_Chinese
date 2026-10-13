"""Extract the embedded DDS atlas from a .FNT font and export it as PNG."""
import sys, os

# 游戏资源目录。仓库不含游戏素材，必须由使用者自行准备：
#   GAME_ROOT 指向含 GAME2/ 子目录的目录（默认 ./game_files）
#   GAME_TEXT_DIR 等价于 $GAME_ROOT/GAME2/stuff/text
GAME_ROOT = os.environ.get('GAME_ROOT') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'game_files')
GAME_TEXT_DIR = os.path.join(GAME_ROOT, 'GAME2', 'stuff', 'text')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bc3 import (find_dds, parse_dds_header, dds_level_size, decode_bc3,
                 _fourcc_str, write_png)

base = os.path.normpath(GAME_TEXT_DIR)
outdir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       '..', '03_atlas'))
os.makedirs(outdir, exist_ok=True)

for fn in sys.argv[1:] or ['font_pc.fnt', 'PC_FONT_PC.FNT', 'PS2_FONT_J_PC.FNT']:
    p = os.path.join(base, fn)
    raw = open(p, 'rb').read()
    off = find_dds(raw)
    info = parse_dds_header(raw, off)
    w, h = info['width'], info['height']
    sx = 4          # downsample factor for the preview
    face = _fourcc_str(info['fourcc'])
    print("%-22s dds@%#x  %dx%d fourcc=%s mips=%d  payload=%d  tail=%d"
          % (fn, off, w, h, face.decode('latin1'), info['mips'],
             len(raw) - off - 128, len(raw) - off - 128 - dds_level_size(info, w, h)))

    rgba = decode_bc3(raw, off + 128, w, h)

    # full-size png
    out_png = os.path.join(outdir, fn + '.png')
    write_png(out_png, w, h, rgba)

    # downsampled preview so it can be eyeballed quickly
    pw, ph = w // sx, h // sx
    prev = bytearray(pw * ph * 4)
    for y in range(ph):
        for x in range(pw):
            # take the max alpha in the block, average colour
            mr = mg = mb = 0
            ma = 0
            for dy in range(sx):
                for dx in range(sx):
                    o = ((y * sx + dy) * w + (x * sx + dx)) * 4
                    mr = max(mr, rgba[o]); mg = max(mg, rgba[o + 1])
                    mb = max(mb, rgba[o + 2]); ma = max(ma, rgba[o + 3])
            o = (y * pw + x) * 4
            prev[o] = mr; prev[o + 1] = mg; prev[o + 2] = mb; prev[o + 3] = ma
    out_prev = os.path.join(outdir, fn + '.preview.png')
    write_png(out_prev, pw, ph, prev)
    print("    -> %s  (+ %s)" % (out_png, out_prev))
