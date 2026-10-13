import sys, os, csv, io, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttdat import TTDat

GAME = r'D:\SteamLibrary\steamapps\common\Lego Indiana Jones 2'

# 1. 提取所有 .GIP 里的 String "XXX" 引用
d = TTDat(os.path.join(GAME, 'GAME.dat'))
gip_labels = {}  # label -> 引用它的 .GIP 文件
for r in d.files:
    nm = r['name'] or ''
    if not nm.lower().endswith('.gip'):
        continue
    data = d.read_file(r)
    txt = data.decode('latin-1')
    for m in re.finditer(r'String\s+"([^"]+)"', txt):
        lab = m.group(1)
        gip_labels.setdefault(lab, set()).add(nm.split('\\')[-1])
d.close()

print('=== .GIP 里引用的 String label 总数:', len(gip_labels), '===')

# 2. 读 text.csv 的 label 集合（含大小写）
d = TTDat(os.path.join(GAME, 'GAME2.dat'))
raw = d.read_file(d.by_name('stuff\\text\\text.csv')[0]).decode('utf-8-sig')
rows = list(csv.reader(io.StringIO(raw)))
i = {n: k for k, n in enumerate(rows[0])}
label_to_row = {}
for r in rows[1:]:
    if r:
        label_to_row[r[i['LABEL']]] = r
d.close()

# 3. 对照：找出 .GIP 引用但 text.csv 缺失/大小写不匹配的
missing = []
case_mismatch = []
for lab in sorted(gip_labels):
    if lab in label_to_row:
        continue  # 精确匹配，OK
    # 大小写不敏感匹配？
    lower = {k.lower(): k for k in label_to_row}
    if lab.lower() in lower:
        case_mismatch.append((lab, lower[lab.lower()], gip_labels[lab]))
    else:
        missing.append((lab, gip_labels[lab]))

print()
print('=== 大小写不匹配（.GIP引用 vs text.csv实际label）===')
for lab, actual, files in case_mismatch:
    row = label_to_row[actual]
    has_zh = any('\u4e00' <= c <= '\u9fff' for c in row[i['CHINESE']])
    print('  .GIP用 %-24r -> text.csv是 %-24r  ZH已译=%s  [%s]' % (lab, actual, has_zh, ','.join(sorted(files))))

print()
print('=== 完全缺失（.GIP引用但text.csv无此label）===')
for lab, files in missing:
    print('  %-28r [%s]' % (lab, ','.join(sorted(files))))
