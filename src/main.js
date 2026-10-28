// App flow: landing → exhibit (tap parts, explode, ask the AI, lessons, quiz) → back. Photo and VR are reachable from both.
import { cleanSteps } from './choreo.js';
import { Recorder, shrink, speak, unlockSpeech } from './media.js';

// dev only: ?xr emulates a headset (Meta's IWER) so the VR mode can be tried in a desktop browser
if (import.meta.env.DEV && new URLSearchParams(location.search).has('xr')) { const { XRDevice, metaQuest3 } = await import('iwer'); (window.xrDevice = new XRDevice(metaQuest3)).installRuntime({ forceInstall: true }); }   // the desktop browser has its own (headset-less) navigator.xr
const $ = (id) => document.getElementById(id);
const BASE = `${import.meta.env.BASE_URL}exhibits/`;
const viewerModule = import('./viewer.js');   // three.js downloads while the landing page is up
const exhibits = {};   // id -> manifest
let viewer, ex, rig, chat = [], pointed = null, lesson = null, quiz = null, vr = null, tutor = null, explain = null, flow;   // flow: the 連貫 caption timer

// ---------- landing ----------
const list = (await (await fetch(`${BASE}index.json`)).json()).exhibits;
await Promise.all(list.map(async (id) => (exhibits[id] = await (await fetch(`${BASE}${id}/manifest.json`)).json())));
const icon = (id) => `<svg class="i"><use href="#i-${id}"/></svg>`;
const thumb = (id) => `${BASE}${id}/${exhibits[id].thumb}`;
const warm = (id) => viewerModule.then((m) => m.preload(BASE + id + '/' + exhibits[id].model));   // start the model download on touch
$('tiles').replaceChildren(...list.map((id, i) => {
  const e = exhibits[id], b = Object.assign(document.createElement('button'), { className: 'tile', type: 'button' });
  b.innerHTML = `<span class="well"><span class="n"></span><img alt="" loading="${i < 4 ? 'eager' : 'lazy'}" src="${thumb(id)}" onerror="this.style.visibility='hidden'"></span><span class="body"><b></b><small></small><span class="first">${icon('book')}<span></span></span></span>`;
  b.querySelector('.n').textContent = `${e.lessons?.length || 0} 堂課`;
  b.querySelector('b').textContent = e.name;
  b.querySelector('small').textContent = e.title;
  b.querySelector('.first span').textContent = e.lessons?.[0]?.title || '點零件看說明';
  b.onpointerdown = () => warm(id);
  b.onclick = () => open(id);
  return b;
}));
// hero: the first exhibit is the way in, its first lesson one tap away
{
  const id = list[0], e = exhibits[id], parts = e.parts.filter((p) => !p.fixed);
  const lessons = list.reduce((n, x) => n + (exhibits[x].lessons?.length || 0), 0);
  $('stats').textContent = `${list.length} 台機器 · ${lessons} 堂課 · 免安裝`;
  $('count').textContent = `${list.length} 台`;
  $('feature-img').src = thumb(id);
  $('feature-name').textContent = e.title;
  $('feature-lesson').textContent = e.lessons?.[0] ? `第一課：${e.lessons[0].title}` : e.intro;
  // shortcut: callout spots are placed for the bike thumbnail; move them if another exhibit leads
  $('co1').textContent = (e.parts.find((p) => p.id === 'saddle') || parts[0]).name;
  $('co2').textContent = (e.parts.find((p) => p.id === 'handlebar') || parts[1]).name;
  const begin = async () => { await open(id); if (ex.lessons?.[0]) startLesson(ex.lessons[0], true); };
  $('start').onpointerdown = $('feature').onpointerdown = () => warm(id);
  $('start').onclick = $('feature').onclick = begin;
  $('browse').onclick = () => $('all').scrollIntoView({ behavior: 'smooth' });
}
const toast = (t, ms = 2500) => { $('toast').textContent = t; $('toast').hidden = !t; clearTimeout(toast.t); if (t) toast.t = setTimeout(() => ($('toast').hidden = true), ms); };

async function open(id) {
  if (!exhibits[id]) return;
  $('home').hidden = true; $('app').hidden = false;
  window.history.replaceState(null, '', `?ex=${id}`);
  if (ex?.id === id) return;
  ex = exhibits[id];
  $('title').textContent = ex.name; $('subtitle').textContent = ex.title;
  say('', '載入中…', true);
  const { Viewer } = await viewerModule;
  viewer ||= new Viewer($('c'), { onPick: pick, panel: $('sheet') });
  if (import.meta.env.DEV) window.viewer = viewer;   // dev: poke at it from the console
  viewer.resize();
  rig = await viewer.load(ex, `${BASE}${id}/`);
  chat = []; pointed = null;
  chips();
  say(ex.name, ex.intro);
  $('vr').hidden = !(await Viewer.vrSupported());
}
function home() { stopAll(); speak(''); $('app').hidden = true; $('home').hidden = false; window.history.replaceState(null, '', location.pathname); }
$('back').onclick = home;

// ---------- caption ----------
function say(title, text, thinking = false, voice = false) {
  $('cap-title').textContent = title; $('cap-text').textContent = text;
  $('caption').classList.toggle('thinking', thinking);
  if (voice) speak(text);
  vr?.say(text);
}

// ---------- parts ----------
function pick(id) {
  if (!rig || lesson) return;
  pointed = id;
  if (!id) { rig.highlight([]); return; }
  const p = ex.parts.find((x) => x.id === id);
  rig.highlight([id]);
  say(p.name, p.info, false, true);
}
$('explode-r').oninput = (e) => rig?.setExplode(+e.target.value);
function stopAll() { clearTimeout(flow); stopRide(); if (viewer) viewer.lessonMode = false; lesson = quiz = tutor = explain = null; vr?.refresh(); document.body.classList.remove('lesson', 'tutor'); $('lesson').hidden = $('quiz').hidden = $('tutor').hidden = true; $('q').placeholder = '問任何問題…'; viewer?.choreo?.cancel(); rig?.reset(); $('explode-r').value = 0; }
$('reset').onclick = () => { stopAll(); speak(''); viewer.frame(); pointed = null; say(ex.name, ex.intro); };

// ---------- suggestions: AI questions and lessons ----------
function chips() {
  const chip = (cls, label, run) => { const b = Object.assign(document.createElement('button'), { className: `chip ${cls}`, type: 'button', onclick: run }); b.innerHTML = icon({ lesson: 'book', quiz: 'q', ai: 'spark', ask: 'spark', tutor: 'cap' }[cls.split(' ').pop()]) + '<span></span>'; b.lastChild.textContent = label; return b; };
  $('ai-chips').replaceChildren(chip('ai ask tutor', 'AI 家教', () => startTutor()), chip('ai', '問 AI 老師', () => $('type').onclick()), ...ex.suggest.map((q) => chip('ai', q, () => ask(q))));
  $('chips').replaceChildren(
    ...(ex.ride ? [chip('lesson', '坐上去', startRide)] : []),
    ...ex.lessons.map((l) => chip('lesson', l.title, () => startLesson(l, false))),
    ...(ex.lessons.some((l) => l.steps.some((s) => s.quiz)) ? [chip('lesson quiz', '先猜再看', () => startLesson(ex.lessons.find((l) => l.steps.some((s) => s.quiz)), true))] : []),
  );
}

// ---------- AI: ask → spoken answer + a demonstration the model composed from the exhibit's parts ----------
async function ask(text) {
  text = text.trim();
  if (!text || !rig) return;
  if (explain) return explainBack(text);   // while the tutor or the explain-back check runs, the mic and the keyboard answer it
  if (tutor) return tutorTurn(text);
  stopAll();
  say('你問', text, true);
  try {
    const res = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exhibit: ex.id, text, pointed, history: chat }), signal: AbortSignal.timeout(30000) });
    const r = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(r.error || `HTTP ${res.status}`);
    chat = [...chat, { role: 'user', content: text }, { role: 'assistant', content: r.say }].slice(-6);
    say('AI', r.say, false, true);
    const steps = cleanSteps(r.steps, ex);
    if (steps.length) viewer.choreo.play(steps);
  } catch (e) {
    const local = offline(text);
    say(local ? local.name : 'AI 暫時連不上', local ? local.info : '可以先上一堂課，或點零件看說明。', false, true);
    if (local) rig.isolate([local.id]);
    console.warn('ask failed:', e.message);
  }
}
// without the AI: a question that names a part still gets that part
const offline = (text) => ex.parts.find((p) => [p.name, ...p.aliases].some((n) => text.includes(n)));

$('type').onclick = () => { $('ask').hidden = !$('ask').hidden; if (!$('ask').hidden) $('q').focus(); };
$('ask').onsubmit = (e) => { e.preventDefault(); ask($('q').value); $('q').value = ''; $('ask').hidden = true; };

// hold to talk
const rec = new Recorder();
let holding = false;
const talk = async () => {
  holding = true; speak('');
  try { await rec.start(); $('mic').classList.add('rec'); toast(tapMode ? '說完再點一下送出' : '說吧，放開就送出'); vr?.say('🎤 說吧，說完按 ⏹'); if (!holding) release(); }
  catch { holding = false; toast('沒有麥克風權限，改用鍵盤打字'); vr?.say('沒有麥克風權限'); }
};
let tapMode = false, downAt = 0;
$('mic').onpointerdown = (e) => { e.preventDefault(); if (holding) return release(); downAt = Date.now(); tapMode = false; talk(); };
// a quick tap keeps recording until the next tap; a long press sends on release
const lift = () => { if (!holding) return; if (Date.now() - downAt < 400) { tapMode = true; return toast('說完再點一下送出', 20000); } release(); };
const release = async () => {
  if (!holding) return;
  holding = false; $('mic').classList.remove('rec'); toast('');
  const wav = await rec.stop();
  if (!wav) return toast('太短了，按住久一點');
  say('你說', '聽寫中', true);
  try {
    const res = await fetch(`/api/stt?exhibit=${ex.id}`, { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav, signal: AbortSignal.timeout(20000) });
    const { text } = await res.json();
    if (text) ask(text); else say('', '沒聽清楚，再說一次？');
  } catch { say('', '語音暫時不能用，改用鍵盤打字。'); }
};
for (const ev of ['pointerup', 'pointercancel']) $('mic').addEventListener(ev, () => { if (!tapMode) lift(); });

// ---------- 因果連動 / 先猜再看: manifest lessons, one cause → effect per step ----------
function startLesson(l, quiz) { stopAll(); lesson = { l, quiz, i: 0 }; Object.assign(viewer, { lessonMode: true, userView: false }); document.body.classList.add('lesson'); $('lesson').hidden = false; showStep(); }
function showStep() {
  const { l, quiz: guess, i } = lesson, s = l.steps[i];
  $('l-step').textContent = `${l.title} · ${i + 1}/${l.steps.length}`;
  $('l-step').style.setProperty('--p', `${((i + 1) / l.steps.length) * 100}%`);
  $('l-prev').disabled = i === 0 && !lesson.all;
  $('l-all').textContent = lesson.all ? '分步' : '連貫';
  if (lesson.all) flowStep(); else if (guess && s.quiz) askQuiz(s); else playStep(s);
  vr?.refresh();
}
function playStep(s) {
  $('quiz').hidden = true; quiz = null;
  viewer.choreo.cancel(); rig.stop();
  rig.isolate(s.parts);
  for (const d of [].concat(s.drive || [])) rig.drive(d, s.speed ?? 0.5);   // a step can run several drives (rotor turning while the stick moves)
  say(`第 ${lesson.i + 1} 步`, s.say, false, true);
}
function askQuiz(s) {
  rig.isolate(s.parts); rig.stop();
  say('先猜猜看', s.quiz.q, false, true);
  quiz = s.quiz.options; $('quiz').hidden = false;
  $('quiz').replaceChildren(...quiz.map(([text], i) => Object.assign(document.createElement('button'), { type: 'button', textContent: text, onclick: () => answer(i) })));
}
function answer(i) {
  if (!quiz || !lesson) return;
  const [, right, why] = quiz[i], s = lesson.l.steps[lesson.i];
  quiz = null; vr?.refresh();
  for (const b of $('quiz').children) b.disabled = true;
  $('quiz').children[i].classList.add(right ? 'right' : 'wrong');
  say(right ? '答對了！' : '再想想', why, false, true);
  setTimeout(() => lesson && playStep(s), 2600);
}
// 連貫: every step's parts and drives at once, the captions walking through the chain and starting over

function playAll() {
  const steps = lesson.l.steps, drives = new Map();
  clearTimeout(flow); lesson.all = true; $('quiz').hidden = true; quiz = null;
  viewer.choreo.cancel(); rig.stop();
  rig.isolate([...new Set(steps.flatMap((s) => s.parts))]);
  for (const s of steps) for (const d of [].concat(s.drive || [])) drives.set(d, s.speed ?? 0.5);   // a drive two steps share runs once, at the later step's speed
  for (const [d, v] of drives) rig.drive(d, v);
  showStep();
}
function flowStep() {
  const { l, i } = lesson, s = l.steps[i];
  rig.highlight(s.parts);
  say(`第 ${i + 1} 步`, s.say, false, true);
  clearTimeout(flow);
  flow = setTimeout(() => { if (lesson?.all) { lesson.i = (i + 1) % l.steps.length; showStep(); } }, 2500 + s.say.length * 220);   // roughly the time to read or hear it
}
// ---------- 坐上去: first person on a vehicle, throttle and gears with the real rpm and speed ----------
let ride = null;
async function startRide() {
  stopAll();
  const { Ride } = await import('./ride.js');
  ride = viewer.ride ||= new Ride(viewer);
  ride.start(ex.ride);
  document.body.classList.add('riding'); $('ride').hidden = false;
  $('r-gears').replaceChildren(...ex.ride.gears.map((_, i) => Object.assign(document.createElement('button'), { type: 'button', textContent: `${i + 1}`, ariaLabel: `${i + 1} 檔`, onclick: () => { ride.gear(i); rideRead(); } })));
  $('r-thr').value = ride.thr; $('r-see').setAttribute('aria-pressed', 'false');
  rideRead();
  say('坐上去', ex.ride.hint, false, true);
}
function rideRead() {
  const r = ride.read;
  $('r-read').textContent = `${r.gear} 檔 · 引擎 ${r.rpm} rpm · 時速 ${r.kmh} km/h`;
  [...$('r-gears').children].forEach((b, i) => b.classList.toggle('on', i === ride.g));
}
function stopRide() { if (!ride) return; ride.stop(); ride = null; document.body.classList.remove('riding'); $('ride').hidden = true; }
$('r-thr').oninput = (e) => { if (ride) { ride.throttle(+e.target.value); rideRead(); } };
$('r-see').onclick = (e) => { if (!ride) return; ride.xray(!ride.see); e.currentTarget.setAttribute('aria-pressed', String(ride.see)); };
$('r-stop').onclick = () => { stopAll(); say(ex.name, ex.intro); };
const go = (d) => {
  if (!lesson) return;
  const n = lesson.i + d, len = lesson.l.steps.length;
  if (lesson.all) { lesson.i = (n + len) % len; return showStep(); }
  if (n < 0) return; if (n >= len) return startExplain(lesson.l); lesson.i = n; showStep();
};
$('l-all').onclick = () => { if (!lesson) return; if (lesson.all) { lesson.all = false; rig.stop(); showStep(); } else playAll(); };
$('l-next').onclick = () => go(1);
$('l-prev').onclick = () => go(-1);
$('l-stop').onclick = () => { stopAll(); say(ex.name, ex.intro); };

// ---------- AI 家教: Muse asks, grades the free-form answer, shows it on the model and adapts the next question ----------
// The learner's record (concept → last verdict) stays in this browser and goes with every turn, so a return visit starts from the weak spots.
const VERDICT = { right: '答對了', partial: '對一半', wrong: '再想想' };
// one compact card while the tutor runs (the caption is hidden): a coloured verdict word, then what the AI said
const feedback = (cls, label, text) => { $('t-v').className = cls; $('t-v').replaceChildren(...(label ? [Object.assign(document.createElement('b'), { textContent: label }), ' '] : []), text); };
const record = (id) => { try { return JSON.parse(localStorage.getItem(`mechanica.tutor.${id}`)) || []; } catch { return []; } };
function remember(g) {
  const k = [...record(ex.id).filter((x) => x.concept !== g.concept), { concept: g.concept, verdict: g.verdict }].slice(-12);
  try { localStorage.setItem(`mechanica.tutor.${ex.id}`, JSON.stringify(k)); } catch { /* private mode: this visit only */ }
}
function startTutor(focus) {
  if (!rig) return;
  stopAll(); speak('');
  tutor = { history: [], n: 0, right: 0 };
  document.body.classList.add('tutor'); $('tutor').hidden = false; $('q').placeholder = '輸入你的答案…';
  $('t-bar').textContent = 'AI 家教'; $('t-show').textContent = '不會，示範給我看';
  tutorTurn('', focus);
}
async function tutorTurn(answer, focus) {
  const t = tutor;
  if (!t || t.busy) return;
  t.busy = true; viewer.choreo.cancel(); speak('');
  feedback('', '', ''); $('t-q').textContent = answer ? `你答：${answer}` : '準備第一題'; $('t-choices').replaceChildren(); $('t-hint').hidden = true; $('tutor').classList.add('thinking');
  say('AI 家教', answer ? '看看你答得怎麼樣' : '準備第一題', true);
  const user = answer ? `我的回答：${answer}` : '開始上課，先問我第一題。';
  try {
    const res = await fetch('/api/tutor', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exhibit: ex.id, answer, history: t.history, known: record(ex.id), focus }), signal: AbortSignal.timeout(30000) });
    const r = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(r.error || `HTTP ${res.status}`);
    if (tutor !== t) return;
    if (r.grade) { t.n++; t.right += r.grade.verdict === 'right'; remember(r.grade); }
    const q = r.question?.q || '還有哪個零件你想弄懂？';
    t.history = [...t.history, { role: 'user', content: user }, { role: 'assistant', content: `${r.say} 問：${q}` }].slice(-6);
    $('t-bar').textContent = t.n ? `AI 家教 · 答對 ${t.right}/${t.n}` : 'AI 家教';
    feedback(r.grade?.verdict || '', r.grade ? VERDICT[r.grade.verdict] : '', r.say);
    $('t-q').textContent = q;
    $('t-choices').replaceChildren(...(r.question?.choices || []).map((c) => Object.assign(document.createElement('button'), { type: 'button', textContent: c, onclick: () => tutorTurn(c) })));
    $('t-hint').hidden = t.n > 0 || !!r.question?.choices?.length;
    say(r.grade ? VERDICT[r.grade.verdict] : 'AI 家教', r.say);
    speak(`${r.say} ${q}`);
    vr?.say(q);
    const steps = cleanSteps(r.steps, ex);
    if (steps.length) viewer.choreo.play(steps);
  } catch (e) {
    if (tutor === t) feedback('wrong', '連不上', '再回答一次試試，或先上一堂課。');
    console.warn('tutor failed:', e.message);
  } finally { t.busy = false; $('tutor').classList.remove('thinking'); }
}
$('t-show').onclick = () => (explain ? done() : tutorTurn('我不知道，請動模型示範給我看，再問簡單一點的'));
const done = () => { stopAll(); say('完成', '這一套上完了。可以找 AI 家教再練，或換一套。', false, true); };

// ---------- 講一遍給我聽: after a lesson the learner explains it back; Muse marks each cause → effect link, the model replays the missed ones ----------
function startExplain(l) {
  stopAll(); speak('');
  explain = { l };
  document.body.classList.add('tutor'); $('tutor').hidden = false; $('q').placeholder = '用你自己的話講一遍…';
  $('t-bar').textContent = '講一遍給我聽'; $('t-show').textContent = '跳過';
  feedback('', '', ''); $('t-choices').replaceChildren(); $('t-hint').hidden = false;
  $('t-q').textContent = `用你自己的話，從頭講一次「${l.title}」是怎麼動的。`;
  say('最後一關', $('t-q').textContent, false, true);
  vr?.refresh();
}
async function explainBack(text) {
  const x = explain;
  if (!x || x.busy) return;
  x.busy = true; viewer.choreo.cancel(); speak('');
  say('你說', text, true); feedback('', '', ''); $('t-q').textContent = `你說：${text}`; $('t-hint').hidden = true; $('tutor').classList.add('thinking');
  try {
    const res = await fetch('/api/explain', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exhibit: ex.id, lesson: x.l.id, text }), signal: AbortSignal.timeout(30000) });
    const r = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(r.error || `HTTP ${res.status}`);
    if (explain !== x) return;
    const steps = x.l.steps, got = r.covered.filter(Boolean).length, missed = steps.filter((_, i) => !r.covered[i]);
    remember({ concept: x.l.title, verdict: !missed.length ? 'right' : got * 2 >= steps.length ? 'partial' : 'wrong' });   // the tutor starts from what was missed
    feedback(!missed.length ? 'right' : got * 2 >= steps.length ? 'partial' : 'wrong', `講到 ${got}/${steps.length}`, r.say);
    $('t-choices').replaceChildren(...missed.map((s) => Object.assign(document.createElement('div'), { className: 'miss', textContent: s.say })));   // only the missed links, one line each
    $('t-q').textContent = missed.length ? '看模型補上，想再講一次就直接說' : '整條因果鏈都講對了！';
    $('t-show').textContent = '結束';
    say(missed.length ? '還差一點' : '全對', r.say);
    speak(r.say);
    // the model replays only the missed links, one every 4 s
    viewer.choreo.play(cleanSteps(missed.flatMap((s, k) => [{ do: 'isolate', at: k * 4, parts: s.parts }, ...[].concat(s.drive || []).map((d) => ({ do: 'drive', at: k * 4, drive: d, speed: s.speed ?? 0.5, duration: 3.5 }))]), ex));
  } catch (e) {
    if (explain === x) feedback('wrong', '連不上', '再講一次試試，或按跳過。');
    console.warn('explain failed:', e.message);
  } finally { x.busy = false; $('tutor').classList.remove('thinking'); }
}
$('t-stop').onclick = () => { stopAll(); speak(''); say(ex.name, ex.intro); };

// ---------- 📷 a real machine → the matching exhibit, its part lit, and the AI shows how it moves ----------
const photoIn = $('photo-in');
$('photo').onclick = $('home-photo').onclick = () => photoIn.click();
photoIn.onchange = async () => {
  const f = photoIn.files[0]; photoIn.value = '';
  if (!f) return;
  toast('我看看這是什麼…', 20000);
  try {
    const res = await fetch('/api/identify', { method: 'POST', headers: { 'Content-Type': 'image/jpeg' }, body: await shrink(f), signal: AbortSignal.timeout(30000) });
    const r = await res.json();
    toast('');
    if (!res.ok) throw new Error(r.error);
    if (!r.match || !exhibits[r.exhibit]) { if (!$('app').hidden) say('拍到的', r.say, false, true); else toast(r.say, 5000); return; }
    await open(r.exhibit);
    if (r.parts?.length) rig.isolate(r.parts);
    say('拍到的', r.say, false, true);
    const part = ex.parts.find((p) => p.id === r.parts?.[0]);
    setTimeout(() => startTutor(part?.id), 3500);   // the tutor starts its lesson from the part in the photo
  } catch { toast('現在認不出來，再拍一次試試', 4000); }
};

// ---------- VR (optional) ----------
// what the VR menu and panels can reach
const app = {
  list: list.map((id) => ({ id, thumb: `${BASE}${id}/${exhibits[id].thumb}`, title: exhibits[id].name })),
  get ex() { return ex; }, get rig() { return rig; }, get lesson() { return lesson; }, get quiz() { return quiz; }, get recording() { return holding; },
  get tutoring() { return !!(tutor || explain); },
  open, pick, go, answer, startLesson, startTutor: () => startTutor(),
  quizLesson: () => startLesson(ex.lessons.find((l) => l.steps.some((s) => s.quiz)) || ex.lessons[0], true),
  stopLesson: () => { stopAll(); say(ex.name, ex.intro); },
  explode: (v) => { rig.setExplode(v); $('explode-r').value = v; },
  reset: () => $('reset').onclick(),
  talk: (on) => (on ? talk() : release()),
  onExit: () => (vr = null),
};
async function enterVR() {
  try { vr = await viewer.enterVR(app); } catch { vr = null; toast('這個瀏覽器不能進 VR'); }
}
$('vr').onclick = enterVR;
viewerModule.then(async ({ Viewer }) => { if (await Viewer.vrSupported()) $('home-vr').hidden = false; });
$('home-vr').onclick = async () => { await open(ex?.id || list[0]); enterVR(); };

// first sound needs a tap on phones
addEventListener('pointerdown', unlockSpeech, { once: true });
const start = new URLSearchParams(location.search).get('ex');
if (exhibits[start]) open(start);
