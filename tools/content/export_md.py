# Export the teaching text of every exhibit (manifest.json 中 + en.json EN) as one bilingual Markdown with keys, for rewriting.
# python3 tools/content/export_md.py <out-dir>   (reads REF via git show; set REF to the branch to export)
import json, subprocess, sys, os
REF = 'origin/claude/project-thread-nul10q'   # PR #14 = main + "reasons" (wrong explanations for the why question)
OUT = sys.argv[1]
def load(p):
    return json.loads(subprocess.check_output(['git', 'show', f'{REF}:{p}']))
ids = load('public/exhibits/index.json')['exhibits']
L = 'ABCDEFG'
def pair(key, zh, en, label=None):
    out = [f'- `{key}`' + (f' （{label}）' if label else '')]
    out.append(f'  - 中：{zh}')
    out.append(f'  - EN：{en if en is not None else "（無英文）"}')
    return out

def exhibit(e):
    m = load(f'public/exhibits/{e}/manifest.json'); n = load(f'public/exhibits/{e}/en.json')
    o = [f'# {e} · {m["name"]} / {n["name"]}', '']
    o += ['## 1. 展品介紹', '']
    o += pair(f'{e}.title', m['title'], n['title'], '標題')
    o += pair(f'{e}.intro', m['intro'], n['intro'], '開場白')
    o += pair(f'{e}.looksLike', m['looksLike'], n['looksLike'], '拍照辨識用的同義詞，不顯示給學生')
    o += ['', '### 建議提問（首頁/展品頁的快速問題）', '']
    for i, (z, en) in enumerate(zip(m['suggest'], n['suggest'])):
        o += pair(f'{e}.suggest.{i}', z, en)
    o += ['', '## 2. 零件說明（點零件時顯示/朗讀）', '']
    for p in m['parts']:
        q = n['parts'].get(p['id'], {})
        o += [f'### `{e}.parts.{p["id"]}` {p["name"]} / {q.get("name","")}']
        o += [f'- info 中：{p.get("info","")}', f'- info EN：{q.get("info","")}']
        o += [f'- aliases 中：{"、".join(p.get("aliases",[]))}', f'- aliases EN：{", ".join(q.get("aliases",[]))}', '']
    o += ['## 3. 動作名稱（drive）', '']
    for d in m['drives']:
        o += pair(f'{e}.drives.{d["id"]}', d['name'], n.get('drives', {}).get(d['id']))
    o += ['', '## 4. 原理課程（Learn）與小測驗', '']
    for l in m['lessons']:
        nl = n['lessons'].get(l['id'], {}); ns = nl.get('steps', [])
        o += [f'### 課程 `{e}.lessons.{l["id"]}` {l["title"]} / {nl.get("title","")}', '']
        for i, s in enumerate(l['steps']):
            t = ns[i] if i < len(ns) else {}
            k = f'{e}.lessons.{l["id"]}.steps.{i}'
            o += [f'#### 步驟 {i+1} `{k}`', f'- 旁白 中：{s["say"]}', f'- 旁白 EN：{t.get("say","")}',
                  f'- 示範零件（勿改）：{", ".join(s.get("parts",[]))}']
            if 'quiz' in s:
                tq = t.get('quiz', {}); to = tq.get('options', [])
                o += [f'- **測驗** `{k}.quiz`', f'  - 題目 中：{s["quiz"]["q"]}', f'  - 題目 EN：{tq.get("q","")}']
                for j, (txt, ok, why) in enumerate(s['quiz']['options']):
                    et = to[j] if j < len(to) else ['', '']
                    o += [f'  - 選項 {L[j]} {"✅ 正解" if ok else "❌ 錯誤"} `{k}.quiz.options.{j}`',
                          f'    - 中：{txt} ｜ 解說：{why}', f'    - EN：{et[0]} ｜ Explanation: {et[1]}']
            o += ['']
    o += ['## 5. 修理挑戰（Fix）', '']
    for f in m.get('faults', []):
        g = n['faults'].get(f['id'], {}); k = f'{e}.faults.{f["id"]}'
        o += [f'### 故障 `{k}` {f["title"]} / {g.get("title","")}', '',
              f'- 正確的壞掉零件（勿改）：{", ".join(f["broken"])}；對應課程：{f.get("lesson","")}', '']
        for fld, label in [('short', '首頁卡片的一句症狀'), ('symptom', '開場症狀描述'), ('observe', '「先看」提示'), ('hint', '線索（按提示/猜錯後）')]:
            o += pair(f'{k}.{fld}', f[fld], g.get(fld), label)
        o += ['', f'**猜測選項**（正解是第 {f["right"]+1} 個；每個錯誤選項配一句「為什麼不是它」）', '']
        for j, s in enumerate(f['suspects']):
            ok = j == f['right']
            ew = g.get('suspects', [''] * 9)[j]
            o += [f'- 選項 {L[j]} {"✅ 正解" if ok else "❌ 錯誤"} `{k}.suspects.{j}`', f'  - 中：{s}', f'  - EN：{ew}']
            if not ok:
                o += [f'  - 為什麼不是 中 `{k}.whys.{j}`：{f["whys"][j]}', f'  - 為什麼不是 EN：{g.get("whys",[""]*9)[j]}']
        o += ['', '**修好之後**', '']
        o += pair(f'{k}.cause', f['cause'], g.get('cause'), '修好時揭曉的原因')
        o += pair(f'{k}.why', f['why'], g.get('why'), '追問「為什麼」的題目')
        o += pair(f'{k}.answer', f['answer'], g.get('answer'), '✅ 標準答案（也是點選題的正確選項）')
        for j, r in enumerate(f.get('reasons', [])):
            o += pair(f'{k}.reasons.{j}', r, (g.get('reasons') or [None]*9)[j], '❌ 點選題的錯誤選項（常見迷思）')
        o += ['']
    return '\n'.join(o) + '\n'

HEAD = '''# Mechanica 教學內容匯出（給 Gemini 優化用）

來源：jhuang-tw/mechanica 的 `public/exhibits/<展品>/manifest.json`（中文）與 `en.json`（英文），
以 PR #14（main + 修理挑戰「為什麼」的點選錯誤選項 reasons）為準。產生日期 2026-10-31。

## 給 Gemini 的規則（請一起貼過去）

1. **反引號裡的 key（例如 `bike.lessons.drive.steps.2.quiz.options.0`）一個字都不能改、不能刪、不能新增**，改完的文字要靠它匯回程式。
2. 只改「中：」「EN：」後面的文字。中英文意思要一致，中文用台灣繁體口語，對象是國中到高中生。
3. 標「勿改」的行（零件 id、壞掉零件、對應課程）不要動；✅/❌ 正解位置不要換。
4. 測驗選項數量維持不變；錯誤選項要是學生真的會有的迷思，解說要說出「為什麼錯」。
5. 數字（齒數、轉速、比例等）只能用原文已有的數字，不要自己編新數據。
6. 旁白（say）、答案（answer）會被語音唸出來：每句盡量短，中文 ≤ 60 字。
7. 修理挑戰的「為什麼不是它」要引導學生去看模型上的某個地方，而不是直接說出答案。
8. 輸出時保留完全相同的 Markdown 結構，可另外在檔尾附「修改說明」。

'''
os.makedirs(OUT, exist_ok=True)
allmd = [HEAD, '## 目錄', ''] + [f'- {e}' for e in ids] + ['']
for e in ids:
    md = exhibit(e)
    open(f'{OUT}/{e}.md', 'w').write(HEAD + md)
    allmd.append(md)
open(f'{OUT}/ALL.md', 'w').write('\n'.join(allmd))
