"""PE section parser + cross-reference scanner.

Locates code in .text that references a given string by searching for the
little-endian absolute VA of that string (MSVC x86 typically loads string
addresses via `push offset str` / `mov reg, offset str`).
"""
import struct


class PE:
    def __init__(self, path):
        self.data = open(path, 'rb').read()
        d = self.data
        self.image_base = None
        self.sections = []
        pe_off = struct.unpack_from('<I', d, 0x3C)[0]
        assert d[pe_off:pe_off+4] == b'PE\x00\x00'
        machine = struct.unpack_from('<H', d, pe_off + 4)[0]
        nsec = struct.unpack_from('<H', d, pe_off + 6)[0]
        opt_size = struct.unpack_from('<H', d, pe_off + 20)[0]
        opt_off = pe_off + 24
        magic = struct.unpack_from('<H', d, opt_off)[0]
        self.is64 = (magic == 0x20b)
        self.image_base = struct.unpack_from('<I' if not self.is64 else '<Q',
                                             d, opt_off + 28)[0]
        sect_off = opt_off + opt_size
        for i in range(nsec):
            o = sect_off + i * 40
            name = d[o:o+8].rstrip(b'\x00').decode('latin1')
            vsize, vaddr, rsize, raddr = struct.unpack_from('<IIII', d, o + 8)
            chars = struct.unpack_from('<I', d, o + 36)[0]
            self.sections.append({
                'name': name, 'vsize': vsize, 'vaddr': vaddr,
                'rsize': rsize, 'raddr': raddr, 'chars': chars,
            })

    def off_to_rva(self, off):
        for s in self.sections:
            if s['raddr'] <= off < s['raddr'] + s['rsize']:
                return s['vaddr'] + (off - s['raddr'])
        return None

    def off_to_va(self, off):
        r = self.off_to_rva(off)
        return None if r is None else self.image_base + r

    def rva_to_off(self, rva):
        for s in self.sections:
            if s['vaddr'] <= rva < s['vaddr'] + max(s['vsize'], s['rsize']):
                return s['raddr'] + (rva - s['vaddr'])
        return None

    def section(self, name):
        for s in self.sections:
            if s['name'] == name:
                return s
        return None

    def find_str(self, needle):
        """Return list of file offsets where needle occurs (as latin1 bytes)."""
        if isinstance(needle, str):
            needle = needle.encode('latin1')
        out, i = [], 0
        while True:
            j = self.data.find(needle, i)
            if j < 0:
                break
            out.append(j)
            i = j + 1
        return out

    def xrefs_to_va(self, va):
        """Search .text for 4-byte LE occurrences of va."""
        t = self.section('.text')
        if not t:
            return []
        blob = self.data[t['raddr']:t['raddr'] + t['rsize']]
        pat = struct.pack('<I', va)
        out, i = [], 0
        while True:
            j = blob.find(pat, i)
            if j < 0:
                break
            out.append(t['raddr'] + j)
            i = j + 1
        return out
