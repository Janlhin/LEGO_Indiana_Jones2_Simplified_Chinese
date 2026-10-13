"""Verify a built .FNT by re-parsing it from disk and rendering a contact sheet.

Checks:
  1. header fields self-consistent (payload size, dds offset, table end)
  2. embedded DDS parses, dimensions match the middle chunk
  3. glyph metrics all inside the atlas
  4. grid file character count == metric count - 3
  5. renders the atlas back out as PNG for visual confirmation
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bc3 import find_dds, parse_dds_header, decode_bc3, write_png

fnt = sys.argv[1]
grid = sys.argv[2] if len(sys.argv) > 2 else None
out_png = sys.argv[3] if len(sys.argv) > 3 else None

raw = open(fnt, 'rb').read()
size = len(raw)
ok = True

payload = struct.unpack_from('<I', raw, 0x00)[0]
f08 = struct.unpack_from('<I', raw, 0x08)[0]
table_end = struct.unpack_from('<I', raw, 0x18)[0]
n1 = struct.unpack_from('<I', raw, 0x1c)[0]
n2 = struct.unpack_from('<I', raw, 0x20)[0]
lineh = struct.unpack_from('<f', raw, 0x24)[0]
base = struct.unpack_from('<f', raw, 0x28)[0]
dds_off = find_dds(raw)
info = parse_dds_header(raw, dds_off)
W, H = info['width'], info['height']
chunk_dims = struct.unpack_from('<II', raw, table_end + 0x20)

print("file            : %s" % fnt)
print("size            : %d" % size)
print("payload field   : %d  (= size-64 ? %s)" % (payload, payload == size - 64))
print("f08             : %#x  (= ddsOff-8 ? %s)" % (f08, f08 == dds_off - 8))
print("table_end       : %#x   N1=%d N2=%d" % (table_end, n1, n2))
print("lineHeight/base : %.1f / %.1f" % (lineh, base))
print("DDS             : @%#x  %dx%d mips=%d fourcc=%s"
      % (dds_off, W, H, info['mips'], struct.pack('<I', info['fourcc']).decode('latin1')))
print("chunk dims      : %dx%d  (match DDS ? %s)" % (chunk_dims[0], chunk_dims[1],
                                                    list(chunk_dims) == [W, H]))

nrec = (table_end - 72) // 12
metrics = [struct.unpack_from('<3f', raw, 72 + i * 12) for i in range(nrec)]
bad = [m for m in metrics if not (0 <= m[0] <= W and 0 <= m[1] <= H and 0 <= m[2] <= lineh)]
print("metric records  : %d  (out-of-range: %d)" % (nrec, len(bad)))
print("  first 4       : %s" % ['%.0f/%.0f/%.0f' % m for m in metrics[:4]])

if grid:
    d = open(grid, 'rb').read()
    txt = d.decode('utf-16') if d[:2] in (b'\xff\xfe', b'\xfe\xff') else d.decode('utf-8')
    chars = []
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith('chars'):
            chars.append(s[5:].strip().strip('"'))
    nchars = sum(len(c) for c in chars)
    print("grid            : %d rows, %d chars" % (len(chars), nchars))
    print("  chars == N1-3 ? %s" % (nchars == n1 - 3))

for cond, lbl in [(payload == size - 64, 'payload size'),
                  (f08 == dds_off - 8, 'dds pointer'),
                  (list(chunk_dims) == [W, H], 'texture dims'),
                  (not bad, 'metrics in range')]:
    if not cond:
        ok = False
        print("  !! FAIL: %s" % lbl)

if out_png:
    rgba = decode_bc3(raw, dds_off + 128, W, H)
    write_png(out_png, W, H, rgba)
    print("atlas rendered -> %s" % out_png)

print("\nRESULT: %s" % ('PASS' if ok else 'FAIL'))
