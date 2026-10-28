// App flow: straight into a repair challenge (修理: a broken machine, the learner guesses, Muse checks it on the model)
// or 原理 on the same exhibit (tap parts, explode, ask the AI, lessons, quiz, tutor); the landing page picks another machine.
// Photo and VR are reachable from both.
import { cleanSteps } from './choreo.js';
import { Recorder, shrink, speak } from './media.js';
import { t, lang, isEn, applyStatic, switchLang, here } from './i18n.js';
import { localize } from './localize.js';

// dev only: ?xr emulates a headset (Meta's IWER) so the VR mode can be tried in a desktop browser
if (import.meta.env.DEV && new URLSearchParams(location.search).has('xr')) { const { XRDevice, metaQuest3 } = await import('iwer'); (window.xrDevice = new XRDevice(metaQuest3)).installRuntime({ forceInstall: true }); }   // the desktop browser has its own (headset-less) navigator.xr
const $ = (id) => document.getElementById(id);
const BASE = `${import.meta.env.BASE_URL}exhibits/`;
const viewerModule = import('./viewer.js');   // three.js downloads while the landing page is up
const exhibits = {};   // id -> manifest
let viewer, ex, rig, chat = [], pointed = null, lesson = null, quiz = null, vr = null, tutor = null, explain = null, flow;   // flow: the 連貫 caption timer

// ---------- landing ----------
const list = (await (await fetch(`${BASE}index.json`)).json()).exhibits;
applyStatic();
for (const b of document.querySelectorAll('.lang')) { b.textContent = t('switchTo'); b.setAttribute('aria-label', t('switchAria')); b.onclick = switchLang; }
// English: each manifest gets its en.json words laid over it (src/localize.js)
const getJSON = async (u) => { const r = await fetch(u); if (!r.ok) throw new Error(r.status); return r.json(); };
await Promise.all(list.map(async (id) => { const m = await getJSON(`${BASE}${id}/manifest.json`); exhibits[id] = isEn ? localize(m, await getJSON(`${BASE}${id}/en.json`).catch(() => ({}))) : m; }));
const icon = (id) => `<svg class="i"><use href="#i-${id}"/></svg>`;
const thumb = (id) => `${BASE}${id}/${exhibits[id].thumb}`;
const warm = (id) => viewerModule.then((m) => m.preload(BASE + id + '/' + exhibits[id].model));   // start the model download on touch
const faults = list.flatMap((id) => (exhibits[id].faults || []).map((f) => ({ ex: id, f, key: `${id}/${f.id}` })));
const solvedKeys = () => { try { return JSON.parse(localStorage.getItem('mechanica.fixed')) || []; } catch { return []; } };
function tiles() {
  const done = new Set(solvedKeys());
  $('tiles').replaceChildren(...list.map((id, i) => {
    const e = exhibits[id], f = e.faults?.[0], b = Object.assign(document.createElement('button'), { className: 'tile', type: 'button' });
    b.innerHTML = `<span class="well"><span class="n"></span><img alt="" loading="${i < 4 ? 'eager' : 'lazy'}" src="${thumb(id)}" onerror="this.style.visibility='hidden'"></span><span class="body"><b></b><small></small><span class="first">${icon('book')}<span></span></span></span>`;
    const fixed = f && done.has(`${id}/${f.id}`);
    b.querySelector('.n').textContent = fixed ? t('fixed') : t('toFix');
    b.querySelector('.n').classList.toggle('done', !!fixed);
    b.querySelector('b').textContent = e.name;
    b.querySelector('small').textContent = f ? t('symptomShort', f.short) : e.title;
    b.querySelector('.first span').textContent = t('lessonsN', e.lessons?.length || 0);
    b.onpointerdown = () => warm(id);
    b.onclick = () => (f ? startFix(`${id}/${f.id}`) : learn(id));
    return b;
  }));
}
tiles();
const toast = (msg, ms = 2500) => { $('toast').textContent = msg; $('toast').hidden = !msg; clearTimeout(toast.t); if (msg) toast.t = setTimeout(() => ($('toast').hidden = true), ms); };

async function open(id) {
  if (!exhibits[id]) return;
  $('home').hidden = true; $('app').hidden = false;
  window.history.replaceState(null, '', here(`ex=${id}`));
  if (ex?.id === id) return;
  ex = exhibits[id];
  $('title').textContent = ex.name; $('subtitle').textContent = ex.title;
  say('', t('loading'), true);
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
function home() { stopAll(); speak(''); tiles(); $('app').hidden = true; $('home').hidden = false; window.history.replaceState(null, '', here()); }
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
  if (fix) { rig.highlight(id ? [id] : []); const p = ex.parts.find((x) => x.id === id); if (p && fix.stage === 'diagnose') fixTurn(t('pickedPart', p.name), id); return; }
  if (!id) { rig.highlight([]); return; }
  const p = ex.parts.find((x) => x.id === id);
  rig.highlight([id]);
  say(p.name, p.info, false, true);
}
$('explode-r').oninput = (e) => rig?.setExplode(+e.target.value);
function stopAll() { clearTimeout(flow); clearTimeout(symptomT); stopRide(); if (fix) { fix = null; rig?.setFault(null); } document.body.classList.remove('fix'); $('fix').hidden = true; if (viewer) viewer.lessonMode = false; lesson = quiz = tutor = explain = null; vr?.refresh(); document.body.classList.remove('lesson', 'tutor'); $('lesson').hidden = $('quiz').hidden = $('tutor').hidden = true; $('q').placeholder = t('askPh'); viewer?.choreo?.cancel(); rig?.reset(); $('explode-r').value = 0; }
$('reset').onclick = () => { if (fix) { viewer.frame(); return symptom(); } stopAll(); speak(''); viewer.frame(); pointed = null; say(ex.name, ex.intro); };

// ---------- suggestions: AI questions and lessons ----------
function chips() {
  const chip = (cls, label, run) => { const b = Object.assign(document.createElement('button'), { className: `chip ${cls}`, type: 'button', onclick: run }); b.innerHTML = icon({ lesson: 'book', quiz: 'q', ai: 'spark', ask: 'spark', tutor: 'cap' }[cls.split(' ').pop()]) + '<span></span>'; b.lastChild.textContent = label; return b; };
  // 原理: one row, the lessons in order first; the AI tutor and a typed question after them (the mic asks anything)
  $('ai-chips').replaceChildren();
  $('chips').replaceChildren(
    ...ex.lessons.map((l, i) => chip('lesson', i ? l.title : t('firstLesson', l.title), () => startLesson(l, false))),
    ...(ex.lessons.some((l) => l.steps.some((s) => s.quiz)) ? [chip('lesson quiz', t('guessFirst'), () => startLesson(ex.lessons.find((l) => l.steps.some((s) => s.quiz)), true))] : []),
    ...(ex.ride ? [chip('lesson', t('ride'), startRide)] : []),
    chip('ai ask tutor', t('tutorName'), () => startTutor()),
    chip('ai', t('askAI'), () => $('type').onclick()),
  );
}

// ---------- AI: ask → spoken answer + a demonstration the model composed from the exhibit's parts ----------
async function ask(text) {
  text = text.trim();
  if (!text || !rig) return;
  if (fix) return fixTurn(text, pointed);   // in a repair challenge the mic and the keyboard answer it
  if (explain) return explainBack(text);   // while the tutor or the explain-back check runs, the mic and the keyboard answer it
  if (tutor) return tutorTurn(text);
  stopAll();
  say(t('youAsked'), text, true);
  try {
    const res = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exhibit: ex.id, lang, text, pointed, history: chat }), signal: AbortSignal.timeout(30000) });
    const r = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(r.error || `HTTP ${res.status}`);
    chat = [...chat, { role: 'user', content: text }, { role: 'assistant', content: r.say }].slice(-6);
    say('AI', r.say, false, true);
    const steps = cleanSteps(r.steps, ex);
    if (steps.length) viewer.choreo.play(steps);
  } catch (e) {
    const local = offline(text);
    say(local ? local.name : t('aiDown'), local ? local.info : t('aiDownTip'), false, true);
    if (local) rig.isolate([local.id]);
    console.warn('ask failed:', e.message);
  }
}
// without the AI: a question that names a part still gets that part
const offline = (text) => ex.parts.find((p) => [p.name, ...p.aliases].some((n) => text.toLowerCase().includes(n.toLowerCase())));

$('type').onclick = () => { $('ask').hidden = !$('ask').hidden; if (!$('ask').hidden) $('q').focus(); };
$('ask').onsubmit = (e) => { e.preventDefault(); ask($('q').value); $('q').value = ''; $('ask').hidden = true; };

// hold to talk
const rec = new Recorder();
let holding = false;
const talk = async () => {
  holding = true; speak('');
  try { await rec.start(); $('mic').classList.add('rec'); toast(tapMode ? t('tapAgain') : t('speakNow')); vr?.say(t('vrSpeak')); if (!holding) release(); }
  catch { holding = false; toast(t('noMic')); vr?.say(t('vrNoMic')); }
};
let tapMode = false, downAt = 0;
$('mic').onpointerdown = (e) => { e.preventDefault(); if (holding) return release(); downAt = Date.now(); tapMode = false; talk(); };
// a quick tap keeps recording until the next tap; a long press sends on release
const lift = () => { if (!holding) return; if (Date.now() - downAt < 400) { tapMode = true; return toast(t('tapAgain'), 20000); } release(); };
const release = async () => {
  if (!holding) return;
  holding = false; $('mic').classList.remove('rec'); toast('');
  const wav = await rec.stop();
  if (!wav) return toast(t('tooShort'));
  say(t('youSaid'), t('transcribing'), true);
  try {
    const res = await fetch(`/api/stt?exhibit=${ex.id}&lang=${lang}`, { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav, signal: AbortSignal.timeout(20000) });
    const { text } = await res.json();
    if (text) ask(text); else say('', t('notHeard'));
  } catch { say('', t('noVoice')); }
};
for (const ev of ['pointerup', 'pointercancel']) $('mic').addEventListener(ev, () => { if (!tapMode) lift(); });

// ---------- 因果連動 / 先猜再看: manifest lessons, one cause → effect per step ----------
function startLesson(l, quiz) { stopAll(); lesson = { l, quiz, i: 0 }; Object.assign(viewer, { lessonMode: true, userView: false }); document.body.classList.add('lesson'); $('lesson').hidden = false; showStep(); }
function showStep() {
  const { l, quiz: guess, i } = lesson, s = l.steps[i];
  $('l-step').textContent = `${l.title} · ${i + 1}/${l.steps.length}`;
  $('l-step').style.setProperty('--p', `${((i + 1) / l.steps.length) * 100}%`);
  $('l-prev').disabled = i === 0 && !lesson.all;
  $('l-all').textContent = lesson.all ? t('steps') : t('all');
  if (lesson.all) flowStep(); else if (guess && s.quiz) askQuiz(s); else playStep(s);
  vr?.refresh();
}
function playStep(s) {
  $('quiz').hidden = true; quiz = null;
  viewer.choreo.cancel(); rig.stop();
  rig.isolate(s.parts);
  for (const d of [].concat(s.drive || [])) rig.drive(d, s.speed ?? 0.5);   // a step can run several drives (rotor turning while the stick moves)
  say(t('stepN', lesson.i + 1), s.say, false, true);
}
function askQuiz(s) {
  rig.isolate(s.parts); rig.stop();
  say(t('guess'), s.quiz.q, false, true);
  quiz = s.quiz.options; $('quiz').hidden = false;
  $('quiz').replaceChildren(...quiz.map(([text], i) => Object.assign(document.createElement('button'), { type: 'button', textContent: text, onclick: () => answer(i) })));
}
function answer(i) {
  if (!quiz || !lesson) return;
  const [, right, why] = quiz[i], s = lesson.l.steps[lesson.i];
  quiz = null; vr?.refresh();
  for (const b of $('quiz').children) b.disabled = true;
  $('quiz').children[i].classList.add(right ? 'right' : 'wrong');
  say(right ? t('right') : t('thinkAgain'), why, false, true);
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
  say(t('stepN', i + 1), s.say, false, true);
  clearTimeout(flow);
  flow = setTimeout(() => { if (lesson?.all) { lesson.i = (i + 1) % l.steps.length; showStep(); } }, 2500 + s.say.length * (isEn ? 70 : 220));   // roughly the time to read or hear it
}
// ---------- 坐上去: first person on a vehicle, throttle and gears with the real rpm and speed ----------
let ride = null;
async function startRide() {
  stopAll();
  const { Ride } = await import('./ride.js');
  ride = viewer.ride ||= new Ride(viewer);
  ride.start(ex.ride);
  document.body.classList.add('riding'); $('ride').hidden = false;
  $('r-gears').replaceChildren(...ex.ride.gears.map((_, i) => Object.assign(document.createElement('button'), { type: 'button', textContent: `${i + 1}`, ariaLabel: t('gear', i + 1), onclick: () => { ride.gear(i); rideRead(); } })));
  $('r-thr').value = ride.thr; $('r-see').setAttribute('aria-pressed', 'false');
  rideRead();
  say(t('ride'), ex.ride.hint, false, true);
}
function rideRead() {
  const r = ride.read;
  $('r-read').textContent = t('rideRead', r);
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
const VERDICT = { right: t('vRight'), partial: t('vPartial'), wrong: t('vWrong') };
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
  document.body.classList.add('tutor'); $('tutor').hidden = false; $('q').placeholder = t('answerPh');
  $('t-bar').textContent = t('tutorName'); $('t-show').textContent = t('tShow');
  tutorTurn('', focus);
}
async function tutorTurn(answer, focus) {
  const tu = tutor;
  if (!tu || tu.busy) return;
  tu.busy = true; viewer.choreo.cancel(); speak('');
  feedback('', '', ''); $('t-q').textContent = answer ? t('youAnswered', answer) : t('firstQ'); $('t-choices').replaceChildren(); $('t-hint').hidden = true; $('tutor').classList.add('thinking');
  say(t('tutorName'), answer ? t('checking') : t('firstQ'), true);
  const user = answer ? t('myAnswer', answer) : t('tutorStart');
  try {
    const res = await fetch('/api/tutor', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exhibit: ex.id, lang, answer, history: tu.history, known: record(ex.id), focus }), signal: AbortSignal.timeout(30000) });
    const r = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(r.error || `HTTP ${res.status}`);
    if (tutor !== tu) return;
    if (r.grade) { tu.n++; tu.right += r.grade.verdict === 'right'; remember(r.grade); }
    const q = r.question?.q || t('fallbackQ');
    tu.history = [...tu.history, { role: 'user', content: user }, { role: 'assistant', content: t('asks', r.say, q) }].slice(-6);
    $('t-bar').textContent = tu.n ? t('score', tu.right, tu.n) : t('tutorName');
    feedback(r.grade?.verdict || '', r.grade ? VERDICT[r.grade.verdict] : '', r.say);
    $('t-q').textContent = q;
    $('t-choices').replaceChildren(...(r.question?.choices || []).map((c) => Object.assign(document.createElement('button'), { type: 'button', textContent: c, onclick: () => tutorTurn(c) })));
    $('t-hint').hidden = tu.n > 0 || !!r.question?.choices?.length;
    say(r.grade ? VERDICT[r.grade.verdict] : t('tutorName'), r.say);
    speak(`${r.say} ${q}`);
    vr?.say(q);
    const steps = cleanSteps(r.steps, ex);
    if (steps.length) viewer.choreo.play(steps);
  } catch (e) {
    if (tutor === tu) feedback('wrong', t('offline'), t('tutorRetry'));
    console.warn('tutor failed:', e.message);
  } finally { tu.busy = false; $('tutor').classList.remove('thinking'); }
}
$('t-show').onclick = () => (explain ? done() : tutorTurn(t('showMe')));
const done = () => { stopAll(); say(t('doneT'), ex.faults?.length ? t('doneFix') : t('doneTutor'), false, true); };

// ---------- 講一遍給我聽: after a lesson the learner explains it back; Muse marks each cause → effect link, the model replays the missed ones ----------
function startExplain(l) {
  stopAll(); speak('');
  explain = { l };
  document.body.classList.add('tutor'); $('tutor').hidden = false; $('q').placeholder = t('explainPh');
  $('t-bar').textContent = t('explainBar'); $('t-show').textContent = t('skip');
  feedback('', '', ''); $('t-choices').replaceChildren(); $('t-hint').hidden = false;
  $('t-q').textContent = t('explainQ', l.title);
  say(t('lastStep'), $('t-q').textContent, false, true);
  vr?.refresh();
}
async function explainBack(text) {
  const x = explain;
  if (!x || x.busy) return;
  x.busy = true; viewer.choreo.cancel(); speak('');
  say(t('youSaid'), text, true); feedback('', '', ''); $('t-q').textContent = t('youSaidX', text); $('t-hint').hidden = true; $('tutor').classList.add('thinking');
  try {
    const res = await fetch('/api/explain', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exhibit: ex.id, lang, lesson: x.l.id, text }), signal: AbortSignal.timeout(30000) });
    const r = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(r.error || `HTTP ${res.status}`);
    if (explain !== x) return;
    const steps = x.l.steps, got = r.covered.filter(Boolean).length, missed = steps.filter((_, i) => !r.covered[i]);
    remember({ concept: x.l.title, verdict: !missed.length ? 'right' : got * 2 >= steps.length ? 'partial' : 'wrong' });   // the tutor starts from what was missed
    feedback(!missed.length ? 'right' : got * 2 >= steps.length ? 'partial' : 'wrong', t('covered', got, steps.length), r.say);
    $('t-choices').replaceChildren(...missed.map((s) => Object.assign(document.createElement('div'), { className: 'miss', textContent: s.say })));   // only the missed links, one line each
    $('t-q').textContent = missed.length ? t('missedTip') : t('allRight');
    $('t-show').textContent = t('end');
    say(missed.length ? t('almost') : t('allCorrect'), r.say);
    speak(r.say);
    // the model replays only the missed links, one every 4 s
    viewer.choreo.play(cleanSteps(missed.flatMap((s, k) => [{ do: 'isolate', at: k * 4, parts: s.parts }, ...[].concat(s.drive || []).map((d) => ({ do: 'drive', at: k * 4, drive: d, speed: s.speed ?? 0.5, duration: 3.5 }))]), ex));
  } catch (e) {
    if (explain === x) feedback('wrong', t('offline'), t('explainRetry'));
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
  toast(t('looking'), 20000);
  try {
    const res = await fetch(`/api/identify?lang=${lang}`, { method: 'POST', headers: { 'Content-Type': 'image/jpeg' }, body: await shrink(f), signal: AbortSignal.timeout(30000) });
    const r = await res.json();
    toast('');
    if (!res.ok) throw new Error(r.error);
    if (!r.match || !exhibits[r.exhibit]) { if (!$('app').hidden) say(t('photoSaw'), r.say, false, true); else toast(r.say, 5000); return; }
    await learn(r.exhibit);
    if (r.parts?.length) rig.isolate(r.parts);
    say(t('photoSaw'), r.say, false, true);
    const part = ex.parts.find((p) => p.id === r.parts?.[0]);
    setTimeout(() => startTutor(part?.id), 3500);   // the tutor starts its lesson from the part in the photo
  } catch { toast(t('photoFail'), 4000); }
};

// ---------- 修理挑戰: the exhibit's fault breaks a drive; guess → Muse checks it on the model → repair → explain why → next ----------
let fix = null, symptomT;
function setMode(m) { $('m-fix').setAttribute('aria-pressed', String(m === 'fix')); $('m-learn').setAttribute('aria-pressed', String(m === 'learn')); $('m-fix').disabled = !ex?.faults?.length; }
async function learn(id = ex?.id) { await open(id); stopAll(); setMode('learn'); say(ex.name, ex.intro); }
$('m-learn').onclick = () => { if (fix) learn(); };
$('m-fix').onclick = () => { if (!fix && ex.faults?.length) startFix(`${ex.id}/${ex.faults[0].id}`); };
const card = (cls, label, text) => { $('f-v').className = cls; $('f-v').replaceChildren(...(label ? [Object.assign(document.createElement('b'), { textContent: label }), ' '] : []), text); };
const choices = (items) => $('f-choices').replaceChildren(...items.map(([text, run, go]) => Object.assign(document.createElement('button'), { type: 'button', textContent: text, className: go ? 'go' : '', onclick: run })));
const driveParts = (f) => [...new Set([...(ex.drives.find((d) => d.id === f.drive)?.moves || []).map((m) => m.part), ...f.broken])];
async function startFix(key) {
  const c = faults.find((x) => x.key === key);
  if (!c) return learn(list[0]);
  await open(c.ex);
  stopAll(); speak('');
  fix = { ...c, stage: 'diagnose', tries: 0, help: 0, history: [] };
  rig.setFault(c.f);
  document.body.classList.add('fix'); $('fix').hidden = false; setMode('fix');
  $('f-bar').textContent = t('fixBarEx', ex.name);
  card('', '', ''); choices([]); $('f-help').hidden = false; $('f-help').textContent = t('help'); $('f-hint').hidden = false; $('f-hint').textContent = t('fixHint');
  $('f-q').textContent = c.f.symptom;
  symptom();
  speak(c.f.symptom); vr?.say(c.f.symptom);
}
// the broken machine running, as the learner first saw it (again after every check)
function symptom() {
  clearTimeout(symptomT);
  if (!fix) return;
  viewer.choreo.cancel(); rig.reset();
  if (fix.stage !== 'diagnose') { rig.isolate(driveParts(fix.f)); return rig.drive(fix.f.drive, fix.f.speed ?? 0.5); }
  if (fix.f.see) { rig.isolate(fix.f.see); rig.highlight([]); }   // the mechanism in view, nothing lit: finding it is the learner's job
  rig.drive(fix.f.drive, fix.f.speed ?? 0.5);
}
async function fixTurn(text, pointed) {
  const x = fix;
  if (!x || x.busy || x.stage === 'done') return;
  x.busy = true; clearTimeout(symptomT); speak('');
  card('', '', x.stage === 'diagnose' ? t('youGuess', text) : t('youSay', text)); $('fix').classList.add('thinking'); $('f-hint').hidden = true;
  let r;
  try {
    const res = await fetch('/api/fix', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ exhibit: x.ex, lang, fault: x.f.id, stage: x.stage, text, pointed, history: x.history, solved: solvedKeys() }), signal: AbortSignal.timeout(30000) });
    r = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(r.error || `HTTP ${res.status}`);
  } catch (e) { console.warn('fix failed:', e.message); r = offlineFix(x, text, pointed); }
  x.busy = false; $('fix').classList.remove('thinking');
  if (fix !== x) return;
  x.history = [...x.history, { role: 'user', content: text }, { role: 'assistant', content: r.say }].slice(-4);
  const steps = cleanSteps(r.steps, ex);
  if (steps.length) viewer.choreo.play(steps);
  const wait = (steps.length ? Math.min(12, Math.max(...steps.map((s) => s.at + (s.duration || 2)))) + 1.5 : 0) * 1000;
  speak(r.say); vr?.say(r.say);
  x.tries++;
  if (x.stage === 'diagnose') {
    if (r.result === 'found') { card('right', t('found'), r.say); choices([]); $('f-help').hidden = true; symptomT = setTimeout(() => fix === x && repair(x), Math.max(wait, 2500)); return; }
    card(r.result === 'close' ? 'partial' : 'wrong', r.result === 'close' ? t('close') : t('notIt'), r.say);
    suspects(x);
    symptomT = setTimeout(symptom, Math.max(wait, 1500));
    return;
  }
  const v = r.grade?.verdict || 'partial';
  card(v, { right: t('gRight'), partial: t('vPartial'), wrong: t('vWrong') }[v], r.say);
  if (v === 'right' || x.tries >= 2) return finish(x, r.next, v === 'right' ? '' : x.f.answer);
  $('f-q').textContent = t('sayAgain', x.f.why);
  symptomT = setTimeout(symptom, Math.max(wait, 1500));
}
// a guess list after the first miss (or 提示), so nobody is stuck without words for the part
function suspects(x) { if (x.stage === 'diagnose') choices((x.f.suspects || []).map((g) => [g, () => fixTurn(g)])); }
// without the AI: a guess that names a broken part (or taps one) is found; an explanation is answered with the right one
function offlineFix(x, text, pointed) {
  if (x.stage === 'diagnose') {
    const hit = x.f.broken.includes(pointed) || x.f.broken.some((id) => { const p = ex.parts.find((q) => q.id === id); return [p.name, ...(p.aliases || [])].some((n) => text.toLowerCase().includes(n.toLowerCase())); });
    return hit ? { result: 'found', say: t('offFound', x.f.cause) } : { result: 'not_it', say: t('offClue', x.f.hint) };
  }
  return { grade: { verdict: 'right' }, say: t('offAnswer', x.f.answer) };
}
function repair(x) {
  x.stage = 'explain'; x.tries = 0;
  viewer.choreo.cancel(); rig.setFault(null);
  symptom();
  card('right', t('repaired'), x.f.cause); choices([]);
  $('f-q').textContent = x.f.why; $('f-hint').textContent = t('explainHint'); $('f-hint').hidden = false; $('f-help').hidden = false; $('f-help').textContent = t('dunno');
  speak(`${x.f.cause} ${x.f.why}`); vr?.say(x.f.why);
}
function finish(x, next, answer) {
  x.stage = 'done';
  try { localStorage.setItem('mechanica.fixed', JSON.stringify([...new Set([...solvedKeys(), x.key])])); } catch { /* private mode */ }
  const done = new Set(solvedKeys()), n = faults.find((c) => c.key === next && !done.has(c.key)) || faults.find((c) => !done.has(c.key)) || faults.find((c) => c.key !== x.key);
  const l = ex.lessons.find((y) => y.id === x.f.lesson);
  if (answer) card('partial', t('fullAnswer'), answer);
  $('f-q').textContent = t('exFixed', ex.name); $('f-hint').hidden = true; $('f-help').hidden = true;
  choices([...(n ? [[t('nextFix', exhibits[n.ex].name, n.f.short), () => startFix(n.key), true]] : []), ...(l ? [[t('seeLesson', l.title), async () => { await learn(); startLesson(l, false); }]] : [])]);
  symptom();
}
$('f-help').onclick = () => {
  const x = fix;
  if (!x || x.busy) return;
  if (x.stage === 'explain') return finish(x, null, x.f.answer);
  if (x.help++ === 0) { card('', t('clue'), x.f.hint); suspects(x); speak(x.f.hint); $('f-help').textContent = t('seeAnswer'); return; }
  card('', t('answerT'), x.f.cause); x.tries = 9;
  symptomT = setTimeout(() => fix === x && repair(x), 2500);
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
  try { vr = await viewer.enterVR(app); } catch { vr = null; toast(t('noVR')); }
}
$('vr').onclick = enterVR;
viewerModule.then(async ({ Viewer }) => { if (await Viewer.vrSupported()) $('home-vr').hidden = false; });
$('home-vr').onclick = async () => { await learn(ex?.id || list[0]); enterVR(); };

// first sound needs a tap on phones
addEventListener('pointerdown', () => speechSynthesis?.speak(new SpeechSynthesisUtterance('')), { once: true });
// no landing page first: a broken machine is the way in (?ex= picks which, ?learn opens 原理)
const qs = new URLSearchParams(location.search), start = exhibits[qs.get('ex')] ? qs.get('ex') : null;
if (qs.has('learn') && start) learn(start);
else startFix(faults.find((x) => x.ex === start)?.key || faults.find((x) => !solvedKeys().includes(x.key))?.key || faults[0]?.key);
