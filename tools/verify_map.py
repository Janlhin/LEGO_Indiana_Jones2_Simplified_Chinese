"""Verify the hypothesis: for leaf name entries, fileIndex == (-next) (0 also means 0)."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttdat import TTDat

dat = sys.argv[1]
d = TTDat(dat)

print("fileCount      :", d.fileCount)
print("fileNameCount  :", d.fileNameCount)

leaves = []
for n in d.names:
    nx = n['next']
    if nx is None:
        continue
    if nx <= 0:
        leaves.append((-nx, n))
print("叶子条目数 (next <= 0):", len(leaves))

idx_map = collections.defaultdict(list)
for k, n in leaves:
    idx_map[k].append(n['full'])

dups = {k: v for k, v in idx_map.items() if len(v) > 1}
print("重复索引数:", len(dups))
if dups:
    for k in list(dups)[:5]:
        print("   idx %d -> %s" % (k, dups[k]))

keys = sorted(idx_map)
print("索引范围: %d .. %d" % (keys[0], keys[-1]) if keys else "none")
missing = [i for i in range(d.fileCount) if i not in idx_map]
print("缺失索引数: %d" % len(missing))
if missing:
    print("  前 20 个缺失:", missing[:20])
extra = [k for k in keys if k >= d.fileCount]
print("越界索引: %d %s" % (len(extra), extra[:10]))

print("\n=== 前 20 个文件（按索引）===")
for i in range(min(20, d.fileCount)):
    rec = d.files[i]
    name = idx_map.get(i, ['<none>'])[0]
    print("  [%4d] off=%-11d size=%-9d zsize=%-9d packed=%-2d  %s"
          % (i, rec['offset'], rec['size'], rec['zsize'], rec['packed'], name))

print("\n=== 目标文件定位 ===")
for want in ('stuff\\text\\text.csv', 'gui\\Font\\FONT_NXG.ft2',
             'framework-data\\gui\\Font\\buttons_360_NXG.fnt'):
    found = [(i, idx_map[i][0]) for i in keys
             if want.lower() in idx_map[i][0].lower()]
    if found:
        for i, nm in found:
            rec = d.files[i]
            print("  %-45s idx=%-5d off=%-11d size=%-9d zsize=%-9d packed=%d"
                  % (nm, i, rec['offset'], rec['size'], rec['zsize'], rec['packed']))
    else:
        hits = [n['full'] for n in d.names if want.split('\\')[-1].lower() in n['full'].lower()]
        print("  %-45s 未直接命中；相似: %s" % (want, hits[:5]))
