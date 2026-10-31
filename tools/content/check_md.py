"""Compare an edited content Markdown with the original export: keys, right answers, locked lines, new numbers, length.
python3 tools/content/check_md.py <original.md> <edited.md>
"""
import re, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from import_md import parse, KEY

def locked(md):
    return [re.sub(r'^[-\s]*|\*\*', '', l).strip() for l in md.splitlines() if '（勿改）' in l or ('`' in l and ('✅' in l or '❌' in l)) or '正解是第' in l]
def nums(t): return set(re.findall(r'\d+(?:\.\d+)?', t))

a, b = (open(p, encoding='utf-8').read() for p in sys.argv[1:3])
va, vb = parse(a), parse(b)
ka, kb = KEY.findall(a), KEY.findall(b)
out = []
miss, extra = set(va) - set(vb), set(vb) - set(va)
out += [f'少了：{k}' for k in sorted(miss)] + [f'多了：{k}' for k in sorted(extra)]
if [k for k in ka] != [k for k in kb]: out.append(f'key 順序或數量不同（原 {len(ka)}、新 {len(kb)}）')
la, lb = locked(a), locked(b)
for x, y in zip(la, lb):
    if x != y: out.append(f'鎖定行被改：\n    原 {x}\n    新 {y}')
if len(la) != len(lb): out.append(f'鎖定行數不同（原 {len(la)}、新 {len(lb)}）')
for k in sorted(set(va) & set(vb)):
    new = nums(vb[k]) - nums(va[k])
    if new: out.append(f'新數字 {sorted(new)}：{k[0]} {k[1]} {k[2]}\n    原 {va[k]}\n    新 {vb[k]}')
    if k[2] == '中' and (k[1] == 'say' or k[0].endswith(('.answer', '.cause'))) and len(vb[k]) > 60:
        out.append(f'超過 60 字（{len(vb[k])}）：{k[0]}')
    if not vb[k].strip() and va[k].strip(): out.append(f'被清空：{k[0]} {k[1]} {k[2]}')
print(f'{len(va)} 段原文、{len(vb)} 段新文、{sum(va[k] != vb.get(k) for k in va)} 段有改；{len(out)} 個問題')
print('\n'.join(out))
