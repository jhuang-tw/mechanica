// Two languages: English (the default) and 繁體中文.
// The choice: ?lang=en|zh, then the one saved by the switch, else English.
// t(key, ...args) gives the string in the current language; index.html marks its fixed text with data-t / data-t-aria.
const saved = () => { try { return localStorage.getItem('mechanica.lang'); } catch { return null; } };
function detect() {
  if (typeof location === 'undefined') return 'zh';   // node (tests)
  const q = new URLSearchParams(location.search).get('lang');
  if (q === 'en' || q === 'zh') return q;
  const s = saved();
  return s === 'zh' ? 'zh' : 'en';
}
export const lang = detect();
export const isEn = lang === 'en';

export const S = {
  // landing
  docTitle: ['Mechanica · 修好它，就懂了', 'Mechanica · Fix it to understand it'],
  docDesc: ['修好一台壞掉的機器：看症狀、說出你的猜測，Meta AI 在 3D 模型上幫你檢查；也能一步一步學它的原理。', 'Fix a broken machine: watch the symptom, say your guess, and Meta AI checks it on the 3D model. Or learn how it works, step by step.'],
  vrClass: ['VR 上課', 'Learn in VR'],
  pickA: ['選一台來', 'Pick one to '], pickB: ['修', 'fix'],
  pickLede: ['每台機器都有一個地方壞了。看症狀、說出你的猜測，Meta AI 會在 3D 模型上幫你檢查，修好之後再說說看為什麼。', 'Every machine has one thing broken. Watch the symptom and say your guess. Meta AI checks it on the 3D model, and once it is fixed you explain why it failed.'],
  photoB: ['身邊有真的機器？', 'Got a real machine nearby?'],
  photoS: ['拍下來，幫你找到對應的機器和零件', 'Take a photo and we find the matching machine and parts'],
  foot: ['Mechanica · 手機、電腦和 VR 頭戴都能上課', 'Mechanica · works on phones, computers and VR headsets'],
  fixed: ['修好了', 'Fixed'], toFix: ['待修', 'To fix'],
  symptomShort: [(s) => `症狀：${s}`, (s) => `Symptom: ${s}`],
  lessonsN: [(n) => `原理：${n} 堂課`, (n) => `How it works: ${n} lesson${n === 1 ? '' : 's'}`],
  // exhibit chrome
  back: ['回首頁', 'Home'], mode: ['模式', 'Mode'], mFix: ['修理', 'Fix'], mLearn: ['原理', 'Learn'], reset: ['還原', 'Reset'],
  fixBar: ['修理挑戰', 'Repair challenge'], help: ['提示', 'Hint'],
  fixHint: ['選一個猜測，或按麥克風說你自己的想法、直接點你懷疑的零件', 'Pick a guess, or say your own with the mic, or tap the part you suspect'],
  look: ['先看：', 'Look:'], tryAgain: ['那會是哪一個？', 'So which one is it?'], clueLine: [(h) => `線索：${h}`, (h) => `Clue: ${h}`],
  tutorName: ['AI 家教', 'AI tutor'], tShow: ['不會，示範給我看', "I don't know, show me"], tStop: ['結束家教', 'End tutor'],
  tHint: ['點選項，或按麥克風用說的、點鍵盤打字', 'Tap an option, or answer with the mic or the keyboard'],
  prev: ['上一步', 'Previous step'], next: ['下一步', 'Next step'], allAria: ['連貫播放和分步切換', 'Switch between playing it all and step by step'],
  all: ['連貫', 'Play all'], steps: ['分步', 'Step by step'], end: ['結束', 'End'],
  xray: ['透視', 'X-ray'], getOff: ['下車', 'Get off'], throttle: ['油門', 'Throttle'],
  askPh: ['問任何問題…', 'Ask anything…'], send: ['送出', 'Send'], explode: ['拆解', 'Explode'],
  typeAria: ['打字提問', 'Type a question'], photoAria: ['拍真的機器', 'Photograph a real machine'], micAria: ['按住說話', 'Hold to talk'],
  loading: ['載入中…', 'Loading…'],
  // chips
  firstLesson: [(t) => `第一課：${t}`, (t) => `Lesson 1: ${t}`], guessFirst: ['先猜再看', 'Guess first'], ride: ['坐上去', 'Take a seat'], askAI: ['問 AI 老師', 'Ask the AI'],
  // ask
  youAsked: ['你問', 'You asked'], aiDown: ['AI 暫時連不上', 'The AI is not reachable'], aiDownTip: ['可以先上一堂課，或點零件看說明。', 'Try a lesson, or tap a part to read about it.'],
  // mic
  tapAgain: ['說完再點一下送出', 'Tap again when you are done'], speakNow: ['說吧，放開就送出', 'Speak, release to send'], vrSpeak: ['🎤 說吧，說完按 ⏹', '🎤 Speak, then press ⏹'],
  noMic: ['沒有麥克風權限，改用鍵盤打字', 'No microphone access, type instead'], vrNoMic: ['沒有麥克風權限', 'No microphone access'],
  tooShort: ['太短了，按住久一點', 'Too short, hold a little longer'], youSaid: ['你說', 'You said'], transcribing: ['聽寫中', 'Listening'],
  notHeard: ['沒聽清楚，再說一次？', "Didn't catch that. Say it again?"], noVoice: ['語音暫時不能用，改用鍵盤打字。', 'Voice is not available right now, type instead.'],
  // lessons
  stepN: [(n) => `第 ${n} 步`, (n) => `Step ${n}`], guess: ['先猜猜看', 'Take a guess'], right: ['答對了！', 'Correct!'], thinkAgain: ['再想想', 'Think again'],
  gear: [(n) => `${n} 檔`, (n) => `Gear ${n}`],
  rideRead: [(r) => `${r.gear} 檔 · 引擎 ${r.rpm} rpm · 時速 ${r.kmh} km/h`, (r) => `Gear ${r.gear} · engine ${r.rpm} rpm · ${r.kmh} km/h`],
  // tutor
  vRight: ['答對了', 'Right'], vPartial: ['對一半', 'Half right'], vWrong: ['再想想', 'Not quite'],
  answerPh: ['輸入你的答案…', 'Type your answer…'], youAnswered: [(a) => `你答：${a}`, (a) => `You answered: ${a}`], firstQ: ['準備第一題', 'Getting the first question'],
  checking: ['看看你答得怎麼樣', 'Checking your answer'], tutorStart: ['開始上課，先問我第一題。', 'Start the lesson. Ask me the first question.'], myAnswer: [(a) => `我的回答：${a}`, (a) => `My answer: ${a}`],
  fallbackQ: ['還有哪個零件你想弄懂？', 'Which part would you like to understand next?'], asks: [(s, q) => `${s} 問：${q}`, (s, q) => `${s} Question: ${q}`],
  score: [(r, n) => `AI 家教 · 答對 ${r}/${n}`, (r, n) => `AI tutor · ${r}/${n} right`], offline: ['連不上', 'Offline'],
  tutorRetry: ['再回答一次試試，或先上一堂課。', 'Try answering again, or take a lesson first.'],
  showMe: ['我不知道，請動模型示範給我看，再問簡單一點的', "I don't know. Please show me on the model, then ask something simpler."],
  doneT: ['完成', 'Done'], doneFix: ['這一套上完了。試試看「修理挑戰」：這台機器有個地方壞了，看你找不找得到。', 'That lesson is done. Try the repair challenge: something on this machine is broken. Can you find it?'],
  doneTutor: ['這一套上完了。可以找 AI 家教再練，或換一套。', 'That lesson is done. Practise with the AI tutor, or pick another lesson.'],
  // explain back
  explainPh: ['用你自己的話講一遍…', 'Explain it in your own words…'], explainBar: ['講一遍給我聽', 'Explain it to me'], skip: ['跳過', 'Skip'],
  explainQ: [(t) => `用你自己的話，從頭講一次「${t}」是怎麼動的。`, (t) => `In your own words, explain from the start how "${t}" works.`], lastStep: ['最後一關', 'Last step'],
  youSaidX: [(t) => `你說：${t}`, (t) => `You said: ${t}`], covered: [(g, n) => `講到 ${g}/${n}`, (g, n) => `${g}/${n} covered`],
  missedTip: ['看模型補上，想再講一次就直接說', 'Watch the model fill in the gaps, or just say it again'], allRight: ['整條因果鏈都講對了！', 'You got the whole chain of cause and effect!'],
  almost: ['還差一點', 'Almost'], allCorrect: ['全對', 'All correct'], explainRetry: ['再講一次試試，或按跳過。', 'Try explaining again, or tap Skip.'],
  // photo
  looking: ['我看看這是什麼…', 'Let me see what this is…'], photoSaw: ['拍到的', 'In your photo'], photoFail: ['現在認不出來，再拍一次試試', "Couldn't recognise it. Try another photo"],
  // repair challenge
  fixBarEx: [(n) => `修理挑戰 · ${n}`, (n) => `Repair challenge · ${n}`], youGuess: [(t) => `你猜：${t}`, (t) => `Your guess: ${t}`], youSay: [(t) => `你說：${t}`, (t) => `You said: ${t}`],
  pickedPart: [(n) => `我覺得是${n}壞了`, (n) => `I think the ${n.toLowerCase()} is broken`],
  found: ['找到了！', 'Found it!'], close: ['方向對了', 'Getting close'], notIt: ['不是這裡', 'Not there'],
  gRight: ['說對了', 'Right'], sayAgain: [(w) => `再說一次：${w}`, (w) => `Try again: ${w}`],
  offFound: [(c) => `對，就是這裡。${c}`, (c) => `Yes, that's it. ${c}`], offClue: [(h) => `AI 暫時連不上，先給你線索：${h}`, (h) => `The AI is not reachable, so here is a clue: ${h}`],
  offAnswer: [(a) => `AI 暫時連不上，完整的說法是：${a}`, (a) => `The AI is not reachable. The full explanation: ${a}`],
  repaired: ['修好了', 'Repaired'], explainHint: ['點一個答案，或用你自己的話說說看（麥克風或鍵盤）', 'Tap an answer, or say it in your own words (mic or keyboard)'], dunno: ['不知道', "I don't know"],
  fullAnswer: ['完整的說法', 'The full explanation'], exFixed: [(n) => `${n}修好了！`, (n) => `Fixed: the ${n.toLowerCase()} works again!`],
  nextFix: [(n, s) => `下一台：${n}（${s}）`, (n, s) => `Next: ${n} (${s})`], seeLesson: [(t) => `看原理：${t}`, (t) => `How it works: ${t}`],
  clue: ['線索', 'Clue'], seeAnswer: ['看答案', 'Show answer'], answerT: ['答案', 'Answer'],
  // VR
  noVR: ['這個瀏覽器不能進 VR', 'This browser cannot enter VR'],
  vrTutor: ['🎓 AI 家教', '🎓 AI tutor'], vrGuess: ['❓ 先猜再看', '❓ Guess first'], vrClose: ['🧩 合起來', '🧩 Put together'], vrOpen: ['💥 拆開', '💥 Explode'],
  vrReset: ['↺ 重設', '↺ Reset'], vrDone: ['⏹ 說完了', '⏹ Done'], vrAnswer: ['🎤 回答家教', '🎤 Answer'], vrAsk: ['🎤 問 AI', '🎤 Ask AI'],
  vrMenuClose: ['✕ 關選單', '✕ Close'], vrExit: ['🚪 離開 VR', '🚪 Exit VR'],
  // language switch: names the other language
  switchTo: ['EN', '中文'], switchAria: ['Switch to English', '切換成中文'],
};
export function t(key, ...args) {
  const v = S[key]?.[isEn ? 1 : 0];
  return typeof v === 'function' ? v(...args) : v ?? key;
}

// fixed text in index.html: data-t="key" sets the text, data-t-aria="key" the aria-label
export function applyStatic(root = document) {
  document.documentElement.lang = isEn ? 'en' : 'zh-Hant';
  document.title = t('docTitle');
  document.querySelector('meta[name=description]')?.setAttribute('content', t('docDesc'));
  for (const el of root.querySelectorAll('[data-t]')) el.textContent = t(el.dataset.t);
  for (const el of root.querySelectorAll('[data-t-aria]')) el.setAttribute('aria-label', t(el.dataset.tAria));
}

// a URL that keeps an explicit ?lang= (a shared English link stays English)
export function here(params = '') {
  const l = new URLSearchParams(location.search).get('lang'), q = new URLSearchParams(params);
  if (l) q.set('lang', l);
  const s = q.toString();
  return s ? `?${s}` : location.pathname;
}

// the switch saves the other language and reloads in place (the exhibit stays open)
export function switchLang() {
  const next = isEn ? 'zh' : 'en';
  try { localStorage.setItem('mechanica.lang', next); } catch { /* private mode: the URL carries it */ }
  const u = new URL(location.href);
  u.searchParams.set('lang', next);
  location.replace(u);
}
