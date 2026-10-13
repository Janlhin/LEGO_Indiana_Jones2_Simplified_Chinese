"""Pin down the .FNT glyph-metric layout by cross-validating against the grid .txt.

Grid files are UTF-16LE (BOM FF FE).
Hypothesis: glyph table is an array of 3 float32 per glyph = (advance/width, x, y).
Validation: grouping glyphs by their Y field must reproduce the grid's row-length list.
"""
import sys, os, struct, collections, itertools

# 游戏资源目录。仓库不含游戏素材，必须由使用者自行准备：
#   GAME_ROOT 指向含 GAME2/ 子目录的目录（默认 ./game_files）
#   GAME_TEXT_DIR 等价于 $GAME_ROOT/GAME2/stuff/text
GAME_ROOT = os.environ.get('GAME_ROOT') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'game_files')
GAME_TEXT_DIR = os.path.join(GAME_ROOT, 'GAME2', 'stuff', 'text')


TEXTDIR = os.path.normpath(GAME_TEXT_DIR)


def read_text_any(path):
    d = open(path, 'rb').read()
    if d[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return d.decode('utf-16')
    try:
        return d.decode('utf-8')
    except Exception:
        return d.decode('latin-1')


def parse_grid(path):
    hdr, rows = {}, []
    for line in read_text_any(path).splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('chars'):
            rows.append(s[5:].strip().strip('"'))
        else:
            p = s.split()
            if len(p) >= 2 and p[0] in ('name', 'height', 'base', 'trans'):
                hdr[p[0]] = p[1]
    return hdr, rows


def analyse(grid_name, fnt_name):
    gp, fp = os.path.join(TEXTDIR, grid_name), os.path.join(TEXTDIR, fnt_name)
    hdr, rows = parse_grid(gp)
    rowlens = [len(r) for r in rows]
    total = sum(rowlens)
    data = open(fp, 'rb').read()
    table_end = struct.unpack_from('<I', data, 0x18)[0]

    print("=" * 96)
    print("GRID %-20s rows=%-3d chars=%-4d rowlens=%s" % (grid_name, len(rows), total, rowlens))
    print("     hdr=%s" % hdr)
    print("FNT  %-20s size=%-8d table_end=%#x  N1=%d N2=%d"
          % (fnt_name, len(data), table_end,
             struct.unpack_from('<I', data, 0x1c)[0],
             struct.unpack_from('<I', data, 0x20)[0]))

    hits = []
    for rsize in (8, 12, 16, 20, 24):
        nf = rsize // 4
        for start in range(64, 320):
            span = table_end - start
            if span <= 0 or span % rsize:
                continue
            n = span // rsize
            if not (total <= n <= total + 32):
                continue
            recs = []
            for i in range(n):
                recs.append(struct.unpack_from('<%df' % nf, data, start + i * rsize))
            # try every field as the "y" (row) field, and the remaining fields as (w,x)
            for yidx in range(nf):
                ys = [round(r[yidx], 2) for r in recs]
                if not all(0 <= v < 8192 for v in ys):
                    continue
                byy = collections.OrderedDict()
                for k, y in enumerate(ys):
                    byy.setdefault(y, []).append(k)
                # ignore leading records that are padding
                for shift in range(0, 6):
                    pred = [len(v) for v in list(byy.values())[shift:]]
                    if pred[:len(rowlens)] == rowlens and len(pred) == len(rowlens):
                        hits.append((shift, rsize, start, yidx, n, sorted(byy.keys())))
    if not hits:
        print("  !! 无匹配布局")
    for shift, rsize, start, yidx, n, ykeys in hits:
        print("  >> recsize=%-2d start=%#05x records=%-4d yFieldIdx=%d padSkip=%d"
              % (rsize, start, n, yidx, shift))
        print("     Y 取值集合: %s" % ykeys)
    return hits


if __name__ == '__main__':
    pairs = [('PS2_font_j.txt', 'PS2_FONT_J_PC.FNT'),
             ('font.txt', 'font_pc.fnt'),
             ('PC_font.txt', 'PC_FONT_PC.FNT'),
             ('PS2_font.txt', 'PS2_FONT_PC.FNT'),
             ('font3.txt', 'font3_pc.fnt'),
             ('font2.txt', 'font2_pc.fnt'),
             ('font_russian.txt', 'font_russian_pc.fnt'),
             ('font1024.txt', 'font1024_pc.fnt')]
    for g, f in pairs:
        if os.path.exists(os.path.join(TEXTDIR, g)) and os.path.exists(os.path.join(TEXTDIR, f)):
            analyse(g, f)
        else:
            print("MISSING PAIR", g, f)
