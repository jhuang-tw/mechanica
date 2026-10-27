// App flow: landing → exhibit (tap parts, explode, ask the AI, lessons, quiz) → back. Photo and VR are reachable from both.
import { cleanSteps } from './choreo.js';
import { Recorder, shrink, speak } from './media.js';

// dev only: ?xr emulates a headset (Meta's IWER) so the VR mode can be tried in a desktop browser
if (import.meta.env.DEV && new URLSearchParams(location.search).has('xr')) { const { XRDevice, metaQuest3 } = await import('iwer'); (window.xrDevice = new XRDevice(metaQuest3)).installRuntime({ forceInstall: true }); }   // the desktop browser has its own (headset-less) navigator.xr
const $ = (id) => document.getElementById(id);
const BASE = `${import.meta.env.BASE_URL}exhibits/`;
const viewerModule = import('./viewer.js');   // three.js downloads while the landing page is up
const exhibits = {};   // id -> manifest
let viewer, ex, rig, chat = [], pointed = null, lesson = null, quiz = null, vr = null;

// ---------- landing ----------
const list = (await (await fetch(`${BASE}index.json`)).json()).exhibits;
await Promise.all(list.map(async (id) => (exhibits[id] = await (await fetch(`${BASE}${id}/manifest.json`)).json())));
$('tiles').replaceChildren(...list.map((id) => {
  const e = exhibits[id], b = Object.assign(document.createElement('button'), { className: 'tile', type: 'button' });
  b.innerHTML = `<img alt="" src="${BASE}${id}/${e.thumb}" onerror="this.style.visibility='hidden'"><span></span>`;
  b.querySelector('span').textContent = e.title;
  b.onpointerdown = () => viewerModule.then((m) => m.preload(BASE + id + '/' + e.model));   // start the model download on touch
  b.onclick = () => open(id);
  return b;
}));
const toast = (t, ms = 2500) => { $('toast').textContent = t; $('toast').hidden = !t; clearTimeout(toast.t); if (t) toast.t = setTimeout(() => ($('toast').hidden = true), ms); };

async function open(id) {
  if (!exhibits[id]) return;
  $('home').hidden = true; $('app').hidden = false;
  window.history.replaceState(null, '', `?ex=${id}`);
  if (ex?.id === id) return;
  ex = exhibits[id];
  $('title').textContent = ex.title;
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
function stopAll() { lesson = quiz = null; vr?.refresh(); document.body.classList.remove('lesson'); $('lesson').hidden = $('quiz').hidden = true; viewer?.choreo?.cancel(); rig?.reset(); $('explode-r').value = 0; }
$('reset').onclick = () => { stopAll(); speak(''); viewer.frame(); pointed = null; say(ex.name, ex.intro); };

// ---------- suggestions: AI questions and lessons ----------
function chips() {
  const chip = (cls, label, run) => Object.assign(document.createElement('button'), { className: `chip ${cls}`, type: 'button', textContent: label, onclick: run });
  $('chips').replaceChildren(
    ...ex.lessons.map((l) => chip('lesson', `⛓ ${l.title}`, () => startLesson(l, false))),
    ...(ex.lessons.some((l) => l.steps.some((s) => s.quiz)) ? [chip('lesson', '❓ 先猜再看', () => startLesson(ex.lessons.find((l) => l.steps.some((s) => s.quiz)), true))] : []),
    ...ex.suggest.map((q) => chip('ai', `✨ ${q}`, () => ask(q))),
  );
}

// ---------- AI: ask → spoken answer + a demonstration the model composed from the exhibit's parts ----------
async function ask(text) {
  text = text.trim();
  if (!text || !rig) return;
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
    say(local ? local.name : 'AI 暫時連不上', local ? local.info : '可以先試試 ⛓ 因果連動，或點零件看說明。', false, true);
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
  try { await rec.start(); $('mic').classList.add('rec'); toast('說吧，放開就送出'); vr?.say('🎤 說吧，說完按 ⏹'); if (!holding) release(); }
  catch { holding = false; toast('沒有麥克風權限，改用 ⌨ 打字'); vr?.say('沒有麥克風權限'); }
};
$('mic').onpointerdown = (e) => { e.preventDefault(); talk(); };
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
  } catch { say('', '語音暫時不能用，改用 ⌨ 打字。'); }
};
for (const ev of ['pointerup', 'pointercancel', 'pointerleave']) $('mic').addEventListener(ev, release);

// ---------- 因果連動 / 先猜再看: manifest lessons, one cause → effect per step ----------
function startLesson(l, quiz) { stopAll(); lesson = { l, quiz, i: 0 }; document.body.classList.add('lesson'); $('lesson').hidden = false; showStep(); }
function showStep() {
  const { l, quiz: guess, i } = lesson, s = l.steps[i];
  $('l-step').textContent = `${l.title} · ${i + 1}/${l.steps.length}`;
  $('l-prev').disabled = i === 0;
  if (guess && s.quiz) askQuiz(s); else playStep(s);
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
const go = (d) => { if (!lesson) return; const n = lesson.i + d; if (n < 0) return; if (n >= lesson.l.steps.length) { stopAll(); return say('完成', '這一套看完了。可以再問 AI，或換一套。', false, true); } lesson.i = n; showStep(); };
$('l-next').onclick = () => go(1);
$('l-prev').onclick = () => go(-1);
$('l-stop').onclick = () => { stopAll(); say(ex.name, ex.intro); };

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
    setTimeout(() => ask(part ? `讓我看${part.name}怎麼運作` : `讓我看${ex.name}怎麼動`), 3500);
  } catch { toast('現在認不出來，再拍一次試試', 4000); }
};

// ---------- VR (optional) ----------
// what the VR menu and panels can reach
const app = {
  list: list.map((id) => ({ id, thumb: `${BASE}${id}/${exhibits[id].thumb}`, title: exhibits[id].name })),
  get ex() { return ex; }, get rig() { return rig; }, get lesson() { return lesson; }, get quiz() { return quiz; }, get recording() { return holding; },
  open, pick, go, answer, startLesson,
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
addEventListener('pointerdown', () => speechSynthesis?.speak(new SpeechSynthesisUtterance('')), { once: true });
const start = new URLSearchParams(location.search).get('ex');
if (exhibits[start]) open(start);
