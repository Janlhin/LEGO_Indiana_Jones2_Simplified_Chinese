"""Dump and interpret the header of a TT Games .DAT archive."""
import sys, struct

path = sys.argv[1]
n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x400
with open(path, 'rb') as f:
    head = f.read(n)
    f.seek(0, 2)
    size = f.tell()
    f.seek(max(0, size - 64))
    tail = f.read()

print("=" * 78)
print("file:", path)
print("size: %d (%.2f MB)" % (size, size / 1048576))
print("-" * 78)
for off in range(0, min(n, 0x200), 16):
    chunk = head[off:off+16]
    hexs = ' '.join('%02x' % b for b in chunk)
    asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print('%08x  %-47s  %s' % (off, hexs, asc))

print("-" * 78)
print("首个 32 个小端 uint32:")
vals = struct.unpack_from('<32I', head, 0)
for i in range(0, 32, 8):
    print('  [%02d..] ' % i + ' '.join('%10d' % v for v in vals[i:i+8]))
print("  hex:    " + ' '.join('%08x' % v for v in vals[:8]))

print("-" * 78)
print("末尾 64 字节:")
print(tail.hex(' '))
print(tail.decode('latin1', 'replace'))
