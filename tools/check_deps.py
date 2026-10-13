import struct
import sys

d = open(sys.argv[1], "rb").read()
pe = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, pe + 6)[0]
optoff = pe + 24
magic = struct.unpack_from("<H", d, optoff)[0]
ddoff = optoff + (96 if magic == 0x10B else 112)
impva, _impsz = struct.unpack_from("<II", d, ddoff + 8)
print(("PE32" if magic == 0x10B else "PE32+"), "导入表 RVA", hex(impva))

secs = []
# 节表紧跟在可选头之后：起点 = pe + 24(COFF头) + SizeOfOptionalHeader
shoff = pe + 24 + struct.unpack_from("<H", d, pe + 20)[0]
for i in range(nsec):
    b = shoff + i * 40
    nm = d[b:b + 8].rstrip(b"\0").decode()
    vs, va, rs, ra = struct.unpack_from("<IIII", d, b + 8)
    secs.append((nm, va, vs, rs, ra))


def r2o(r):
    for _nm, va, vs, rs, ra in secs:
        if va <= r < va + max(vs, rs):
            return ra + (r - va)
    return None


off = r2o(impva)
names = []
while True:
    nrva = struct.unpack_from("<I", d, off + 12)[0]
    if nrva == 0:
        break
    o = r2o(nrva)
    e = d.index(b"\0", o)
    names.append(d[o:e].decode())
    off += 20

print("依赖 DLL:")
for n in names:
    print("  ", n)
bad = [n for n in names
       if any(x in n.lower() for x in ("libgcc", "libstdc", "pthread"))]
print("外发依赖:", bad if bad else "无 —— 可单文件分发")