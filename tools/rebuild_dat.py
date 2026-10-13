"""Rebuild a TT Games old-format .DAT archive with some files replaced.

The name tree, name-string blob and CRC table never change (we do not add or
rename files), so everything after the file table inside the info block is
copied verbatim. Only the 16-byte file records (offset / zsize / size / packed)
are regenerated, which is exactly what a repack needs.

Usage:
  python rebuild_dat.py <original.dat> <out.dat> --replace <name>=<newfile> ...
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttdat import TTDat

ALIGN = 256
DATA_START = 1024


def rebuild(src, dst, replace):
    d = TTDat(src)
    raw = d.f  # file object
    fsize = d.size

    # --- original footer tail (everything after the file table) ---
    tail_start = 8 + d.fileCount * 16          # relative to infoOffset
    d.f.seek(d.infoOffset)
    footer_head = d.f.read(tail_start)          # infoType + fileCount + file table
    d.f.seek(d.infoOffset + tail_start)
    footer_tail = d.f.read(d.infoSize - tail_start)

    # --- read original file bodies we keep ---
    keep = {}
    for rec in d.files:
        nm = rec['name'] or ''
        if nm in replace:
            continue
        d.f.seek(rec['offset'])
        keep[rec['index']] = (d.f.read(rec['zsize']), rec['packed'], rec['zsize'], rec['size'])

    # --- assemble data region ---
    blobs = []
    table = []
    cursor = DATA_START
    index_of = {rec['name']: rec['index'] for rec in d.files if rec['name']}
    for rec in d.files:
        nm = rec['name'] or ''
        idx = rec['index']
        if nm in replace:
            data = replace[nm]
            packed, zsize, size = 0, len(data), len(data)
        else:
            data, packed, zsize, size = keep[idx]
        off = cursor
        table.append(struct.pack('<III', off >> 8, zsize, size)
                     + packed.to_bytes(3, 'little')
                     + bytes([off & 0xFF]))
        blobs.append((off, data))
        cursor += len(data)
        if cursor % ALIGN:
            cursor += ALIGN - (cursor % ALIGN)

    data_region = bytearray(cursor - DATA_START)
    for off, data in blobs:
        data_region[off - DATA_START:off - DATA_START + len(data)] = data

    new_info_off = DATA_START + len(data_region)
    if new_info_off % ALIGN:
        new_info_off += ALIGN - (new_info_off % ALIGN)

    footer = bytearray(footer_head)
    footer[8:8 + 16 * d.fileCount] = b''.join(table)
    footer += footer_tail
    info_size = len(footer)

    header = bytearray(DATA_START)
    header[:DATA_START] = open(src, 'rb').read(DATA_START)
    struct.pack_into('<I', header, 0x00, new_info_off)
    struct.pack_into('<I', header, 0x04, info_size)

    out = bytes(header) + bytes(data_region) + b'\x00' * (new_info_off - DATA_START - len(data_region)) + bytes(footer)
    with open(dst, 'wb') as f:
        f.write(out)

    print('rebuild %s -> %s' % (os.path.basename(src), os.path.basename(dst)))
    print('  files=%d  replaced=%d  data=%d bytes  infoOffset=%#x  infoSize=%d  total=%d'
          % (d.fileCount, len(replace), len(data_region), new_info_off, info_size, len(out)))
    print('  original size=%d' % fsize)
    d.close()
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--replace', nargs='*', default=[])
    a = ap.parse_args()
    rep = {}
    for spec in a.replace:
        name, path = spec.split('=', 1)
        with open(path, 'rb') as f:
            rep[name] = f.read()
        print('  replace %-40s <- %s (%d bytes)' % (name, os.path.basename(path), len(rep[name])))
    rebuild(a.src, a.dst, rep)


if __name__ == '__main__':
    main()
