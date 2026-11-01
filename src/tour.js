// 讓 Muse 帶你看 / Muse tour: a 30–60 s cinematic teardown that Muse Spark directs with tool calls (server/ai.mjs tour()).
// Each scene is one narrated shot: where the camera looks, how far the machine is pulled apart, how see-through the
// shell is, which parts are lit or pulled out, which mechanism runs. Scenes are model output, so cleanTour() checks
// every field against the exhibit's manifest (unknown parts and drives dropped, numbers clamped, count and length bounded).
// Shared by the server (it cleans what Muse sends) and the browser (it cleans again before playing).
const EASE = 2.4;
export const TOUR = { scenes: [3, 8], seconds: [3, 10], total: 60, orbit: 120, say: [60, 220] };
const clamp = (v, lo, hi, d) => (Number.isFinite(+v) && v !== null && v !== '' ? Math.min(hi, Math.max(lo, +v)) : d);
const list = (v, ok) => [...new Set((Array.isArray(v) ? v : typeof v === 'string' ? [v] : []).filter((id) => ok.has(id)))];

export function cleanTour(raw, e) {
  const parts = new Set(e.parts.map((p) => p.id)), drives = new Set((e.drives || []).map((d) => d.id)), max = TOUR.say[e.lang === 'en' ? 1 : 0];
  const out = [];
  let total = 0;
  for (const s of Array.isArray(raw) ? raw : []) {
    const say = String(s?.say ?? '').replace(/\s+/g, ' ').trim().slice(0, max);
    if (!say) continue;   // a shot without a line has nothing to hold it on screen
    const c = { say, seconds: clamp(s.seconds, ...TOUR.seconds, 5), focus: list(s.focus, parts), orbit: clamp(s.orbit, -TOUR.orbit, TOUR.orbit, 0),
      explode: clamp(s.explode, 0, 1, 0), xray: clamp(s.xray, 0, 1, 0), isolate: list(s.isolate, parts), detach: list(s.detach, parts) };
    if (drives.has(s.drive)) Object.assign(c, { drive: s.drive, speed: clamp(s.speed, -1, 1, 0.6) || 0.6 });
    if (total + c.seconds > TOUR.total) break;
    total += c.seconds; out.push(c);
    if (out.length === TOUR.scenes[1]) break;
  }
  return out;
}

// Without Muse (no key, a refusal, an outage): the same kind of tour built from the exhibit's own lessons,
// so the button never does nothing. It is marked model 'exhibit' and the page says so.
export function fallbackTour(e) {
  const en = e.lang === 'en', l = e.lessons?.[0];
  const steps = (l?.steps || []).slice(0, 4);
  return cleanTour([
    { say: e.intro || e.name, seconds: 5, orbit: 60 },
    { say: en ? 'Let the shell go see-through and look inside.' : '外殼變透明，看看裡面。', seconds: 4, xray: 0.85, orbit: 30 },
    { say: en ? 'Now pull every part apart.' : '現在把每個零件拉開。', seconds: 4, explode: 1, xray: 0.4, focus: [], orbit: -40 },
    ...steps.map((s) => ({ say: s.say, seconds: 6, isolate: s.parts, focus: s.parts, drive: [].concat(s.drive || [])[0], speed: s.speed, xray: 0.6 })),
    { say: en ? 'And back together. Now try it yourself.' : '再裝回去。換你自己動手玩。', seconds: 4, orbit: 45 },
  ], e);
}

// Plays a cleaned tour on the viewer. `line(i, scene)` shows and speaks the scene's line and resolves when it has been
// heard; the next shot waits for both the line and the scene's seconds. stop() ends it at once.
export class TourPlayer {
  constructor(viewer, { line, xray, explode, done } = {}) { Object.assign(this, { viewer, line, xray, explode, done }); this.run = 0; }
  get playing() { return this.run > 0 && this.on === this.run; }
  async play(scenes) {
    const me = this.on = ++this.run, v = this.viewer, r = v.rig;
    v.choreo.cancel(); r.reset(); v.lessonMode = true; v.userView = false;
    let out = [], cut = [];
    for (const [i, s] of scenes.entries()) {
      if (this.on !== me) return;
      r.stop();
      r.detach(out.filter((id) => !s.detach.includes(id)), { amount: 0, duration: 0.8 });   // what this shot no longer pulls out goes back
      if (s.detach.length) r.detach(s.detach, { amount: 0.35, duration: 1.2 });
      out = s.detach;
      this.explode?.(s.explode); r.tween(EASE, r.explodeTarget, s.explode, (v) => r.setExplode(v));   // the parts travel out and home, so the eye can follow them
      this.xray?.(s.xray);
      if (s.isolate.length) r.isolate(s.isolate); else { r.isolated = null; r.highlight([]); }
      if (s.drive) r.drive(s.drive, s.speed);
      // camera: after isolate (which glides on its own), so the shot's own framing wins
      r.show(cut);   // what the last close-up cut away comes back
      cut = v.shot(s.focus.length ? s.focus : null, { explode: s.explode, orbit: s.orbit, seconds: s.seconds, keep: s.isolate }) || [];
      const timer = new Promise((ok) => setTimeout(ok, s.seconds * 1000));
      await Promise.all([timer, this.line?.(i, s)]);
    }
    if (this.on !== me) return;
    r.show(cut);
    this.on = 0; v.lessonMode = false; r.stop(); r.setExplode(0); this.explode?.(0); this.xray?.(0); r.isolated = null; r.highlight([]); r.detach(out, { amount: 0 });
    v.shot(null, { orbit: 0 });
    this.done?.(true);
  }
  stop() { if (!this.playing) return; this.on = 0; this.viewer.lessonMode = false; this.viewer.spin = null; this.done?.(false); }
}
