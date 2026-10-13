"""Resolve the .FNT glyph-metric record format using projection-derived truth.

We already know the packing from alpha projection:
  - PS2_FONT_J_PC.FNT : 23 rows, pitch 44, row 0 glyph x-starts = [1,33,61,90,...]
This script searches (table start, record size, field order) so that the parsed
records' row-0 entries reproduce those x positions.
"""
import sys, os, struct

# 游戏资源目录。仓库不含游戏素材，必须由使用者自行准备：
#   GAME_ROOT 指向含 GAME2/ 子目录的目录（默认 ./game_files）
#   GAME_TEXT_DIR 等价于 $GAME_ROOT/GAME2/stuff/text
GAME_ROOT = os.environ.get('GAME_ROOT') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'game_files')
GAME_TEXT_DIR = os.path.join(GAME_ROOT, 'GAME2', 'stuff', 'text')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bc3 import find_dds, parse_dds_header, decode_bc3

base = os.path.normpath(GAME_TEXT_DIR)


def projection(rgba, w, h):
    rowsum = [0] * h
    for y in range(h):
        o = y * w * 4
        s = 0
        for x in range(w):
            s += rgba[o + x * 4 + 3]
        rowsum[y] = s
    bands, start = [], None
    for i, v in enumerate(rowsum):
        if v:
            if start is None:
                start = i
        else:
            if start is not None:
                bands.append((start, i)); start = None
    if start is not None:
        bands.append((start, h))
    return bands


def row_xstarts(rgba, w, a, b):
    colsum = [0] * w
    for y in range(a, b):
        o = y * w * 4
        for x in range(w):
            colsum[x] += rgba[o + x * 4 + 3]
    out, start = [], None
    for i, v in enumerate(colsum):
        if v:
            if start is None:
                start = i
        else:
            if start is not None:
                out.append(start); start = None
    if start is not None:
        out.append(start)
    return out


fn = sys.argv[1] if len(sys.argv) > 1 else 'PS2_FONT_J_PC.FNT'
raw = open(os.path.join(base, fn), 'rb').read()
off = find_dds(raw)
info = parse_dds_header(raw, off)
w, h = info['width'], info['height']
rgba = decode_bc3(raw, off + 128, w, h)
table_end = struct.unpack_from('<I', raw, 0x18)[0]

bands = projection(rgba, w, h)
truth = row_xstarts(rgba, w, *bands[0])
print("%s  %dx%d  table_end=%#x  rows=%d" % (fn, w, h, table_end, len(bands)))
print("row0 y-band = %s   x-starts = %s" % (bands[0], truth[:14]))

print("\n--- 候选度量表布局 (要求 y==0 的记录按 x 排序后匹配投影) ---")
found = []
for rsize in (8, 12, 16, 20, 24):
    nf = rsize // 4
    for start in range(64, 512, 4):
        if (table_end - start) % rsize:
            continue
        n = (table_end - start) // rsize
        for perm in [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]:
            if max(perm) >= nf:
                continue
            recs = []
            ok = True
            for i in range(n):
                f = struct.unpack_from('<%df' % nf, raw, start + i * rsize)
                x, y, wd = f[perm[0]], f[perm[1]], f[perm[2]]
                if not (0 <= x <= w and 0 <= y <= h and 0 <= wd <= 200):
                    ok = False; break
                recs.append((x, y, wd))
            if not ok:
                continue
            ys = set(round(r[1], 2) for r in recs)
            row0 = sorted(r[0] for r in recs if abs(r[1]) < 0.001)
            if len(row0) < 5:
                continue
            score = sum(1 for a, b in zip(row0, truth) if abs(a - b) <= 1)
            if score >= 4:
                found.append((score, rsize, start, perm, n, len(ys), row0[:14]))

found.sort(key=lambda t: -t[0])
for score, rsize, start, perm, n, nrows, row0 in found[:12]:
    print("  score=%2d recsize=%-2d start=%#05x perm=%s recs=%-4d distinctY=%-3d"
          % (score, rsize, start, perm, n, nrows))
    print("        row0 x = %s" % row0)
if not found:
    print("  (无候选)")
