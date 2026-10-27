// AI-composed demonstrations: a list of timed steps from /api/ask, played on the Rig.
// Steps are model output, so every field is checked here: unknown parts and actions are dropped, numbers are clamped.
export const LIMITS = { steps: 16, total: 30, duration: [0.3, 10], degrees: 1080, rpm: 60, amount: 1 };
const ACTIONS = new Set(['highlight', 'isolate', 'hide', 'show', 'detach', 'translate', 'rotate', 'drive', 'reset']);
const clamp = (v, lo, hi, d) => (Number.isFinite(+v) ? Math.min(hi, Math.max(lo, +v)) : d);

export function cleanSteps(raw, manifest) {
  const parts = new Set(manifest.parts.map((p) => p.id)), drives = new Set((manifest.drives || []).map((d) => d.id));
  const out = [];
  for (const s of Array.isArray(raw) ? raw : []) {
    if (!s || !ACTIONS.has(s.do)) continue;
    const step = { do: s.do === 'translate' ? 'detach' : s.do, at: clamp(s.at, 0, LIMITS.total, 0) };
    if (!['drive', 'reset'].includes(step.do)) {
      step.parts = (Array.isArray(s.parts) ? s.parts : [s.part]).filter((id) => parts.has(id));
      if (!step.parts.length) continue;
    }
    if (step.do === 'drive') { if (!drives.has(s.drive)) continue; step.drive = s.drive; step.speed = clamp(s.speed, -1, 1, 0.5); }
    if (s.duration !== undefined) step.duration = clamp(s.duration, ...LIMITS.duration, 2);
    if (step.do === 'rotate') {
      if (s.rpm !== undefined) step.rpm = clamp(s.rpm, -LIMITS.rpm, LIMITS.rpm, 10);
      else step.degrees = clamp(s.degrees, -LIMITS.degrees, LIMITS.degrees, 90);
    }
    if (step.do === 'detach') { step.dir = s.dir; step.amount = clamp(s.amount, 0, LIMITS.amount, 0.3); }
    out.push(step);
  }
  return out.sort((a, b) => a.at - b.at).slice(0, LIMITS.steps);
}

export class Choreo {
  constructor(rig) { this.rig = rig; this.queue = []; this.t = 0; this.stops = []; }
  get playing() { return this.queue.length > 0 || this.stops.length > 0; }
  play(steps) { this.cancel(); this.rig.reset(); this.queue = [...steps]; this.t = 0; }
  cancel() { this.queue = []; this.stops = []; }
  update(dt) {
    this.t += dt;
    while (this.queue.length && this.queue[0].at <= this.t) this.run(this.queue.shift());
    this.stops = this.stops.filter(([at, fn]) => (at <= this.t ? (fn(), false) : true));
  }
  run(s) {
    const r = this.rig, end = (fn) => s.duration && this.stops.push([this.t + s.duration, fn]);
    switch (s.do) {
      case 'highlight': return r.highlight([...r.lit, ...s.parts]);
      case 'isolate': return r.isolate(s.parts);
      case 'hide': return r.hide(s.parts);
      case 'show': return r.show(s.parts);
      case 'detach': return r.detach(s.parts, s);
      case 'rotate': r.rotate(s.parts, s); return s.rpm !== undefined && end(() => r.rotate(s.parts, { rpm: 0 }));
      case 'drive': r.drive(s.drive, s.speed); return end(() => r.drive(s.drive, 0));
      case 'reset': return r.reset();
    }
  }
}
