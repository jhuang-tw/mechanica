// 真機照片 → 3D 零件: a phone photo of a real machine, taken apart by Meta's models.
//   1. Muse Spark (vision) names the machine and the parts it can see      -> /api/identify
//   2. SAM 3.1 traces each of those parts on the photo, one mask per part  -> /api/segment
//   3. tap a traced part: it lifts off the photo and flies into the exploded 3D model, where that part lights up
//      (everything else goes see-through) and Muse explains it and shows it moving                  -> /api/ask
// Loaded on the first photo (it pulls in three.js for the screen projection). Its UI and styles live here, not in index.html.
import * as THREE from 'three';
import { isEn, lang } from './i18n.js';

const W = {
  muse: ['Muse Spark 視覺辨識', 'Muse Spark vision'], sam: ['SAM 3.1 零件分割', 'SAM 3.1 segmentation'],
  looking: ['Muse 正在看你的照片…', 'Muse is looking at your photo…'],
  tracing: [(m, n) => `Muse 認出：${m}。SAM 3.1 正在描出 ${n} 個零件…`, (m, n) => `Muse sees: ${m}. SAM 3.1 is tracing ${n} part${n === 1 ? '' : 's'}…`],
  tap: ['點照片上的零件，看它飛進 3D 模型', 'Tap a part on the photo to send it into the 3D model'],
  noMask: ['SAM 這張沒描到輪廓，直接點下面的零件也可以', "SAM couldn't trace outlines here. Tap a part below instead"],
  noPart: ['認出機器了，但照片裡沒看到這台展品也有的零件', 'Machine recognised, but none of its parts are clear in this photo'],
  photo: ['你的照片', 'Your photo'], close: ['關閉', 'Close'], fail: ['現在認不出來，再拍一次試試', "Couldn't recognise it. Try another photo"],
  ask: [(m, p) => `我用手機拍到真的${m}，SAM 在照片上圈出了「${p}」。用一兩句話說它是什麼、在整台機器裡負責什麼，再在模型上示範它怎麼跟其他零件連動。`,
    (m, p) => `I photographed a real ${m} and SAM traced the "${p}" on it. In one or two sentences say what it is and what it does in the whole machine, then show on the model how it moves with the parts around it.`],
};
const w = (k, ...a) => { const v = W[k][isEn ? 1 : 0]; return typeof v === 'function' ? v(...a) : v; };
const COLORS = ['#ffb02e', '#5ab4ff', '#4fd08a', '#ff7ab6'];
const EXPLODE = 0.55;   // how far the model comes apart while a photo part is in it

const CSS = `
#snap { position:fixed; inset:0; z-index:6; display:flex; flex-direction:column; gap:10px; padding:calc(12px + env(safe-area-inset-top)) 16px calc(14px + env(safe-area-inset-bottom)); background:rgba(6,8,12,.9); backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px); transition:opacity .35s; }
#snap.away { opacity:0; pointer-events:none; }
#snap .top { display:flex; align-items:center; gap:6px; flex-wrap:wrap; padding:0; min-height:0; }
#snap .badge { padding:3px 10px; border-radius:999px; font-size:12px; font-weight:700; letter-spacing:.02em; color:#cfe6ff; background:rgba(90,180,255,.14); border:1px solid rgba(90,180,255,.35); }
#snap .badge.on { color:#0b1a2e; background:#8ec5ff; }
#snap .x { margin-left:auto; display:grid; place-items:center; width:44px; height:44px; padding:0; border-radius:12px; background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.14); }
#snap .stage { position:relative; flex:1; min-height:0; display:grid; place-items:center; }
#snap .frame { position:relative; max-width:100%; max-height:100%; line-height:0; border-radius:14px; overflow:hidden; box-shadow:0 20px 50px -20px #000; }
#snap img { display:block; max-width:100%; max-height:calc(100dvh - 230px); object-fit:contain; }
#snap .frame svg { position:absolute; inset:0; width:100%; height:100%; }
#snap .m path { fill:var(--c); fill-rule:evenodd; fill-opacity:.32; stroke:var(--c); stroke-width:2.5; vector-effect:non-scaling-stroke; stroke-dasharray:4000; stroke-dashoffset:4000; animation:snapdraw 1.1s ease-out forwards; cursor:pointer; transition:fill-opacity .2s; }
#snap .m:hover path, #snap .m.hot path { fill-opacity:.55; }
#snap.busy .scan { position:absolute; left:0; right:0; height:22%; top:-22%; background:linear-gradient(transparent, rgba(142,197,255,.35) 70%, rgba(200,230,255,.9) 100%); animation:snapscan 1.6s linear infinite; pointer-events:none; }
@keyframes snapdraw { to { stroke-dashoffset:0; } }
@keyframes snapscan { to { top:100%; } }
#snap .say { margin:0; min-height:1.5em; font-size:15px; line-height:1.5; text-align:center; color:#f2f5f8; }
#snap.busy .say::after { content:"…"; animation:blink 1s infinite; }
#snap .parts { display:flex; flex-wrap:wrap; justify-content:center; gap:8px; }
#snap .parts button { display:flex; align-items:center; gap:8px; min-height:44px; padding:0 14px; border-radius:999px; font-size:14px; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.16); }
#snap .parts i { width:10px; height:10px; border-radius:50%; background:var(--c); }
.snapfly { position:fixed; z-index:7; pointer-events:none; transform-origin:center; filter:drop-shadow(0 0 14px rgba(255,176,46,.9)); }
#snap-pill { position:absolute; z-index:2; left:12px; top:calc(70px + env(safe-area-inset-top)); display:flex; align-items:center; gap:8px; padding:4px 12px 4px 4px; border-radius:14px; font-size:13px; font-weight:600; background:var(--glass); border:1px solid var(--line2); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px); }
#snap-pill img { width:40px; height:40px; object-fit:cover; border-radius:10px; }
body.fix #snap-pill, body.riding #snap-pill { display:none; }
`;

let ui, cur;   // cur: the photo on screen { url, w, h, exhibit, machine, parts[], masks Map, said Map }

function build() {
  document.head.append(Object.assign(document.createElement('style'), { textContent: CSS }));
  const el = Object.assign(document.createElement('div'), { id: 'snap', hidden: true });
  el.innerHTML = `<div class="top"><span class="badge b-muse"></span><span class="badge b-sam"></span><button class="x" type="button"><svg class="i"><use href="#i-x"/></svg></button></div>
    <div class="stage"><div class="frame"><img alt=""><svg xmlns="http://www.w3.org/2000/svg"></svg><div class="scan"></div></div></div>
    <p class="say" aria-live="polite"></p><div class="parts"></div>`;
  el.querySelector('.b-muse').textContent = w('muse'); el.querySelector('.b-sam').textContent = w('sam');
  el.querySelector('.x').setAttribute('aria-label', w('close'));
  document.body.append(el);
  const pill = Object.assign(document.createElement('button'), { id: 'snap-pill', type: 'button', hidden: true });
  pill.innerHTML = '<img alt=""><span></span>';
  pill.lastChild.textContent = w('photo');
  document.getElementById('app').append(pill);
  return { el, img: el.querySelector('img'), svg: el.querySelector('.frame svg'), say: el.querySelector('.say'), parts: el.querySelector('.parts'), x: el.querySelector('.x'), pill };
}

const show = (on) => { ui.el.hidden = false; requestAnimationFrame(() => ui.el.classList.toggle('away', !on)); if (!on) setTimeout(() => { if (ui.el.classList.contains('away')) ui.el.hidden = true; }, 400); };
const status = (text, busy) => { ui.say.textContent = text; ui.el.classList.toggle('busy', !!busy); };
const badge = (k) => { ui.el.querySelector('.b-muse').classList.toggle('on', k === 'muse'); ui.el.querySelector('.b-sam').classList.toggle('on', k === 'sam'); };

async function post(url, body, type) {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': type }, body, signal: AbortSignal.timeout(30000) });
  const r = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(r.error || `HTTP ${res.status}`);
  return r;
}

// app: { shrink, learn, stop, explode, say, speak, cleanSteps, get viewer, get rig, get ex }
export async function runPhoto(file, app) {
  ui ||= build();
  ui.x.onclick = () => show(false);
  ui.pill.onclick = async () => { if (!cur) return; if (cur.exhibit && app.ex?.id !== cur.exhibit) await app.learn(cur.exhibit); show(true); };
  const blob = await app.shrink(file);
  if (cur) URL.revokeObjectURL(cur.url);
  const url = URL.createObjectURL(blob), me = cur = { url, masks: new Map(), said: new Map() };
  ui.img.src = url; await ui.img.decode().catch(() => {});
  me.w = ui.img.naturalWidth; me.h = ui.img.naturalHeight;
  ui.svg.setAttribute('viewBox', `0 0 ${me.w} ${me.h}`); ui.svg.replaceChildren(); ui.parts.replaceChildren();
  ui.pill.hidden = true; ui.pill.querySelector('img').src = url;
  show(true); badge('muse'); status(w('looking'), true);

  let r;
  try { r = await post(`/api/identify?lang=${lang}`, blob, 'image/jpeg'); } catch { status(w('fail')); badge(); return; }
  if (cur !== me) return;
  if (!r.match) { status(r.say || w('fail')); badge(); app.speak(r.say); return; }
  me.exhibit = r.exhibit; me.machine = r.machine || ''; me.boxes = r.boxes || {};
  const opening = app.learn(r.exhibit);   // the 3D model loads behind the photo while SAM works
  await opening;
  if (cur !== me) return;
  const ex = app.ex;
  me.parts = (r.parts || []).map((id) => ex.parts.find((p) => p.id === id)).filter(Boolean);
  if (!me.parts.length) { status(`${r.say} ${w('noPart')}`); badge(); app.speak(r.say); return; }
  app.speak(r.say);
  badge('sam'); status(w('tracing', me.machine || ex.name, me.parts.length), true);

  try {
    const s = await post(`/api/segment?exhibit=${encodeURIComponent(r.exhibit)}&${me.parts.map((p) => `part=${encodeURIComponent(p.id)}`).join('&')}`, blob, 'image/jpeg');
    if (cur !== me) return;
    for (const x of s.results || []) me.masks.set(x.part, { ...x, masks: oneMask(x, me.boxes[x.part]) });
  } catch (e) { console.warn('segment failed:', e.message); }
  if (cur !== me) return;
  draw(me, app);
  badge(); status(me.masks.size ? w('tap') : w('noMask'));
}

// the masks over the photo (bigger ones first, so a small part on top of a big one stays tappable) and one chip per part
function draw(me, app) {
  const groups = [];
  me.parts.forEach((p, i) => {
    const c = COLORS[i % COLORS.length], res = me.masks.get(p.id);
    const chip = Object.assign(document.createElement('button'), { type: 'button', onclick: () => fly(me, p, app) });
    chip.style.setProperty('--c', c); chip.innerHTML = '<i></i><span></span>'; chip.lastChild.textContent = p.name;
    ui.parts.append(chip);
    if (!res) return;
    // SAM's boxes are in its frame's pixels; each raster covers its box at its own resolution
    const fx = res.frame ? me.w / res.frame.w : 1, fy = res.frame ? me.h / res.frame.h : 1;
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'm'); g.style.setProperty('--c', c); g.dataset.part = p.id;
    let area = 0;
    for (const m of res.masks) {
      const b = m.bounds, sx = ((b.right - b.left) / m.width) * fx, sy = ((b.bottom - b.top) / m.height) * fy;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', m.path); path.setAttribute('transform', `matrix(${sx} 0 0 ${sy} ${b.left * fx} ${b.top * fy})`);
      path.style.animationDelay = `${i * 0.18}s`;
      g.append(path);
      area += (b.right - b.left) * (b.bottom - b.top);
    }
    g.addEventListener('click', () => fly(me, p, app));
    chip.onpointerenter = () => g.classList.add('hot'); chip.onpointerleave = () => g.classList.remove('hot');
    groups.push([area, g]);
  });
  ui.svg.replaceChildren(...groups.sort((a, b) => b[0] - a[0]).map(([, g]) => g));
}

// the part's pixels cut out of the photo, placed exactly over where it is on screen
// SAM finds every instance of its prompt ("rear wheel" also finds the front one): keep the mask that best fits where Muse
// said this part is (box as fractions of the photo), else SAM's most confident one, else the first
export function oneMask(res, box) {
  const ms = res.masks || [];
  if (ms.length < 2) return ms;
  const W = res.frame?.w, H = res.frame?.h;
  if (box && W && H) {
    const [l, t, r, b] = [box[0] * W, box[1] * H, box[2] * W, box[3] * H], area = (x) => Math.max(0, x.right - x.left) * Math.max(0, x.bottom - x.top);
    const iou = (m) => { const i = area({ left: Math.max(l, m.bounds.left), top: Math.max(t, m.bounds.top), right: Math.min(r, m.bounds.right), bottom: Math.min(b, m.bounds.bottom) }); return i / (area(m.bounds) + (r - l) * (b - t) - i || 1); };
    return [ms.reduce((a, m) => (iou(m) > iou(a) ? m : a))];
  }
  return [ms.reduce((a, m) => ((m.confidence ?? 0) > (a.confidence ?? 0) ? m : a))];
}

function cutout(me, part) {
  const res = me.masks.get(part.id), frame = ui.img.getBoundingClientRect(), k = frame.width / me.w;
  const box = me.boxes?.[part.id];
  if (!res && box) {   // no SAM mask: the rectangle Muse pointed at stands in for it
    const L = box[0] * me.w, T = box[1] * me.h, c = Object.assign(document.createElement('canvas'), { width: Math.max(1, Math.round((box[2] - box[0]) * me.w)), height: Math.max(1, Math.round((box[3] - box[1]) * me.h)) });
    const g = c.getContext('2d'); g.beginPath(); g.roundRect(0, 0, c.width, c.height, Math.min(c.width, c.height) * 0.15); g.clip(); g.drawImage(ui.img, L, T, c.width, c.height, 0, 0, c.width, c.height);
    return { c, x: frame.left + L * k, y: frame.top + T * k, w: c.width * k, h: c.height * k };
  }
  if (!res) {   // no mask: a round crop from the middle of the photo stands in for it
    const s = Math.min(me.w, me.h) * 0.4, c = Object.assign(document.createElement('canvas'), { width: s, height: s }), g = c.getContext('2d');
    g.beginPath(); g.arc(s / 2, s / 2, s / 2, 0, Math.PI * 2); g.clip(); g.drawImage(ui.img, (me.w - s) / 2, (me.h - s) / 2, s, s, 0, 0, s, s);
    return { c, x: frame.left + (me.w - s) / 2 * k, y: frame.top + (me.h - s) / 2 * k, w: s * k, h: s * k };
  }
  const fx = res.frame ? me.w / res.frame.w : 1, fy = res.frame ? me.h / res.frame.h : 1;
  const L = Math.min(...res.masks.map((m) => m.bounds.left)) * fx, T = Math.min(...res.masks.map((m) => m.bounds.top)) * fy;
  const R = Math.max(...res.masks.map((m) => m.bounds.right)) * fx, B = Math.max(...res.masks.map((m) => m.bounds.bottom)) * fy;
  const c = Object.assign(document.createElement('canvas'), { width: Math.max(1, Math.ceil(R - L)), height: Math.max(1, Math.ceil(B - T)) }), g = c.getContext('2d');
  g.save();
  g.beginPath();
  for (const m of res.masks) {
    const b = m.bounds, sx = ((b.right - b.left) / m.width) * fx, sy = ((b.bottom - b.top) / m.height) * fy, p = new Path2D();
    p.addPath(new Path2D(m.path), new DOMMatrix([sx, 0, 0, sy, b.left * fx - L, b.top * fy - T]));
    g.save(); g.clip(p, 'evenodd'); g.drawImage(ui.img, L, T, c.width, c.height, 0, 0, c.width, c.height); g.restore();
  }
  g.restore();
  return { c, x: frame.left + L * k, y: frame.top + T * k, w: c.width * k, h: c.height * k };
}

// where the part is on screen now (its box centre, projected through the 3D camera)
function onScreen(app, id) {
  const v = app.viewer, p = app.rig?.parts.get(id), canvas = v?.renderer.domElement;
  if (!p || !canvas) return null;
  const at = new THREE.Box3().setFromObject(p.obj).getCenter(new THREE.Vector3()).project(v.camera), r = canvas.getBoundingClientRect();
  return { x: r.left + (at.x + 1) / 2 * r.width, y: r.top + (1 - at.y) / 2 * r.height };
}
const wait = (ms) => new Promise((ok) => setTimeout(ok, ms));

async function fly(me, part, app) {
  if (cur !== me || me.flying) return;
  me.flying = true;
  const cut = cutout(me, part);
  Object.assign(cut.c.style, { left: `${cut.x}px`, top: `${cut.y}px`, width: `${cut.w}px`, height: `${cut.h}px` });
  cut.c.className = 'snapfly';
  document.body.append(cut.c);
  show(false);
  // the model comes apart, everything but this part goes see-through, and the camera glides to it
  const rig = app.rig;
  app.stop(); app.explode(EXPLODE); rig.isolate([part.id]);
  app.say(part.name, part.info);
  const said = explain(me, part, app);   // Muse is asked while the part is in the air
  // 1) the cut-out part rises to the middle of the screen, big, while the photo fades and the model comes apart behind it
  const cx = cut.x + cut.w / 2, cy = cut.y + cut.h / 2, big = Math.min(2.6, (Math.min(innerWidth, innerHeight) * 0.55) / Math.max(cut.w, cut.h));
  const mid = `translate(${innerWidth / 2 - cx}px, ${innerHeight * 0.38 - cy}px) scale(${big})`;
  await cut.c.animate([{ transform: 'none' }, { transform: mid }], { duration: 650, easing: 'cubic-bezier(.2,.8,.3,1)', fill: 'forwards' }).finished.catch(() => {});
  await wait(350);   // a beat to see it (and for the camera to finish its glide)
  // 2) it dives into the same part in the 3D model
  const to = onScreen(app, part.id) || { x: innerWidth / 2, y: innerHeight * 0.4 };
  await cut.c.animate([
    { transform: mid, opacity: 1 },
    { transform: `translate(${to.x - cx}px, ${to.y - cy}px) scale(${Math.min(0.5, 60 / Math.max(cut.w, cut.h))}) rotate(-8deg)`, opacity: 0 },
  ], { duration: 750, easing: 'cubic-bezier(.6,0,.8,.6)', fill: 'forwards' }).finished.catch(() => {});
  cut.c.remove();
  rig.detach([part.id], { amount: 0.12, duration: 0.6 });   // it lands with a little kick out of the model
  ui.pill.hidden = false;
  me.flying = false;
  await said;
}

// Muse explains the part and choreographs it on the model; one call per part per photo
async function explain(me, part, app) {
  let r = me.said.get(part.id);
  if (!r) {
    try {
      r = await post('/api/ask', JSON.stringify({ exhibit: me.exhibit, lang, text: w('ask', me.machine || app.ex.name, part.name), pointed: part.id }), 'application/json');
      me.said.set(part.id, r);
    } catch (e) { console.warn('photo explain failed:', e.message); r = { say: part.info, steps: [] }; }
  }
  if (cur !== me || app.ex?.id !== me.exhibit) return;
  await wait(900);   // let the part land first
  const steps = app.cleanSteps(r.steps, app.ex);
  if (steps.length) {   // keep this part lit and the model apart under Muse's demonstration
    app.viewer.choreo.play([{ do: 'isolate', at: 0, parts: [part.id] }, ...steps.filter((s) => s.do !== 'reset')]);
    app.explode(EXPLODE);
  }
  app.say('Muse', r.say, false, true);
}

export function hidePhoto() { if (ui) { ui.el.hidden = true; ui.el.classList.add('away'); ui.pill.hidden = true; } }
