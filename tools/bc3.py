"""Pure-stdlib BC1/BC3 (DXT1/DXT5) decode + encode, and a minimal PNG writer.

Kept dependency-free on purpose so the whole 汉化 toolchain is reproducible.
"""
import struct
import zlib


# ----------------------------------------------------------------------------- DDS
DDS_MAGIC = b'DDS '
DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PITCH = 0x8
DDSD_PIXELFORMAT = 0x1000
DDSD_MIPMAPCOUNT = 0x20000
DDSD_LINEARSIZE = 0x80000
DDPF_ALPHAPIXELS = 0x1
DDPF_FOURCC = 0x4
DDPF_RGB = 0x40
DDSCAPS_TEXTURE = 0x1000
DDSCAPS_MIPMAP = 0x400000
DDSCAPS_COMPLEX = 0x8


def find_dds(data):
    """Return the offset of the first embedded DDS, or None."""
    i = data.find(DDS_MAGIC)
    return i if i >= 0 else None


def parse_dds_header(data, off):
    h = data[off:off + 128]
    if h[:4] != DDS_MAGIC:
        raise ValueError('not a DDS')
    (dwSize, dwFlags, height, width, pitch, depth, mips) = struct.unpack_from('<7I', h, 4)
    pf_size, pf_flags, fourcc = struct.unpack_from('<3I', h, 76)
    rgbbits = struct.unpack_from('<I', h, 88)[0]
    rmask, gmask, bmask, amask = struct.unpack_from('<4I', h, 92)
    caps = struct.unpack_from('<I', h, 108)[0]
    return {
        'header_size': 128, 'width': width, 'height': height,
        'mips': max(1, mips), 'flags': dwFlags, 'pitch': pitch,
        'pf_flags': pf_flags, 'fourcc': fourcc, 'rgbbits': rgbbits,
        'masks': (rmask, gmask, bmask, amask), 'caps': caps,
    }


def _fourcc_str(v):
    return struct.pack('<I', v)


def dds_level_size(info, w, h):
    fc = _fourcc_str(info['fourcc'])
    if fc == b'DXT1':
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 8
    if fc in (b'DXT3', b'DXT5'):
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 16
    return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 16


# ----------------------------------------------------------------------------- BC3 decode
def _rgb565(v):
    r = ((v >> 11) & 0x1F) * 255 // 31
    g = ((v >> 5) & 0x3F) * 255 // 63
    b = (v & 0x1F) * 255 // 31
    return r, g, b


def decode_bc3_block(block):
    """16 bytes -> list of 16 (r,g,b,a) tuples, row-major 4x4."""
    a0, a1 = block[0], block[1]
    bits = int.from_bytes(block[2:8], 'little')
    if a0 > a1:
        av = [a0, a1,
              (6 * a0 + 1 * a1) // 7, (5 * a0 + 2 * a1) // 7,
              (4 * a0 + 3 * a1) // 7, (3 * a0 + 4 * a1) // 7,
              (2 * a0 + 5 * a1) // 7, (1 * a0 + 6 * a1) // 7]
    else:
        av = [a0, a1,
              (4 * a0 + 1 * a1) // 5, (3 * a0 + 2 * a1) // 5,
              (2 * a0 + 3 * a1) // 5, (1 * a0 + 4 * a1) // 5,
              0, 255]
    c0 = int.from_bytes(block[8:10], 'little')
    c1 = int.from_bytes(block[10:12], 'little')
    r0, g0, b0 = _rgb565(c0)
    r1, g1, b1 = _rgb565(c1)
    if c0 > c1:
        cv = [(r0, g0, b0), (r1, g1, b1),
              ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
              ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3)]
    else:
        cv = [(r0, g0, b0), (r1, g1, b1),
              ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2),
              (0, 0, 0)]
    cbits = int.from_bytes(block[12:16], 'little')
    out = []
    for i in range(16):
        ai = (bits >> (3 * i)) & 7
        ci = (cbits >> (2 * i)) & 3
        r, g, b = cv[ci]
        out.append((r, g, b, av[ai]))
    return out


def decode_bc3(data, off, w, h):
    """Decode a BC3/DXT5 surface into a bytearray of RGBA (w*h*4)."""
    out = bytearray(w * h * 4)
    bw = (w + 3) // 4
    bh = (h + 3) // 4
    p = off
    for by in range(bh):
        for bx in range(bw):
            block = data[p:p + 16]
            p += 16
            px = decode_bc3_block(block)
            for i in range(16):
                x = bx * 4 + (i % 4)
                y = by * 4 + (i // 4)
                if x < w and y < h:
                    o = (y * w + x) * 4
                    out[o:o + 4] = bytes(px[i])
    return out


# ----------------------------------------------------------------------------- BC3 encode
def _fit565(vals):
    """vals = sorted list of channel values 0..255 -> rgb565 const"""
    return max(0, min(255, int(round(vals))))


def encode_bc3_block(pixels):
    """pixels: 16 (r,g,b,a) tuples row-major -> 16 bytes."""
    alphas = [p[3] for p in pixels]
    amin, amax = min(alphas), max(alphas)
    if amin == amax:
        alpha_block = bytes([amin, amin] + [0] * 6)
    else:
        # 8-value mode: a0 > a1
        a0, a1 = amax, amin
        av = [a0, a1,
              (6 * a0 + 1 * a1) // 7, (5 * a0 + 2 * a1) // 7,
              (4 * a0 + 3 * a1) // 7, (3 * a0 + 4 * a1) // 7,
              (2 * a0 + 5 * a1) // 7, (1 * a0 + 6 * a1) // 7]
        bits = 0
        for i, a in enumerate(alphas):
            best_i, best_d = 0, 1 << 30
            for k, v in enumerate(av):
                dd = abs(v - a)
                if dd < best_d:
                    best_d, best_i = dd, k
            bits |= best_i << (3 * i)
        alpha_block = bytes([a0, a1]) + bits.to_bytes(6, 'little')

    rs = [p[0] for p in pixels]
    gs = [p[1] for p in pixels]
    bs = [p[2] for p in pixels]
    def to565(r, g, b):
        return ((r * 31 // 255) << 11) | ((g * 63 // 255) << 5) | (b * 31 // 255)
    c0 = to565(max(rs), max(gs), max(bs))
    c1 = to565(min(rs), min(gs), min(bs))
    r0, g0, b0 = _rgb565(c0)
    r1, g1, b1 = _rgb565(c1)
    if c0 > c1:
        cv = [(r0, g0, b0), (r1, g1, b1),
              ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
              ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3)]
        n = 4
    else:
        cv = [(r0, g0, b0), (r1, g1, b1),
              ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2)]
        n = 3
    cbits = 0
    for i, p in enumerate(pixels):
        best_i, best_d = 0, 1 << 30
        for k in range(n):
            dd = (cv[k][0] - p[0]) ** 2 + (cv[k][1] - p[1]) ** 2 + (cv[k][2] - p[2]) ** 2
            if dd < best_d:
                best_d, best_i = dd, k
        cbits |= best_i << (2 * i)
    return alpha_block + struct.pack('<HH', c0, c1) + cbits.to_bytes(4, 'little')


def encode_bc3(rgba, w, h):
    bw = (w + 3) // 4
    bh = (h + 3) // 4
    out = bytearray()
    for by in range(bh):
        for bx in range(bw):
            px = []
            for i in range(16):
                x = bx * 4 + (i % 4)
                y = by * 4 + (i // 4)
                if x < w and y < h:
                    o = (y * w + x) * 4
                    px.append((rgba[o], rgba[o + 1], rgba[o + 2], rgba[o + 3]))
                else:
                    px.append((0, 0, 0, 0))
            out += encode_bc3_block(px)
    return bytes(out)


# ----------------------------------------------------------------------------- PNG
def write_png(path, w, h, rgba):
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload +
                struct.pack('>I', zlib.crc32(tag + payload) & 0xFFFFFFFF))

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 6))
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


def read_png_rgba(path):
    """Minimal PNG reader for 8-bit RGBA / RGB non-interlaced files."""
    import zlib as _z
    d = open(path, 'rb').read()
    assert d[:8] == b'\x89PNG\r\n\x1a\n'
    p = 8
    w = h = bitd = ctype = None
    idat = bytearray()
    while p < len(d):
        ln = struct.unpack_from('>I', d, p)[0]
        tag = d[p + 4:p + 8]
        body = d[p + 8:p + 8 + ln]
        p += 12 + ln
        if tag == b'IHDR':
            w, h, bitd, ctype, comp, filt, inter = struct.unpack('>IIBBBBB', body)
            assert bitd == 8 and inter == 0, 'only 8-bit non-interlaced supported'
        elif tag == b'IDAT':
            idat += body
        elif tag == b'IEND':
            break
    nch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = _z.decompress(bytes(idat))
    stride = w * nch
    out = bytearray(w * h * 4)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        f = raw[pos]; pos += 1
        line = bytearray(raw[pos:pos + stride]); pos += stride
        if f == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        for x in range(w):
            s = x * nch
            o = (y * w + x) * 4
            if nch == 4:
                out[o:o + 4] = line[s:s + 4]
            elif nch == 3:
                out[o:o + 3] = line[s:s + 3]; out[o + 3] = 255
            elif nch == 2:
                out[o] = out[o + 1] = out[o + 2] = line[s]; out[o + 3] = line[s + 1]
            else:
                out[o] = out[o + 1] = out[o + 2] = line[s]; out[o + 3] = 255
        prev = line
    return w, h, out
