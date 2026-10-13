"""Parse a quoted CRLF-separated path list starting at a given offset."""
import sys

path = sys.argv[1]
off = int(sys.argv[2], 0)
limit = int(sys.argv[3], 0) if len(sys.argv) > 3 else 8 << 20

with open(path, 'rb') as f:
    f.seek(off)
    buf = f.read(limit)

items = []
i = 0
while i < len(buf):
    if buf[i:i+1] == b'"':
        j = buf.find(b'"', i + 1)
        if j < 0:
            break
        s = buf[i+1:j]
        items.append((off + i, s))
        i = j + 1
        # skip CRLF
        while i < len(buf) and buf[i:i+1] in (b'\r', b'\n'):
            i += 1
    else:
        break

print("file:", path)
print("list start: %#x" % off)
print("entries parsed: %d" % len(items))
print("list ends at: %#x" % (off + i))
print("-" * 78)
print("first 25:")
for o, s in items[:25]:
    print("  %#010x  %s" % (o, s.decode('latin1')))
print("...")
print("last 15:")
for o, s in items[-15:]:
    print("  %#010x  %s" % (o, s.decode('latin1')))

print("-" * 78)
print("按扩展名统计:")
import collections
c = collections.Counter()
for o, s in items:
    t = s.decode('latin1')
    ext = t.rsplit('.', 1)[-1].lower() if '.' in t else '(none)'
    c[ext] += 1
for k, v in c.most_common(40):
    print("  %-12s %d" % (k, v))

print("-" * 78)
print("含 text/font/lang 关键字的条目:")
for o, s in items:
    low = s.decode('latin1').lower()
    if any(k in low for k in ('text', 'font', 'lang', 'csv', '.fnt', '.ft2')):
        print("  %#010x  %s" % (o, s.decode('latin1')))
