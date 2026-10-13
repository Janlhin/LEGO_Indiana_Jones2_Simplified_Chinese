"""Build a TT Games .FNT Chinese bitmap font (+ its grid .txt) from a template.

Strategy: keep the template's container layout byte-for-byte where possible
(same header shape, same middle shader chunk, same 64-byte tail) and only
replace
    * the glyph metric table   (x, y, advance) float32 triples @ 0x48)
    * the embedded DDS atlas   (DXT5 + regenerated mip chain)

Glyphs are rasterised with GDI32 (ctypes) - no third-party dependency.

Usage:
  python build_font.py --charset-file <file...> --out-dir <dir>
                       [--template <PS2_FONT_J_PC.FNT>] [--pitch 44]
                       [--atlas 1024] [--name font_chi] [--face "Microsoft YaHei UI"]
                       [--max-glyphs N] [--preview out.png]
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bc3 import encode_bc3, encode_bc3_block, parse_dds_header, find_dds, write_png
from gdi_font import render_charset
from ttfnt import FntFont, GLYPH_REC_START

ASCII_BASE = ''.join(chr(c) for c in range(0x20, 0x7F))


def build_charset(texts, extra=''):
    """Ordered unique charset: ASCII first, then other chars by first appearance."""
    seen = set()
    out = []
    for ch in ASCII_BASE + extra:
        if ch not in seen:
            seen.add(ch)
            out.append(ch)
    for t in texts:
        for ch in t:
            if ch not in seen:
                seen.add(ch)
                out.append(ch)
    return out


def make_grid_text(name, pitch, base, chars, cols):
    lines = ['name %s' % name, 'height %d' % pitch, 'base %d' % base, 'trans 0']
    for i in range(0, len(chars), cols):
        lines.append('chars "%s"' % ''.join(chars[i:i + cols]).replace('"', "'"))
    return '\r\n'.join(lines) + '\r\n'


def build(template, out_dir, name, texts, pitch=44, atlas=1024, base=0,
          face='Microsoft YaHei UI', bold=True, max_glyphs=None, preview=None,
          em=None):
    f = FntFont(template)
    tpl_mid_start = f.table_end
    tpl_dds_off = f.dds_offset
    mid_len = tpl_dds_off - tpl_mid_start
    mid_chunk = bytes(f.raw[tpl_mid_start:tpl_dds_off])
    tail = bytes(f.raw[f.size - 64:])

    cols = atlas // pitch
    capacity = cols * (atlas // pitch)

    chars = build_charset(texts)
    if max_glyphs and len(chars) > max_glyphs:
        chars = chars[:max_glyphs]
    used = set(''.join(texts))
    skipped = sorted(c for c in used if c not in chars)
    if len(chars) > capacity:
        raise SystemExit('charset %d exceeds atlas capacity %d (atlas=%d pitch=%d)'
                         % (len(chars), capacity, atlas, pitch))

    print("charset: %d chars (capacity %d)  skipped: %d %s" %
          (len(chars), capacity, len(skipped), ''.join(skipped)[:40]))

    # ---- rasterise, then pad the canvas out to the exact atlas size
    em = em or pitch
    RW, RH, alpha, advances, rows, meta = render_charset(chars, cols, pitch, face.encode(),
                                                         bold=bold, em=em)
    print("rasterised %dx%d (%d rows), ascent=%d descent=%d linebox=%d; padding to %d"
          % (RW, RH, rows, meta['ascent'], meta['descent'], meta['linebox'], atlas))

    W = H = atlas
    padded = bytearray(W * H)
    for y in range(RH):
        padded[y * W:y * W + RW] = alpha[y * RW:(y + 1) * RW]
    alpha = padded

    # ---- compose atlas RGBA (white glyphs, alpha = coverage)
    rgba = bytearray(W * H * 4)
    for i in range(W * H):
        a = alpha[i]
        o = i * 4
        rgba[o] = rgba[o + 1] = rgba[o + 2] = 255
        rgba[o + 3] = a

    # ---- glyph metrics: (x, y, advance)
    metrics = []
    for i, ch in enumerate(chars):
        col, row = i % cols, i // cols
        adv = advances[i]
        if adv <= 0:
            adv = pitch
        adv = min(adv, pitch)          # keep inside the cell grid
        metrics.append((float(col * pitch), float(row * pitch), float(adv)))
    N = len(metrics) + 3               # template uses chars+3
    while len(metrics) < N:
        metrics.append((0.0, 0.0, 0.0))

    # ---- assemble the FNT
    # layout: [64B header][8B sub-header @0x40][12B*N metrics][shader chunk][DDS][64B tail]
    # the metric records begin at absolute 0x48 (=72), so the 8 bytes at 0x40..0x47
    # belong to the header block and must be preserved from the template.
    head_ext = bytes(f.raw[64:72])
    header = bytearray(f.raw[:64])
    table = bytearray()
    for x, y, w in metrics:
        table += struct.pack('<3f', x, y, w)
    table_end = GLYPH_REC_START + len(table)

    chunk = bytearray(mid_chunk)
    struct.pack_into('<II', chunk, 0x20, atlas, atlas)      # texture dims

    dds = build_dds(rgba, W, H)
    body = bytes(header) + head_ext + bytes(table) + bytes(chunk) + dds + tail

    dds_off = GLYPH_REC_START + len(table) + len(chunk)
    # patch header fields
    h = bytearray(body[:64])
    struct.pack_into('<I', h, 0x00, len(body) - 64)
    struct.pack_into('<I', h, 0x08, dds_off - 8)
    struct.pack_into('<I', h, 0x18, table_end)
    struct.pack_into('<I', h, 0x1c, N)
    struct.pack_into('<I', h, 0x20, N + 2)
    struct.pack_into('<f', h, 0x24, float(pitch))
    struct.pack_into('<f', h, 0x28, float(base))
    body = bytes(h) + body[64:]

    os.makedirs(out_dir, exist_ok=True)
    fnt_path = os.path.join(out_dir, '%s_pc.fnt' % name)
    with open(fnt_path, 'wb') as fh:
        fh.write(body)

    grid = make_grid_text(name, pitch, base, chars, cols)
    grid_path = os.path.join(out_dir, '%s.txt' % name)
    with open(grid_path, 'wb') as fh:
        fh.write(b'\xff\xfe')
        fh.write(grid.encode('utf-16-le'))

    print("wrote %s (%d bytes)" % (fnt_path, len(body)))
    print("wrote %s (%d bytes, %d chars)" % (grid_path, len(grid) * 2 + 2, len(chars)))

    if preview:
        write_png(preview, W, H, rgba)
        print("preview -> %s" % preview)
    return fnt_path, grid_path


def build_dds(rgba, w, h):
    """DDS header + DXT5 main level + full mip chain."""
    mips = 1
    tw, th = w, h
    while tw > 1 or th > 1:
        tw, th = max(1, tw // 2), max(1, th // 2)
        mips += 1
    hdr = bytearray(128)
    hdr[0:4] = b'DDS '
    struct.pack_into('<I', hdr, 4, 124)
    struct.pack_into('<I', hdr, 8, 0x000A1007)
    struct.pack_into('<I', hdr, 12, h)
    struct.pack_into('<I', hdr, 16, w)
    lin = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 16
    struct.pack_into('<I', hdr, 20, lin)
    struct.pack_into('<I', hdr, 24, 0)
    struct.pack_into('<I', hdr, 28, mips)
    struct.pack_into('<I', hdr, 76, 32)          # dwPfSize
    struct.pack_into('<I', hdr, 80, 0x4)         # DDPF_FOURCC
    hdr[84:88] = b'DXT5'
    struct.pack_into('<I', hdr, 108, 0x1000)     # DDSCAPS_TEXTURE

    chain = bytearray()
    cur, cw, ch = rgba, w, h
    while True:
        chain += encode_bc3(cur, cw, ch)
        if cw == 1 and ch == 1:
            break
        nw, nh = max(1, cw // 2), max(1, ch // 2)
        nxt = bytearray(nw * nh * 4)
        for y in range(nh):
            for x in range(nw):
                r = g = b = a = 0
                for dy in range(2):
                    for dx in range(2):
                        sx = min(cw - 1, x * 2 + dx)
                        sy = min(ch - 1, y * 2 + dy)
                        o = (sy * cw + sx) * 4
                        r += cur[o]; g += cur[o + 1]; b += cur[o + 2]; a += cur[o + 3]
                o2 = (y * nw + x) * 4
                nxt[o2] = (r + 2) // 4; nxt[o2 + 1] = (g + 2) // 4
                nxt[o2 + 2] = (b + 2) // 4; nxt[o2 + 3] = (a + 2) // 4
        cur, cw, ch = nxt, nw, nh
    return bytes(hdr) + bytes(chain)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--name', default='font_chi')
    ap.add_argument('--charset-file', nargs='*', default=[])
    ap.add_argument('--pitch', type=int, default=44)
    ap.add_argument('--atlas', type=int, default=1024)
    ap.add_argument('--base', type=int, default=0)
    ap.add_argument('--face', default='Microsoft YaHei UI')
    ap.add_argument('--max-glyphs', type=int, default=0)
    ap.add_argument('--preview', default=None)
    a = ap.parse_args()

    texts = []
    for p in a.charset_file:
        d = open(p, 'rb').read()
        if d[:2] in (b'\xff\xfe', b'\xfe\xff'):
            texts.append(d.decode('utf-16'))
        else:
            try:
                texts.append(d.decode('utf-8-sig'))
            except Exception:
                texts.append(d.decode('latin-1'))
    build(a.template, a.out_dir, a.name, texts, pitch=a.pitch, atlas=a.atlas,
          base=a.base, face=a.face, max_glyphs=a.max_glyphs or None,
          preview=a.preview)


if __name__ == '__main__':
    main()
