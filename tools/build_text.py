"""Produce stuff/text/text.csv with an extra CHINESE language column.

Rows without a translation fall back to the ENGLISH text so the game never
shows a blank string. Also reports the character set actually needed, which
drives the font build.
"""
import csv, io, os, sys, collections

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, 'translations'))
from translations import TRANS
from translations_extra import TRANS_EXTRA
from translations_builder import TRANS_BUILDER
TRANS = dict(TRANS)
TRANS.update(TRANS_EXTRA)
TRANS.update(TRANS_BUILDER)

# 游戏资源根目录（含 GAME2/ 子目录）。可用 GAME_ROOT 覆盖，
# 因为游戏安装位置因人而异 —— 仓库里不含游戏素材，必须自带。
GAME_ROOT = os.environ.get('GAME_ROOT') or os.path.join(_ROOT, 'game_files')

SRC = os.path.join(GAME_ROOT, 'GAME2', 'stuff', 'text', 'text.csv')
# 方案 A：只加 CHINESE 列（引擎按语言取列）
# 方案 B：ENGLISH_TOO=1 时把中文同时写进 ENGLISH 列 —— 兜底引擎未选中文槽位
DST = os.environ.get('TXT_OUT') or os.path.join(_ROOT, 'build', 'stuff', 'text', 'text.csv')
ENGLISH_TOO = bool(os.environ.get('ENGLISH_TOO'))

raw = open(SRC, 'rb').read()
rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
hdr, body = rows[0], rows[1:]
i = {n: k for k, n in enumerate(hdr)}

assert 'CHINESE' not in hdr, 'CHINESE column already present'
new_hdr = hdr + ['CHINESE']

out = []
translated = 0
used_chars = set()
for r in body:
    if not r:
        out.append(r)
        continue
    if len(r) < len(hdr):          # malformed / short row -> pad, keep as-is
        r = r + [''] * (len(hdr) - len(r))
        out.append(r + [''])
        continue
    r = list(r) + ['']
    lab = r[i['LABEL']]
    en = r[i['ENGLISH']]
    zh = TRANS.get(lab, '')
    if zh:
        translated += 1
        used_chars |= set(zh)
        r[-1] = zh
        if ENGLISH_TOO:
            r[i['ENGLISH']] = zh      # 兜底：引擎若不选 CHINESE 列也显示中文
            r[i['AMERICAN']] = zh     # 美式英文槽位一并覆盖
    else:
        r[-1] = en            # fallback -> keeps the game readable
    out.append(r)

print('rows total          : %d' % len(out))
print('rows translated     : %d' % translated)
print('rows english-fallback: %d' % (len(out) - translated))

han = sorted(c for c in used_chars if ord(c) > 0x2E80)
punct = sorted(c for c in used_chars if 0x20 <= ord(c) <= 0x2E80)
print('unique CJK chars    : %d' % len(han))
print('unique ASCII/punct  : %d' % len(punct))
print('total charset       : %d' % (len(han) + len(punct)))

os.makedirs(os.path.dirname(DST), exist_ok=True)
buf = io.StringIO()
w = csv.writer(buf, lineterminator='\r\n', quoting=csv.QUOTE_MINIMAL)
w.writerow(new_hdr)
w.writerows(out)
data = buf.getvalue().encode('utf-8')
with open(DST, 'wb') as f:
    f.write(data)
print('wrote %s (%d bytes, source was %d bytes)' % (DST, len(data), len(raw)))

# dump the charset for the font builder
cs = os.path.join(os.path.dirname(DST), 'charset.txt')
with open(cs, 'w', encoding='utf-8') as f:
    f.write(''.join(sorted(used_chars)))
print('charset dump -> %s' % cs)
