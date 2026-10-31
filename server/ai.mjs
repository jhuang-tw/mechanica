// The app's AI features, all on Meta models:
//   identify()    photo -> exhibit + the parts in view (muse-spark vision)
//   segment()     photo + parts -> one mask per part (SAM 3.1), the start of taking the real thing apart
//   choreograph() question -> a timed demonstration the browser plays (muse-spark tool calling over the exhibit's parts)
//   transcribe()  speech -> Taiwan traditional text (Muse ASR + one quick cleanup pass)
// Exhibits come from public/exhibits/index.json + <id>/manifest.json, the same manifest the browser loads. Every model answer is checked against it.
import { readFileSync } from 'node:fs';
import * as SAM from '@meta-sam/parser';
import { chat, sam, asr } from './meta.mjs';
import { localize } from '../src/localize.js';

const DIR = new URL('../public/exhibits/', import.meta.url);
const fail = (message, status = 400) => Object.assign(new Error(message), { status });
const load = (f) => JSON.parse(readFileSync(new URL(f, DIR), 'utf8'));
// lang 'en': every manifest with its en.json words laid over it (src/localize.js), and every prompt below in English
const cache = {};
const overlay = (id) => { try { return load(`${id}/en.json`); } catch { return {}; } };
export const exhibits = (lang) => (cache[lang === 'en' ? 'en' : 'zh'] ||= Object.fromEntries(load('index.json').exhibits.map((id) => [id, lang === 'en' ? localize(load(`${id}/manifest.json`), overlay(id)) : load(`${id}/manifest.json`)])));
export function exhibit(id, lang) {
  const e = Object.hasOwn(exhibits(lang), id) && exhibits(lang)[id];
  if (!e) throw fail('unknown exhibit');
  return e;
}
const json = (t) => { try { return JSON.parse(String(t).match(/\{[\s\S]*\}/)?.[0]); } catch { return null; } };
const EN = (e) => e?.lang === 'en';
const num = (v, lo, hi, d) => (Number.isFinite(Number(v)) ? Math.min(hi, Math.max(lo, Number(v))) : d);

// ---------- photo -> exhibit + visible parts ----------
export async function identify({ image, mime, lang }) {
  const all = exhibits(lang), en = lang === 'en';
  const list = Object.values(all).map((e) => en ? `${e.id} | ${e.name} (looks like: ${e.looksLike || e.name}) | parts: ${e.parts.map((p) => `${p.id}=${p.name}`).join(', ')}` : `${e.id}｜${e.name}（像：${e.looksLike || e.name}）｜零件：${e.parts.map((p) => `${p.id}=${p.name}`).join('、')}`).join('\n');
  const system = en ? `The user took a phone photo of a real machine. Find the closest exhibit and the parts that are visible in the photo and that the exhibit also has (at most 4, most obvious first).
If it is not a machine (an animal, food, scenery), match=false. say: one short spoken English sentence, at most 25 words, saying what you see and which part to look at.
Output JSON only: {"match":true,"exhibit":"id","confidence":0.0,"machine":"at most 4 words","parts":["part id"],"say":""}
Exhibits (id | name | parts):
${list}` : `使用者用手機拍了一張真實機器的照片。找出最接近的展品，以及照片裡看得到、展品也有的零件（最多 4 個，最明顯的在前）。
不是機器（動物、食物、風景）就 match=false。say：一句台灣繁體中文口語 ≤ 40 字，說看到什麼、要看哪個零件。
只輸出 JSON：{"match":true,"exhibit":"id","confidence":0.0,"machine":"≤12字","parts":["零件id"],"say":""}
展品（id｜名稱｜零件）：
${list}`;
  let j = null, model;
  for (let k = 0; k < 2 && !j; k++) {   // now and then the JSON comes back broken: ask once more
    const r = await chat({ system, json: true, temperature: 0, messages: [{ role: 'user', content: en ? 'What is this?' : '這是什麼？', image: { mime, data: image } }] });
    model = r.model; j = json(r.text);
  }
  const e = j && Object.hasOwn(all, j.exhibit) ? all[j.exhibit] : null;
  const confidence = num(j?.confidence, 0, 1, 0.5);
  if (!e || j.match === false || confidence < 0.2) return { match: false, say: String(j?.say || (en ? "That doesn't look like a machine. Try a bike or a car." : '這好像不是機器，拍拍看腳踏車或車子。')).slice(0, en ? 200 : 80), model };
  const ids = new Set(e.parts.map((p) => p.id));
  return { match: true, exhibit: e.id, confidence, machine: String(j.machine || '').slice(0, 24),
    parts: [...new Set(Array.isArray(j.parts) ? j.parts : [])].filter((p) => ids.has(p)).slice(0, 4),
    say: String(j.say || (en ? `This is a ${e.name}.` : `這是${e.name}。`)).slice(0, en ? 200 : 80), model };
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
  if (EN(e)) return toolsEn(e);
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
function toolsEn(e) {
  const parts = { type: 'array', items: { type: 'string', enum: e.parts.map((p) => p.id) }, description: 'part ids' };
  const at = { type: 'number', description: `start time in seconds (0–${MAX_T})` };
  const T = (name, description, properties, required = []) => ({ name, description, parameters: { type: 'object', properties, required } });
  return [
    T('isolate', 'Show only these parts: light them up, make everything else see-through', { parts, at }, ['parts']),
    T('highlight', 'Light these parts up, leave the rest as it is', { parts, at }, ['parts']),
    T('hide', 'Hide parts that block the view for now', { parts, at }, ['parts']),
    T('show', 'Show hidden parts again', { parts, at }, ['parts']),
    T('detach', 'Take the parts off and move them out to see them clearly', { parts, at, dir: { type: 'string', enum: DIRS }, amount: { type: 'number', description: 'fraction of the exhibit size, 0–1' } }, ['parts']),
    T('rotate', 'Turn parts on their own (nothing else follows)', { parts, at, degrees: { type: 'number', description: '±1080' }, duration: { type: 'number', description: 'seconds, 0.5–8' } }, ['parts']),
    ...(e.drives?.length ? [T('drive', 'Run the real mechanism: every linked part moves at its real ratio', { drive: { type: 'string', enum: e.drives.map((d) => d.id), description: e.drives.map((d) => `${d.id}=${d.name}`).join('; ') }, speed: { type: 'number', description: '−1–1' }, duration: { type: 'number', description: 'seconds, 1–10' }, at }, ['drive'])] : []),
    T('reset', 'Put everything back', { at }),
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
const partList = (e) => e.parts.map((p) => `${p.id}=${p.name}${p.info ? (EN(e) ? ': ' : '：') + p.info : ''}`).join('\n');
// Meta's safety filter refuses some harmless wordings: ask once more in plain words
const retried = async (ask, first, plain) => { try { return await ask(first); } catch (err) { if (!err.policy) throw err; return ask(plain); } };
export async function choreograph({ exhibit: id, text, pointed, history = [], lang }) {
  const e = exhibit(id, lang);
  const system = EN(e) ? `You narrate a 3D teaching model of the ${e.title || e.name}. Your answer is read aloud.
Show the user with the tools: first isolate the relevant parts, use drive for linked motion, rotate for a single part, detach to see clearly; the whole thing 4–15 seconds, ordered with at.
In the same reply, say 1–2 short sentences in plain spoken English (at most 35 words). Only use numbers and specs that appear in the part descriptions.
Parts (id=name: description):
${partList(e)}` : `你是「${e.title || e.name}」3D 教學模型的解說員，答案會被唸出來。
用工具動給使用者看：先 isolate 相關零件，有連動的用 drive，單一零件轉用 rotate，要看清楚就 detach；整段 4–15 秒，用 at 排先後。
同時在文字回覆裡用台灣繁體中文口語講 1–2 句（≤ 50 字）。數字規格只能用零件說明裡有的。
零件（id=名稱：說明）：
${e.parts.map((p) => `${p.id}=${p.name}${p.info ? '：' + p.info : ''}`).join('\n')}`;
  const r = await chat({ system, tools: toolsFor(e), maxTokens: 900, messages: [...history.slice(-4), { role: 'user', content: pointed ? `${text}\n${EN(e) ? `(pointing at: ${pointed})` : `（正指著：${pointed}）`}` : text }] });
  return { say: r.text.slice(0, EN(e) ? 400 : 200), steps: cleanSteps(r.calls, e), model: r.model };
}

// ---------- speech -> text ----------
export async function transcribe({ wav, exhibit: id, lang }) {
  const raw = await asr(wav);
  if (!raw) return { text: '' };
  const all = exhibits(lang), e = all[id] || Object.values(all)[0];
  try {
    const r = await chat({ system: lang === 'en' ? `Clean up this speech recognition result as English. Fix misheard technical terms using the vocabulary, keep the meaning, do not answer it. Output only the corrected sentence.\nVocabulary: ${e.parts.flatMap((p) => [p.name, ...(p.aliases || [])]).join(', ')}, ${Object.values(all).map((x) => x.name).join(', ')}` : `把語音辨識結果改成台灣繁體中文，依詞彙修正聽錯的專有名詞，不改意思、不回答。只輸出修正後的句子。\n詞彙：${e.parts.flatMap((p) => [p.name, ...(p.aliases || [])]).join('、')}、${Object.values(all).map((x) => x.name).join('、')}`,
      messages: [{ role: 'user', content: raw }], maxTokens: 150, temperature: 0, ms: 4000 });
    return { text: r.text && r.text.length <= raw.length * 2 + 10 ? r.text : raw };   // a runaway answer is not a transcript
  } catch { return { text: raw }; }
}

// ---------- AI tutor: Socratic turns that grade the learner, drive the model and adapt the next question ----------
// One Muse call per turn: grade the last answer, demonstrate with the same tools as choreograph(), ask the next question.
const VERDICTS = ['right', 'partial', 'wrong'];
export function tutorTools(e) {
  if (EN(e)) return [...toolsFor(e),
    { name: 'grade', description: 'Call when the student has just answered: grade the answer', parameters: { type: 'object', required: ['verdict', 'concept'], properties: {
      verdict: { type: 'string', enum: VERDICTS, description: 'right=states the cause and effect; partial=right direction but misses the key point; wrong=wrong or a misconception' },
      concept: { type: 'string', description: 'the concept this question tests, at most 5 words' },
      gap: { type: 'string', description: 'the missing key point or misconception, at most 15 words; empty when right' } } } },
    { name: 'ask', description: 'Ask the student the next question (call it once every turn)', parameters: { type: 'object', required: ['question', 'choices'], properties: {
      question: { type: 'string', description: 'one thing at a time, at most 20 words, answerable by looking at the model' },
      choices: { type: 'array', items: { type: 'string' }, description: '2–3 short options, one right, the wrong ones common misconceptions (the student can tap one or answer in their own words)' } } } },
  ];
  return [...toolsFor(e),
    { name: 'grade', description: '學生剛回答時呼叫：評他的答案', parameters: { type: 'object', required: ['verdict', 'concept'], properties: {
      verdict: { type: 'string', enum: VERDICTS, description: 'right=講出因果；partial=方向對但漏了關鍵；wrong=錯或有迷思' },
      concept: { type: 'string', description: '這題考的概念，≤ 12 字' },
      gap: { type: 'string', description: '漏掉的關鍵或迷思，≤ 30 字；答對留空' } } } },
    { name: 'ask', description: '問學生下一題（每一輪都要呼叫一次）', parameters: { type: 'object', required: ['question', 'choices'], properties: {
      question: { type: 'string', description: '一次只問一件事，≤ 40 字，答案看模型就能推出來' },
      choices: { type: 'array', items: { type: 'string' }, description: '2–3 個短選項，含 1 個對的，錯的用常見迷思（學生可以點選，也可以用自己的話回答）' } } } },
  ];
}
const clip = (v, n) => (typeof v === 'string' ? v.trim().slice(0, n) : '');
export function cleanTurn(calls, e) {
  const g = calls.find((c) => c.name === 'grade')?.args, q = calls.find((c) => c.name === 'ask')?.args, k = EN(e) ? 2.5 : 1;   // English needs more characters for the same idea
  const grade = g && VERDICTS.includes(g.verdict) ? { verdict: g.verdict, concept: clip(g.concept, 20 * k) || (EN(e) ? 'this question' : '這一題'), gap: clip(g.gap, 60 * k) } : null;
  const choices = (Array.isArray(q?.choices) ? q.choices : []).map((c) => clip(c, 40 * k)).filter(Boolean).slice(0, 3);
  return { grade, question: clip(q?.question, 80 * k) ? { q: clip(q.question, 80 * k), choices: choices.length >= 2 ? choices : [] } : null, steps: cleanSteps(calls, e) };
}
// ---------- explain it back: the learner retells a lesson, Muse checks each cause → effect link ----------
export async function explainBack({ exhibit: id, lesson, text, lang }) {
  const e = exhibit(id, lang), l = (e.lessons || []).find((x) => x.id === lesson);
  if (!l) throw fail('unknown lesson');
  const n = l.steps.length;
  const system = EN(e) ? `The student has just finished the lesson "${l.title}" and now explains it in their own words. Check each of the ${n} cause-and-effect links below and decide whether they covered it: stating the main cause and effect counts, the wording doesn't have to match, a term, comparison or number inside the link left unsaid is not a miss, judge casual speech and typos by meaning; a link they got wrong (a number or direction reversed, say) counts as not covered.
Output JSON only: {"covered":[${n} true/false values],"wrong":"what they got wrong, at most 15 words, or an empty string","say":"at most 35 words of plain spoken English, said straight to them (use 'you'): first praise what they got right, then correct anything they got wrong, or if nothing was wrong point out the first missing link"}
Links:
${l.steps.map((s, i) => `${i + 1}. ${s.say}`).join('\n')}` : `學生剛上完「${l.title}」，現在用自己的話講一遍。逐一對照下面 ${n} 個因果環節，判斷他有沒有講到：講出主要的因果就算，用詞不必一樣，環節裡的術語、比喻、數字沒提到不算漏，口語和錯字照意思評；講錯的（例如數字或方向相反）算沒講到。
只輸出 JSON：{"covered":[${n} 個 true/false],"wrong":"他講錯的地方 ≤ 30 字，沒有就空字串","say":"≤ 60 字台灣繁體中文口語，直接對他說（用「你」）：先肯定講對的，有講錯就更正講錯的地方，沒有才點出漏掉的第一個環節"}
環節：
${l.steps.map((s, i) => `${i + 1}. ${s.say}`).join('\n')}`;
  const r = await chat({ system, json: true, temperature: 0, maxTokens: 300, messages: [{ role: 'user', content: text }] });
  const j = json(r.text);
  if (!j) throw fail('Muse returned no verdict', 502);
  const k = EN(e) ? 2.5 : 1;
  return { covered: l.steps.map((_, i) => j.covered?.[i] === true), wrong: clip(j.wrong, 60 * k), say: clip(j.say, 200 * k), model: r.model };
}

export async function tutor({ exhibit: id, answer, history = [], known = [], focus, lang }) {
  const e = exhibit(id, lang), part = e.parts.find((p) => p.id === focus);
  if (EN(e)) return tutorEn(e, part, answer, history, known);
  const course = (e.lessons || []).map((l) => `${l.title}：${l.steps.map((s) => s.say).join(' ')}`).join('\n');
  const record = known.length ? known.map((k) => `${k.concept}：${{ right: '懂了', partial: '半懂', wrong: '答錯' }[k.verdict]}`).join('、') : '第一次上課';
  const system = `你是「${e.title || e.name}」3D 模型旁的機械家教，用蘇格拉底式教法：不直接給答案，用問題帶學生自己推理，再動模型讓他親眼確認。
每一輪都在同一個回覆裡一起呼叫多個工具：grade（學生有回答時）＋動模型的工具＋ask，三樣都要有。
1. 學生剛回答就呼叫 grade。口語、錯字、講得不完整都看意思評。
2. 用工具動模型給他看：isolate 相關零件，有連動就 drive，要看清楚就 detach，整段 3–10 秒。
3. 呼叫 ask 問下一題。答對就往下一層因果走、加深；半對或答錯就把同一個概念拆小再問。每題都附 choices。
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
async function tutorEn(e, part, answer, history, known) {
  const course = (e.lessons || []).map((l) => `${l.title}: ${l.steps.map((s) => s.say).join(' ')}`).join('\n');
  const record = known.length ? known.map((k) => `${k.concept}: ${{ right: 'understood', partial: 'half understood', wrong: 'got it wrong' }[k.verdict]}`).join('; ') : 'first lesson';
  const system = `You are a mechanics tutor beside a 3D model of the ${e.title || e.name}. Teach the Socratic way: don't give the answer, lead the student to reason it out with questions, then move the model so they see it for themselves.
Every turn, call several tools in the same reply: grade (when the student has answered) + the model tools + ask. All three every time.
1. When the student has just answered, call grade. Judge casual speech, typos and incomplete answers by meaning.
2. Show it on the model with the tools: isolate the relevant parts, drive for linked motion, detach to see clearly; 3–10 seconds in all.
3. Call ask with the next question. Right: go one level deeper along the chain of cause and effect. Half right or wrong: break the same concept into a smaller question. Every question comes with choices.
4. Your text reply is read aloud. Talk straight to the student (use "you") in plain spoken English, at most 35 words: first respond to their answer (what was right, what was missing); don't repeat the question. Only use numbers that appear in the data below.
The student's record: ${record}. Teach concepts they have never learned or got wrong first.${part ? `\nThey just photographed a real ${part.name}; start from the ${part.name}.` : ''}
Parts (id=name: description):
${partList(e)}
Syllabus (the correct cause and effect):
${course}`;
  const user = answer ? `My answer: ${answer}` : 'Start the lesson. Ask me the first question.';
  const r = await chat({ system, tools: tutorTools(e), maxTokens: 900, messages: [...history.slice(-6), { role: 'user', content: user }] });
  return { say: r.text.slice(0, 400), ...cleanTurn(r.calls, e), model: r.model };
}

// ---------- 修理挑戰: the model is broken (manifest fault); the learner guesses, Muse checks the guess on the model ----------
// stage 'diagnose': grade the guess (found / close / not_it) and show the suspected parts moving (or not) under the fault.
// stage 'explain': the fault is repaired; grade the learner's "why", replay the chain, and pick the next challenge.
const RESULTS = ['found', 'close', 'not_it'];
const faultKeys = () => Object.values(exhibits()).flatMap((e) => (e.faults || []).map((f) => `${e.id}/${f.id}`));
export function fixTools(e, stage) {
  const parts = { type: 'array', items: { type: 'string', enum: e.parts.map((p) => p.id) } };
  if (EN(e)) return [...toolsFor(e), stage === 'diagnose'
    ? { name: 'check', description: "Call every turn: judge the student's guess", parameters: { type: 'object', required: ['result'], properties: {
        result: { type: 'string', enum: RESULTS, description: 'found=named the broken part or the real cause; close=what they suspect is on the same drive path, right direction; not_it=no' },
        suspect: { ...parts, description: 'ids of the parts the student suspects' } } } }
    : { name: 'grade', description: "Call every turn: grade the student's explanation", parameters: { type: 'object', required: ['verdict'], properties: {
        verdict: { type: 'string', enum: VERDICTS, description: 'right=says how the force travels and where it breaks; partial=right direction but misses the key point; wrong=wrong or a misconception' },
        gap: { type: 'string', description: 'the missing key point, at most 15 words; empty when right' },
        next: { type: 'string', enum: faultKeys(), description: "when right, pick the next challenge: ones not yet fixed first, the student's weak concepts first" } } } }];
  return [...toolsFor(e), stage === 'diagnose'
    ? { name: 'check', description: '每一輪都要呼叫：判斷學生的猜測', parameters: { type: 'object', required: ['result'], properties: {
        result: { type: 'string', enum: RESULTS, description: 'found=指出了壞的零件或真正原因；close=懷疑的地方在同一條傳動路線上、方向對；not_it=不是' },
        suspect: { ...parts, description: '學生懷疑的零件 id' } } } }
    : { name: 'grade', description: '每一輪都要呼叫：評學生的解釋', parameters: { type: 'object', required: ['verdict'], properties: {
        verdict: { type: 'string', enum: VERDICTS, description: 'right=講出力量怎麼傳、哪裡斷掉；partial=方向對但漏了關鍵；wrong=錯或有迷思' },
        gap: { type: 'string', description: '漏掉的關鍵，≤ 30 字；答對留空' },
        next: { type: 'string', enum: faultKeys(), description: '答對時挑下一題：先挑沒修過的，學生弱的概念優先' } } } }];
}
export function cleanFix(calls, e, stage) {
  const c = calls.find((x) => x.name === (stage === 'diagnose' ? 'check' : 'grade'))?.args || {}, ids = new Set(e.parts.map((p) => p.id));
  const out = { steps: cleanSteps(calls, e) };
  if (stage === 'diagnose') Object.assign(out, { result: RESULTS.includes(c.result) ? c.result : 'not_it', suspect: (Array.isArray(c.suspect) ? c.suspect : []).filter((p) => ids.has(p)).slice(0, 4) });
  else Object.assign(out, { grade: VERDICTS.includes(c.verdict) ? { verdict: c.verdict, gap: clip(c.gap, EN(e) ? 150 : 60) } : null, next: faultKeys().includes(c.next) ? c.next : null });
  return out;
}
// Muse writes its line before it runs the tools, so a miss often ends with no clue: fall back on the exhibit's own question (an empty line gets it too)
export const withClue = (say, f, result) => (!result || result === 'found' || /[？?]/.test(say) ? say : [say, f.observe].filter(Boolean).join(' '));
// a miss must not name the fault; the lookarounds keep "chain" from matching "chainring"
export const leaks = (say, e, f) => f.broken.flatMap((id) => { const p = e.parts.find((x) => x.id === id); return p ? [p.name, ...(p.aliases || [])] : []; }).some((n) => new RegExp(`(?<![a-z])${n.replace(/[^\p{L}\p{N} -]/gu, '.')}(?![a-z])`, 'i').test(say));
// That first line comes before the tools run, so it can only be a plan. With the check made, a second call says what the model showed.
// The answer was already earned by the first call: any failure here keeps it (and its clue) rather than failing the turn.
async function afterTools({ system, messages, out, stage, f, e, name, first, max }) {
  const en = EN(e), shown = out.steps.map((s) => (s.parts ? `${s.do} ${s.parts.map(name).join(en ? ', ' : '、')}` : `${s.do} ${s.drive || ''}`.trim())).join(en ? '; ' : '；') || (en ? 'nothing' : '沒有');
  const result = stage === 'diagnose'
    ? (en ? `Check result: ${out.result}. Shown on the model: ${shown}. While it ran, these parts stayed still: ${f.stops.map(name).join(', ')}. Everything else moved normally.` : `檢查結果：${out.result}。模型上演的：${shown}。運轉時這些零件停著：${f.stops.map(name).join('、')}。其他零件都正常。`)
    : (en ? `Grade: ${out.grade?.verdict || 'partial'}. Missing: ${out.grade?.gap || 'nothing'}. Shown on the model: ${shown}.` : `評分：${out.grade?.verdict || 'partial'}。漏掉的：${out.grade?.gap || '沒有'}。模型上演的：${shown}。`);
  const say = en ? 'The tools have run. Do not call tools. Write only your spoken line under rule 3, in the past tense, about what the model showed.' : '工具已經跑完。不要再呼叫工具。只寫第 3 條的那句話，用已經做完的語氣，講模型呈現了什麼。';
  const text = await retried((content) => chat({ system: `${system}\n${say}`, maxTokens: 150, ms: 8000, messages: [...messages, { role: 'user', content }] }), result, en ? 'Say your line now.' : '請說出你的那句話。').then((r) => r.text, (err) => (console.warn(`fix: second call failed: ${String(err.message).slice(0, 80)}`), ''));
  const missed = stage === 'diagnose' && out.result !== 'found';
  if (text && !(missed && (leaks(text, e, f) || !/[？?]/.test(text)))) return text.slice(0, max);
  return withClue(missed && leaks(first, e, f) ? '' : first.slice(0, max), f, out.result);
}
export async function fix({ exhibit: id, fault, stage, text, pointed, history = [], solved = [], lang }) {
  const e = exhibit(id, lang), f = (e.faults || []).find((x) => x.id === fault);
  if (!f) throw fail('unknown fault');
  if (!['diagnose', 'explain'].includes(stage)) throw fail('unknown stage');
  const name = (p) => e.parts.find((x) => x.id === p)?.name || p, drive = e.drives.find((d) => d.id === f.drive);
  if (EN(e)) return fixEn(e, f, stage, text, pointed, history, solved, name, drive);
  const common = `零件（id=名稱：說明）：
${e.parts.map((p) => `${p.id}=${p.name}${p.info ? '：' + p.info : ''}`).join('\n')}
這題的機構「${drive?.name || f.drive}」依序帶動：${(drive?.moves || []).map((m) => name(m.part)).join(' → ')}`;
  const system = stage === 'diagnose'
    ? `你是「${e.title || e.name}」3D 模型旁的修理教練。模型現在故障了，學生看到的症狀：${f.symptom}
真正的故障（不能直接說出來）：${f.title}。${f.cause} 壞的零件：${f.broken.map(name).join('、')}。故障時不會動的零件：${f.stops.map(name).join('、')}。
學生會說出他的猜測，口語、錯字照意思理解。所有工具都要在這一個回覆裡一次呼叫完：模型運轉前不會有工具結果回來。每一輪在同一個回覆裡，以下全部都要做：
1. 呼叫 check 判斷他的猜測，suspect 填他懷疑的零件。
2. 用工具在模型上檢查他懷疑的地方給他看：isolate 那些零件；用 drive 讓他看它們有沒有在動（模型照故障的狀態運轉，不會動的零件會停著）；要看清楚就 detach。整段 3–8 秒。not_it 或 close 時不可以 detach 壞的零件，也不可以只亮它，那等於直接給答案。
3. 文字回覆會被唸出來，直接對學生說（用「你」），台灣繁體中文口語 ≤ 50 字：說你檢查了什麼、看到什麼（哪個零件有轉、哪個停著），不要只說「我來看看」。not_it 或 close 最後一定要用一個問題給線索（沿著力量傳過去的路線往下找），絕對不要說出答案。found 就稱讚他，說出他找到的是什麼。
${common}`
    : `你是「${e.title || e.name}」3D 模型旁的修理教練。學生剛找出故障「${f.title}」，模型已經修好了。你問他：${f.why}
正確的解釋：${f.answer}
所有工具都要在這一個回覆裡一次呼叫完：模型運轉前不會有工具結果回來。每一輪在同一個回覆裡，以下全部都要做：
1. 呼叫 grade 評他的解釋，口語、錯字照意思評。答對時 next 挑下一題（他修過的：${solved.join('、') || '還沒有'}）。
2. 用工具動模型把這條傳動路線演一次：isolate 相關零件，再 drive，3–8 秒。
3. 文字回覆會被唸出來，直接對學生說（用「你」），台灣繁體中文口語 ≤ 60 字：先說他講對的，再補漏掉的那一環。
${common}`;
  const user = stage === 'diagnose' ? `我的猜測：${text}${pointed ? `（我點了：${name(pointed)}）` : ''}` : `我的解釋：${text}`;
  const messages = [...history.slice(-4), { role: 'user', content: user }];
  const r = await chat({ system, tools: fixTools(e, stage), maxTokens: 900, messages });
  const out = cleanFix(r.calls, e, stage);
  return { say: await afterTools({ system, messages: [...messages, ...(r.text ? [{ role: 'assistant', content: r.text }] : [])], out, stage, f, e, name, first: r.text, max: 200 }), ...out, model: r.model };
}
async function fixEn(e, f, stage, text, pointed, history, solved, name, drive) {
  const common = `Parts (id=name: description):
${partList(e)}
The mechanism in this challenge, "${drive?.name || f.drive}", drives in order: ${(drive?.moves || []).map((m) => name(m.part)).join(' → ')}`;
  const system = stage === 'diagnose'
    ? `You are a repair coach beside a 3D model of the ${e.title || e.name}. The model is broken right now. The symptom the student sees: ${f.symptom}
The real fault (never say it outright): ${f.title}. ${f.cause} Broken parts: ${f.broken.map(name).join(', ')}. Parts that stop moving because of the fault: ${f.stops.map(name).join(', ')}.
The student will say a guess; understand casual speech and typos by meaning. Make every tool call in this one reply: no tool results come back before the model runs. Every turn, in the same reply, all of these:
1. Call check to judge the guess; put the parts they suspect in suspect.
2. Check the suspected spot on the model with the tools: isolate those parts; use drive so they can see whether the parts move (the model runs in its broken state, so the stopped parts stay still); detach to see clearly. 3–8 seconds in all. For not_it or close, never detach the broken part or light it up alone: that gives the answer away.
3. Your text reply is read aloud. Talk straight to the student (use "you") in plain spoken English, at most 30 words: say what you checked and what you saw (which part turned, which stayed still), not just "let me look". For not_it or close, always end on a clue as a question (follow the path the force travels), and never give the answer away. For found, praise them and name what they found.
${common}`
    : `You are a repair coach beside a 3D model of the ${e.title || e.name}. The student has just found the fault "${f.title}" and the model is repaired. You asked them: ${f.why}
The correct explanation: ${f.answer}
Make every tool call in this one reply: no tool results come back before the model runs. Every turn, in the same reply, all of these:
1. Call grade on their explanation, judging casual speech and typos by meaning. When it is right, pick the next challenge in next (already fixed: ${solved.join(', ') || 'none yet'}).
2. Replay this drive path on the model with the tools: isolate the relevant parts, then drive, 3–8 seconds.
3. Your text reply is read aloud. Talk straight to the student (use "you") in plain spoken English, at most 35 words: first say what they got right, then add the missing link.
${common}`;
  const user = stage === 'diagnose' ? `My guess: ${text}${pointed ? ` (I tapped: ${name(pointed)})` : ''}` : `My explanation: ${text}`;
  const messages = [...history.slice(-4), { role: 'user', content: user }];
  const r = await chat({ system, tools: fixTools(e, stage), maxTokens: 900, messages });
  const out = cleanFix(r.calls, e, stage);
  return { say: await afterTools({ system, messages: [...messages, ...(r.text ? [{ role: 'assistant', content: r.text }] : [])], out, stage, f, e, name, first: r.text, max: 400 }), ...out, model: r.model };
}
