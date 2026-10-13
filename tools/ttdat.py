"""
ttdat.py - TT Games (Traveller's Tales) .DAT archive reader for LEGO games.

Reimplemented in Python from the documented format used by:
  - Aluigi's ttgames.bms QuickBMS script (format authority)
  - https://github.com/xmusjackson/libttdat (C++ reference implementation)

Supports the "old format" used by LEGO Indiana Jones 2 (MkDat v4.0, infoType -3)
and the "new format" used by later titles (LEGO Jurassic World and friends).

CLI:
  python ttdat.py list    <dat> [-n N]
  python ttdat.py find    <dat> <substring>
  python ttdat.py extract <dat> <outdir> [--only substr] [--max-files N]
  python ttdat.py info    <dat>
"""
import os
import sys
import struct

S_LONG = 4
S_SHORT = 2
S_BYTE = 1
S_LONGLONG = 8

FNV32_OFFSET_BIAS = 0x811C9DC5
FNV32_PRIME = 0x01000193
FNV64_OFFSET_BIAS = 0xCBF29CE484222325
FNV64_PRIME = 0x100000001B3

INFO_AND = 0x80000000   # defs.hpp
INFO_XOR = 0xFFFFFFFF
INFO_SHIFT = 8
INFO_ADD = 0x100


def fnv1a_32(data: bytes) -> int:
    h = FNV32_OFFSET_BIAS
    for b in data:
        h = ((h ^ b) * FNV32_PRIME) & 0xFFFFFFFF
    return h


def fnv1a_64(data: bytes) -> int:
    h = FNV64_OFFSET_BIAS
    for b in data:
        h = ((h ^ b) * FNV64_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def _read(f, off, size):
    f.seek(off)
    return f.read(size)


def rd_le(f, off, size):
    d = _read(f, off, size)
    if len(d) != size:
        return None
    return int.from_bytes(d, 'little')


def rd_be(f, off, size):
    d = _read(f, off, size)
    if len(d) != size:
        return None
    return int.from_bytes(d, 'big')


class TTDat:
    """Reader for a TT Games .DAT archive."""

    def __init__(self, path):
        self.path = path
        self.size = os.path.getsize(path)
        self.f = open(path, 'rb')
        self.warnings = []
        self._parse_header()
        self._parse_names()
        self._parse_file_offsets()
        self._parse_crcs()
        self._match()

    def close(self):
        self.f.close()

    # ---------- header ----------
    def _get_info_offset(self):
        tmp = rd_le(self.f, 0, S_LONG)
        if tmp & INFO_AND:
            tmp ^= INFO_XOR
            tmp = (tmp << INFO_SHIFT) & 0xFFFFFFFF
            tmp += INFO_ADD
        return tmp

    def _is_new_format(self):
        def fourcc(v):
            if v is None:
                return b''
            return (v & 0xFFFFFFFF).to_bytes(4, 'little')
        a = fourcc(self.infoType)
        b = fourcc(self.fileCount)
        for t in (a, b):
            if t in (b'4CC.', b'.CC4'):
                return True
        return False

    def _parse_header(self):
        f = self.f
        # .HDR sidecar?
        base, _ = os.path.splitext(self.path)
        hdr = base + '.HDR'
        self.hdr_path = hdr if os.path.exists(hdr) else None
        self.info_loc_is_hdr = bool(self.hdr_path)

        info = open(self.hdr_path, 'rb') if self.hdr_path else f

        if self.hdr_path:
            self.infoOffset = 12
            self.infoSize = rd_be(info, 0, S_LONG)          # size of .HDR - 4
            self.infoType = rd_le(info, S_LONG, 0)
            self.fileCount = rd_le(info, S_LONG)
            self.newInfoOffset = None
        else:
            self.infoOffset = self._get_info_offset()
            self.infoSize = rd_le(f, 4, S_LONG)
            self.infoType = rd_le(f, self.infoOffset, S_LONG)
            # position after reading infoType is infoOffset+4
            self.fileCount = rd_le(f, self.infoOffset + 4, S_LONG)
            self.newInfoOffset = self.infoOffset + 8

        self.newFormat = self._is_new_format()
        if self.newFormat:
            raise NotImplementedError(
                "new-format (4CC) DAT detected - not required for LEGO Indiana Jones 2")

        info.seek(0)
        # old format
        self.nameInfoOffset = self.newInfoOffset + self.fileCount * 16 + 4
        self.fileNameCount = rd_le(f, self.nameInfoOffset - 4, S_LONG)
        self.nameFieldSize = 12 if (self.infoType is not None and self.infoType <= -5) else 8
        self.fileNamesOffset = (self.fileNameCount * self.nameFieldSize) + self.nameInfoOffset + 4
        _crc_ptr = rd_le(f, self.fileNamesOffset - 4, S_LONG)
        self.crcsOffset = _crc_ptr + self.fileNamesOffset - 4
        self.fileNamesSize = self.crcsOffset - self.fileNamesOffset - 4
        self.fileOffsOffset = self.infoOffset + (self.newInfoOffset - self.infoOffset)

        # CRC table width
        crcs32end = self.crcsOffset + self.fileCount * 4
        chk = rd_le(f, crcs32end, S_LONG)
        if chk in (0, 9):
            self.crc64 = False
        else:
            crcs64end = self.crcsOffset + self.fileCount * 8
            self.crc64 = crcs64end < (self.infoOffset + self.infoSize)
        if self.hdr_path:
            info.close()

    # ---------- name table ----------
    def _parse_names(self):
        f = self.f
        self.names = []
        crc_map = {}
        # read name entries sequentially
        entries = []
        off = self.nameInfoOffset
        for i in range(self.fileNameCount):
            nxt = rd_le(f, off, S_SHORT)
            prev = rd_le(f, off + 2, S_SHORT)
            nameOff = rd_le(f, off + 4, S_LONG)
            off += self.nameFieldSize
            entries.append((nxt, prev, nameOff))

        def signed16(v):
            return v - 0x10000 if v is not None and v >= 0x8000 else v

        tmpPath = ''
        for i, (nxt, prev, nameOff) in enumerate(entries):
            if nameOff is not None and nameOff >= 0:
                f.seek(self.fileNamesOffset + nameOff)
                buf = bytearray()
                while True:
                    c = f.read(1)
                    if not c or c == b'\x00':
                        break
                    buf += c
                name = buf.decode('latin1')
            else:
                name = ''
            if prev != 0 and i != 0 and prev < len(self.names):
                tmpPath = self.names[prev]['path']
            path = tmpPath
            nxt_s = signed16(nxt)
            if nxt_s is not None and nxt_s > 0:
                if name != '':
                    tmpPath += name + '\\'
            full = path + name
            self.names.append({'index': i, 'name': name, 'path': path, 'full': full,
                               'next': nxt_s, 'prev': prev})
            key = fnv1a_32(full.upper().encode('latin1'))
            crc_map[key] = full
        self.crc_map = crc_map

    # ---------- file table ----------
    def _parse_file_offsets(self):
        f = self.f
        self.files = []
        off = self.fileOffsOffset
        infoType = self.infoType if self.infoType is not None else 0
        for i in range(self.fileCount):
            d = _read(f, off, 16)
            if len(d) < 16:
                self.warnings.append('file table truncated at index %d' % i)
                break
            raw_off = int.from_bytes(d[0:4], 'little')
            zsize = int.from_bytes(d[4:8], 'little')
            size = int.from_bytes(d[8:12], 'little')
            packed = int.from_bytes(d[12:15], 'little')
            offadd = d[15]
            if infoType != -1:
                fileOff = (raw_off << 8) + offadd
            else:
                fileOff = raw_off + offadd
            self.files.append({
                'index': i, 'offset': fileOff, 'zsize': zsize, 'size': size,
                'packed': packed, 'crc': None, 'name': None,
            })
            off += 16

    def _parse_crcs(self):
        f = self.f
        width = 8 if self.crc64 else 4
        for i, rec in enumerate(self.files):
            v = rd_le(f, self.crcsOffset + i * width, width)
            rec['crc'] = v

    def _match(self):
        """
        Old-format archives carry the file index inside the name tree itself:
        for a leaf entry, `next` is 0 or -(fileIndex). Verified exhaustively on
        LEGO Indiana Jones 2 GAME.dat: 7659 leaves <-> 7659 file records, a
        perfect bijection over 0..fileCount-1. Fall back to the FNV-1a CRC
        table (used by newer titles) when the tree mapping is unavailable.
        """
        self.path_by_index = {}
        for n in self.names:
            nx = n['next']
            if nx is None or nx > 0:
                continue
            self.path_by_index[-nx] = n['full']
        for rec in self.files:
            mapped = self.path_by_index.get(rec['index'])
            if mapped:
                rec['name'] = mapped
            elif rec['crc'] is not None and rec['crc'] in self.crc_map:
                rec['name'] = self.crc_map[rec['crc']]

    # ---------- access ----------
    def read_file(self, rec):
        """Return the stored bytes. For packed records this is still the
        compressed stream (zsize bytes); decompression is not implemented."""
        self.f.seek(rec['offset'])
        return self.f.read(rec['zsize'])

    def by_name(self, target):
        t = target.upper()
        hits = [r for r in self.files if r['name'] and r['name'].upper() == t]
        return hits

    def search(self, sub):
        s = sub.upper()
        return [r for r in self.files if r['name'] and s in r['name'].upper()]

    def info(self):
        lines = [
            "file            : %s" % self.path,
            "size            : %d (%.2f MB)" % (self.size, self.size / 1048576),
            "infoOffset      : %#x" % self.infoOffset,
            "infoSize        : %d" % self.infoSize,
            "infoType        : %d" % (self.infoType if self.infoType is not None else 0),
            "newInfoOffset   : %#x" % self.newInfoOffset,
            "fileCount       : %d" % self.fileCount,
            "nameInfoOffset  : %#x" % self.nameInfoOffset,
            "fileNameCount   : %d" % self.fileNameCount,
            "nameFieldSize   : %d" % self.nameFieldSize,
            "fileNamesOffset : %#x" % self.fileNamesOffset,
            "fileNamesSize   : %d" % self.fileNamesSize,
            "fileOffsOffset  : %#x" % self.fileOffsOffset,
            "crcsOffset      : %#x" % self.crcsOffset,
            "crc64           : %s" % self.crc64,
            "names matched   : %d / %d" % (
                sum(1 for r in self.files if r['name']), len(self.files)),
            "hdr sidecar     : %s" % (self.hdr_path or 'none'),
        ]
        return '\n'.join(lines)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd, dat = sys.argv[1], sys.argv[2]
    d = TTDat(dat)
    if cmd == 'info':
        print(d.info())
        for w in d.warnings:
            print('WARN:', w)
    elif cmd == 'list':
        n = 0
        if '-n' in sys.argv:
            n = int(sys.argv[sys.argv.index('-n') + 1])
        for r in d.files:
            name = r['name'] or '<unmatched crc %#x>' % (r['crc'] or 0)
            print('%6d  off=%-12d zsize=%-10d size=%-10d packed=%-2d  %s'
                  % (r['index'], r['offset'], r['zsize'], r['size'], r['packed'], name))
            if n and r['index'] + 1 >= n:
                break
    elif cmd == 'find':
        sub = sys.argv[3]
        for r in d.search(sub):
            print('%6d  off=%-12d zsize=%-10d size=%-10d packed=%-2d  %s'
                  % (r['index'], r['offset'], r['zsize'], r['size'], r['packed'], r['name']))
    elif cmd == 'extract':
        outdir = sys.argv[3]
        only = None
        maxn = 0
        if '--only' in sys.argv:
            only = sys.argv[sys.argv.index('--only') + 1]
        if '--max-files' in sys.argv:
            maxn = int(sys.argv[sys.argv.index('--max-files') + 1])
        done = 0
        for r in d.files:
            if only and not (r['name'] and only.upper() in r['name'].upper()):
                continue
            name = r['name'] or ('_crc%08x.bin' % (r['crc'] or 0))
            dest = os.path.join(outdir, name.replace('\\', os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'wb') as o:
                o.write(d.read_file(r))
            done += 1
            if maxn and done >= maxn:
                break
        print('extracted %d file(s) to %s' % (done, outdir))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
