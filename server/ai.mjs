// The app's AI features, all on Meta models:
//   identify()    photo -> exhibit + the parts in view (muse-spark vision)
//   segment()     photo + parts -> one mask per part (SAM 3.1), the start of taking the real thing apart
//   choreograph() question -> a timed demonstration the browser plays (muse-spark tool calling over the exhibit's parts)
//   transcribe()  speech -> Taiwan traditional text (Muse ASR + one quick cleanup pass)
// Exhibits come from public/exhibits/index.json + <id>/manifest.json, the same manifest the browser loads. Every model answer is checked against it.
import { readFileSync } from 'node:fs';
import * as SAM from '@meta-sam/parser';
import { chat, sam, asr } from './meta.mjs';

const DIR = new URL('../public/exhibits/', import.meta.url);
const fail = (message, status = 400) => Object.assign(new Error(message), { status });
const load = (f) => JSON.parse(readFileSync(new URL(f, DIR), 'utf8'));
let cache;
export const exhibits = () => (cache ||= Object.fromEntries(load('index.json').exhibits.map((id) => [id, load(`${id}/manifest.json`)])));
export function exhibit(id) {
  const e = Object.hasOwn(exhibits(), id) && exhibits()[id];
  if (!e) throw fail('unknown exhibit');
  return e;
}
const json = (t) => { try { return JSON.parse(String(t).match(/\{[\s\S]*\}/)?.[0]); } catch { return null; } };
const num = (v, lo, hi, d) => (Number.isFinite(Number(v)) ? Math.min(hi, Math.max(lo, Number(v))) : d);

// ---------- photo -> exhibit + visible parts ----------
export async function identify({ image, mime }) {
  const list = Object.values(exhibits()).map((e) => `${e.id}｜${e.name}（像：${e.looksLike || e.name}）｜零件：${e.parts.map((p) => `${p.id}=${p.name}`).join('、')}`).join('\n');
  const system = `使用者用手機拍了一張真實機器的照片。找出最接近的展品，以及照片裡看得到、展品也有的零件（最多 4 個，最明顯的在前）。
不是機器（動物、食物、風景）就 match=false。say：一句台灣繁體中文口語 ≤ 40 字，說看到什麼、要看哪個零件。
只輸出 JSON：{"match":true,"exhibit":"id","confidence":0.0,"machine":"≤12字","parts":["零件id"],"say":""}
展品（id｜名稱｜零件）：
${list}`;
  let j = null, model;
  for (let k = 0; k < 2 && !j; k++) {   // now and then the JSON comes back broken: ask once more
    const r = await chat({ system, json: true, temperature: 0, messages: [{ role: 'user', content: '這是什麼？', image: { mime, data: image } }] });
    model = r.model; j = json(r.text);
  }
  const e = j && Object.hasOwn(exhibits(), j.exhibit) ? exhibits()[j.exhibit] : null;
  const confidence = num(j?.confidence, 0, 1, 0.5);
  if (!e || j.match === false || confidence < 0.2) return { match: false, say: String(j?.say || '這好像不是機器，拍拍看腳踏車或車子。').slice(0, 80), model };
  const ids = new Set(e.parts.map((p) => p.id));
  return { match: true, exhibit: e.id, confidence, machine: String(j.machine || '').slice(0, 24),
    parts: [...new Set(Array.isArray(j.parts) ? j.parts : [])].filter((p) => ids.has(p)).slice(0, 4),
    say: String(j.say || `這是${e.name}。`).slice(0, 80), model };
}

// ---------- photo + parts -> SAM masks ----------
// Each part is one SAM call (its English name is the prompt), run side by side. A part with no mask is simply absent.
export async function segment({ image, mime, exhibit: id, parts }) {
  const e = exhibit(id), want = [...new Set(parts)].slice(0, 4).map((p) => e.parts.find((x) => x.id === p));
  if (!want.length || want.some((p) => !p)) throw fail('unknown part');
  const out = await Promise.allSettled(want.map(async (p) => ({ part: p.id, masks: parseMasks(await sam({ prompt: p.en || p.name, mime, image })) })));
  return { exhibit: e.id, results: out.filter((r) => r.status === 'fulfilled' && r.value.masks.length).map((r) => r.value) };
}
export function parseMasks(text) {
  // read each mask's H×W before decoding, so a hostile payload can't make us allocate a huge raster (NaN fails too)
  const dims = text.split('data=').slice(1).map((d) => d.split(',', 2).map(Number));
  if (dims.length > 16 || dims.some(([h, w]) => !(h * w <= 1 << 20))) throw fail('SAM mask too large', 502);
  const reader = SAM.formats.segmentation.image().createParser();
  reader.push(text);
  const out = reader.finish({ status: 'completed' }).result;
  if (out.diagnostics.length) throw fail('SAM returned an invalid mask', 502);
  return SAM.recordsOfKind(out.records, 'mask')
    .map(({ bounds, mask }) => ({ bounds, width: mask.width, height: mask.height, path: SAM.decodeMaskToSVGPath(mask) }))
    .filter(({ path, bounds: b }) => path && [b.left, b.top, b.right, b.bottom].every(Number.isFinite) && b.right > b.left && b.bottom > b.top);
}

// ---------- question -> timed demonstration ----------
const MAX_STEPS = 12, MAX_T = 20, DIRS = ['up', 'down', 'left', 'right', 'forward', 'back', 'out'];
export function toolsFor(e) {
  const parts = { type: 'array', items: { type: 'string', enum: e.parts.map((p) => p.id) }, description: '零件 id' };
  const at = { type: 'number', description: `第幾秒開始（0–${MAX_T}）` };
  const T = (name, description, properties, required = []) => ({ name, description, parameters: { type: 'object', properties, required } });
  return [
    T('isolate', '只看這些零件：亮起來，其他變透明', { parts, at }, ['parts']),
    T('highlight', '讓零件亮起來，其他不變', { parts, at }, ['parts']),
    T('hide', '暫時隱藏擋住視線的零件', { parts, at }, ['parts']),
    T('show', '把隱藏的零件顯示回來', { parts, at }, ['parts']),
    T('detach', '把零件拆下來、往外移開，看清楚它', { parts, at, dir: { type: 'string', enum: DIRS }, amount: { type: 'number', description: '展品大小的比例 0–1' } }, ['parts']),
    T('rotate', '單獨轉動零件（不連動別的）', { parts, at, degrees: { type: 'number', description: '±1080' }, duration: { type: 'number', description: '秒 0.5–8' } }, ['parts']),
    ...(e.drives?.length ? [T('drive', '讓真實機構運轉：照真實連動帶動整串零件', { drive: { type: 'string', enum: e.drives.map((d) => d.id), description: e.drives.map((d) => `${d.id}=${d.name}`).join('；') }, speed: { type: 'number', description: '−1–1' }, duration: { type: 'number', description: '秒 1–10' }, at }, ['drive'])] : []),
    T('reset', '全部還原', { at }),
  ];
}
// model output -> steps the browser can trust: known parts / drives only, numbers clamped, ordered, bounded
export function cleanSteps(calls, e) {
  const ids = new Set(e.parts.map((p) => p.id)), drives = new Set((e.drives || []).map((d) => d.id)), names = new Set(toolsFor(e).map((t) => t.name));
  return calls.filter((c) => names.has(c.name)).map(({ name, args: a = {} }) => {
    const s = { do: name, at: num(a.at, 0, MAX_T, 0) };
    if (name === 'drive') return drives.has(a.drive) ? { ...s, drive: a.drive, speed: num(a.speed, -1, 1, 0.5), duration: num(a.duration, 1, 10, 4) } : null;
    if (name === 'reset') return s;
    const parts = (Array.isArray(a.parts) ? a.parts : []).filter((p) => ids.has(p));
    if (!parts.length) return null;
    if (name === 'detach') return { ...s, parts, dir: DIRS.includes(a.dir) ? a.dir : 'out', amount: num(a.amount, 0, 1, 0.3) };
    if (name === 'rotate') return { ...s, parts, degrees: num(a.degrees, -1080, 1080, 360), duration: num(a.duration, 0.5, 8, 3) };
    return { ...s, parts };
  }).filter(Boolean).sort((x, y) => x.at - y.at).slice(0, MAX_STEPS);
}
export async function choreograph({ exhibit: id, text, pointed, history = [] }) {
  const e = exhibit(id);
  const system = `你是「${e.title || e.name}」3D 教學模型的解說員，答案會被唸出來。
用工具動給使用者看：先 isolate 相關零件，有連動的用 drive，單一零件轉用 rotate，要看清楚就 detach；整段 4–15 秒，用 at 排先後。
同時在文字回覆裡用台灣繁體中文口語講 1–2 句（≤ 50 字）。數字規格只能用零件說明裡有的。
零件（id=名稱：說明）：
${e.parts.map((p) => `${p.id}=${p.name}${p.info ? '：' + p.info : ''}`).join('\n')}`;
  const r = await chat({ system, tools: toolsFor(e), maxTokens: 900, messages: [...history.slice(-4), { role: 'user', content: pointed ? `${text}\n（正指著：${pointed}）` : text }] });
  return { say: r.text.slice(0, 200), steps: cleanSteps(r.calls, e), model: r.model };
}

// ---------- speech -> text ----------
export async function transcribe({ wav, exhibit: id }) {
  const raw = await asr(wav);
  if (!raw) return { text: '' };
  const e = exhibits()[id] || Object.values(exhibits())[0];
  try {
    const r = await chat({ system: `把語音辨識結果改成台灣繁體中文，依詞彙修正聽錯的專有名詞，不改意思、不回答。只輸出修正後的句子。\n詞彙：${e.parts.flatMap((p) => [p.name, ...(p.aliases || [])]).join('、')}、${Object.values(exhibits()).map((x) => x.name).join('、')}`,
      messages: [{ role: 'user', content: raw }], maxTokens: 150, temperature: 0, ms: 4000 });
    return { text: r.text && r.text.length <= raw.length * 2 + 10 ? r.text : raw };   // a runaway answer is not a transcript
  } catch { return { text: raw }; }
}

// ---------- AI tutor: Socratic turns that grade the learner, drive the model and adapt the next question ----------
// One Muse call per turn: grade the last answer, demonstrate with the same tools as choreograph(), ask the next question.
const VERDICTS = ['right', 'partial', 'wrong'];
export function tutorTools(e) {
  return [...toolsFor(e),
    { name: 'grade', description: '學生剛回答時呼叫：評他的答案', parameters: { type: 'object', required: ['verdict', 'concept'], properties: {
      verdict: { type: 'string', enum: VERDICTS, description: 'right=講出因果；partial=方向對但漏了關鍵；wrong=錯或有迷思' },
      concept: { type: 'string', description: '這題考的概念，≤ 12 字' },
      gap: { type: 'string', description: '漏掉的關鍵或迷思，≤ 30 字；答對留空' } } } },
    { name: 'ask', description: '問學生下一題（每一輪都要呼叫一次）', parameters: { type: 'object', required: ['question'], properties: {
      question: { type: 'string', description: '一次只問一件事，≤ 40 字，答案看模型就能推出來' },
      choices: { type: 'array', items: { type: 'string' }, description: '學生卡住時才給 2–3 個選項（含 1 個對的），否則不給' } } } },
  ];
}
const clip = (v, n) => (typeof v === 'string' ? v.trim().slice(0, n) : '');
export function cleanTurn(calls, e) {
  const g = calls.find((c) => c.name === 'grade')?.args, q = calls.find((c) => c.name === 'ask')?.args;
  const grade = g && VERDICTS.includes(g.verdict) ? { verdict: g.verdict, concept: clip(g.concept, 20) || '這一題', gap: clip(g.gap, 60) } : null;
  const choices = (Array.isArray(q?.choices) ? q.choices : []).map((c) => clip(c, 40)).filter(Boolean).slice(0, 3);
  return { grade, question: clip(q?.question, 80) ? { q: clip(q.question, 80), choices: choices.length >= 2 ? choices : [] } : null, steps: cleanSteps(calls, e) };
}
export async function tutor({ exhibit: id, answer, history = [], known = [], focus }) {
  const e = exhibit(id), part = e.parts.find((p) => p.id === focus);
  const course = (e.lessons || []).map((l) => `${l.title}：${l.steps.map((s) => s.say).join(' ')}`).join('\n');
  const record = known.length ? known.map((k) => `${k.concept}：${{ right: '懂了', partial: '半懂', wrong: '答錯' }[k.verdict]}`).join('、') : '第一次上課';
  const system = `你是「${e.title || e.name}」3D 模型旁的機械家教，用蘇格拉底式教法：不直接給答案，用問題帶學生自己推理，再動模型讓他親眼確認。
每一輪都在同一個回覆裡一起呼叫多個工具：grade（學生有回答時）＋動模型的工具＋ask，三樣都要有。
1. 學生剛回答就呼叫 grade。口語、錯字、講得不完整都看意思評。
2. 用工具動模型給他看：isolate 相關零件，有連動就 drive，要看清楚就 detach，整段 3–10 秒。
3. 呼叫 ask 問下一題。答對就往下一層因果走、加深；半對或答錯就把同一個概念拆小再問；連錯兩題就給 choices。
4. 文字回覆會被唸出來，直接對學生說（用「你」）：台灣繁體中文口語 ≤ 60 字，先回應他的答案（對在哪、漏了什麼），不要重複題目。數字只能用下面資料裡有的。
學生的紀錄：${record}。從沒學過或答錯過的概念先教。${part ? `\n他剛拍了真的${part.name}，從${part.name}開始。` : ''}
零件（id=名稱：說明）：
${e.parts.map((p) => `${p.id}=${p.name}${p.info ? '：' + p.info : ''}`).join('\n')}
課綱（正確的因果）：
${course}`;
  const user = answer ? `我的回答：${answer}` : '開始上課，先問我第一題。';
  const r = await chat({ system, tools: tutorTools(e), maxTokens: 900, messages: [...history.slice(-6), { role: 'user', content: user }] });
  return { say: r.text.slice(0, 200), ...cleanTurn(r.calls, e), model: r.model };
}
