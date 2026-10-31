"""Write the bilingual teaching-content Markdown (made by export_md.py, edited by hand or by an LLM)
back into public/exhibits/<id>/manifest.json (中) and en.json (EN).

Every text sits under a `key` line; only the string values change, so the JSON files keep their layout.
python3 tools/content/import_md.py <edited.md> [--dry] [--report report.md]
"""
import json, re, sys, os

ROOT = os.path.join(os.path.dirname(__file__), '..', '..', 'public', 'exhibits')

# --- JSON with the source span of every value, so a value can be swapped in place -------------
def spans(text):
    out, i = {}, 0
    def ws():
        nonlocal i
        while text[i] in ' \t\r\n': i += 1
    def val(path):
        nonlocal i
        ws(); s = i; c = text[i]
        if c == '{':
            i += 1; ws()
            if text[i] == '}': i += 1
            else:
                while True:
                    ws(); k = string(); ws(); i += 1  # ':'
                    val(path + (k,)); ws()
                    if text[i] == ',': i += 1; continue
                    i += 1; break
        elif c == '[':
            i += 1; ws(); n = 0
            if text[i] == ']': i += 1
            else:
                while True:
                    val(path + (n,)); n += 1; ws()
                    if text[i] == ',': i += 1; continue
                    i += 1; break
        elif c == '"': string()
        else:
            m = re.compile(r'-?[\w.+-]+').match(text, i); i = m.end()
        out[path] = (s, i)
    def string():
        nonlocal i
        m = re.compile(r'"(?:[^"\\]|\\.)*"').match(text, i); i = m.end()
        return json.loads(m.group())
    val(())
    return out

# --- the Markdown --------------------------------------------------------------------------------
KEY = re.compile(r'`([a-z0-9_]+\.[\w.]+|[a-z0-9_]+)`')
LINE = re.compile(r'^\s*(?:-\s*)?(?:\*\*)?(?P<label>[^：:`]*?)\s*(?P<lang>中|EN)\s*(?:`[^`]*`)?\s*[：:]\s?(?P<text>.*)$')

def parse(md):
    """{(key, field, lang): text}; field is '' for a plain value."""
    vals, cur = {}, None
    for raw in md.splitlines():
        line = raw.rstrip()
        h = re.match(r'^(#{1,4})\s+(.*)$', line)
        keys = KEY.findall(line)
        if keys: cur = keys[-1]
        if h or (keys and not LINE.match(line) and ' / ' in line):   # "### `bike.parts.frame` 車架 / Frame" (heading or plain line)
            body = KEY.sub('', h.group(2) if h else line).strip()
            m = h and re.match(r'^([a-z0-9_]+)\s*·\s*(.*?)\s*/\s*(.*)$', h.group(2))   # "# bike · 自行車 / Bicycle", any level
            if m:
                vals[(m.group(1), 'name', '中')] = m.group(2); vals[(m.group(1), 'name', 'EN')] = m.group(3); cur = None
                continue
            if cur and re.search(r'\.(parts|lessons|faults)\.[\w]+$', cur) and ' / ' in body:
                zh, en = body.rsplit(' / ', 1)
                zh = re.sub(r'^(課程|故障)\s*', '', zh).strip()
                f = 'name' if '.parts.' in cur else 'title'
                vals[(cur, f, '中')] = zh; vals[(cur, f, 'EN')] = en.strip()
            continue
        m = LINE.match(line)
        if not m or not cur: continue
        label = m.group('label').replace('*', '').strip()
        f = {'info': 'info', 'aliases': 'aliases', '旁白': 'say', '題目': 'q'}.get(label, '')
        vals[(cur, f, m.group('lang'))] = m.group('text').strip()
    return vals

# --- where each value lives ----------------------------------------------------------------------
def locate(key, field, lang, man, en):
    """JSON path in manifest (中) or en.json (EN), and how to read the text."""
    p = key.split('.'); e = p[0]; r = p[1:]
    zh = lang == '中'
    def idx(lst, i): return next(n for n, x in enumerate(lst) if x['id'] == i)
    if not r: return (field,)                                    # name
    if r[0] in ('title', 'intro', 'looksLike'): return (r[0],)
    if r[0] == 'suggest': return ('suggest', int(r[1]))
    if r[0] == 'parts':
        f = field
        return ('parts', idx(man['parts'], r[1]), f) if zh else ('parts', r[1], f)
    if r[0] == 'drives':
        return ('drives', idx(man['drives'], r[1]), 'name') if zh else ('drives', r[1])
    if r[0] == 'lessons':
        base = ('lessons', idx(man['lessons'], r[1])) if zh else ('lessons', r[1])
        if len(r) == 2: return base + ('title',)
        s = base + ('steps', int(r[3]))
        if len(r) == 4: return s + ('say',)
        if len(r) == 5: return s + ('quiz', 'q')
        return s + ('quiz', 'options', int(r[6]))               # option: text + explanation
    if r[0] == 'faults':
        base = ('faults', idx(man['faults'], r[1])) if zh else ('faults', r[1])
        if len(r) == 2: return base + ('title',)
        if len(r) == 3: return base + (r[2],)
        return base + (r[2], int(r[3]))
    raise KeyError(key)

def split_option(text):
    m = re.match(r'^(.*?)\s*｜\s*(?:解說|Explanation)\s*[：:]\s*(.*)$', text)
    return (m.group(1), m.group(2)) if m else (text, None)

def main():
    args = sys.argv[1:]
    dry = '--dry' in args
    rep = args[args.index('--report') + 1] if '--report' in args else None
    md = open(args[0], encoding='utf-8').read()
    vals = parse(md)
    by_ex = {}
    for (key, f, lang), t in vals.items(): by_ex.setdefault(key.split('.')[0], []).append((key, f, lang, t))
    changes, problems = [], []
    for e, items in by_ex.items():
        files = {}
        for lang, fn in (('中', 'manifest.json'), ('EN', 'en.json')):
            path = os.path.join(ROOT, e, fn); text = open(path, encoding='utf-8').read()
            files[lang] = [path, text, json.loads(text), spans(text), []]
        man, en = files['中'][2], files['EN'][2]
        for key, f, lang, t in items:
            path, text, data, sp, edits = files[lang]
            try: jp = locate(key, f, lang, man, en)
            except (KeyError, StopIteration, IndexError, ValueError): problems.append(f'找不到位置：{key} {f} {lang}'); continue
            cur = data
            try:
                for k in jp: cur = cur[k]
            except (KeyError, IndexError, TypeError): problems.append(f'原檔沒有：{key} {f} {lang}'); continue
            if '.quiz.options.' in key:
                txt, why = split_option(t)
                if why is None: problems.append(f'選項格式不對（缺「｜ 解說：」）：{key} {lang}'); continue
                if lang == '中': repl = [(jp + (0,), txt), (jp + (2,), why)]
                else: repl = [(jp + (0,), txt), (jp + (1,), why)]
            elif f == 'aliases':
                new = [a.strip() for a in re.split(r'[、,，]', t) if a.strip()]
                repl = [(jp, new)]
            else: repl = [(jp, t)]
            for p2, new in repl:
                old = data
                for k in p2: old = old[k]
                if old != new:
                    edits.append((sp[p2], json.dumps(new, ensure_ascii=False)))
                    changes.append((e, key, f, lang, old, new))
        for lang, (path, text, data, sp, edits) in files.items():
            for (s, t_), v in sorted(edits, reverse=True): text = text[:s] + v + text[t_:]
            json.loads(text)
            if edits and not dry: open(path, 'w', encoding='utf-8').write(text)
    print(f'{len(changes)} 個欄位有改；{len(problems)} 個問題')
    for p in problems: print(' ', p)
    if rep:
        o = ['# 匯入變更清單', '', f'共 {len(changes)} 個欄位有改。', '']
        last = None
        for e, key, f, lang, old, new in changes:
            if e != last: o += [f'## {e}', '']; last = e
            fmt = lambda v: '、'.join(v) if isinstance(v, list) else v
            o += [f'- `{key}`{"." + f if f else ""} {lang}', f'  - 原：{fmt(old)}', f'  - 新：{fmt(new)}']
        open(rep, 'w', encoding='utf-8').write('\n'.join(o) + '\n')

if __name__ == '__main__': main()
