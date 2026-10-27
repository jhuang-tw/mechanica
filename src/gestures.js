// Hand-pose math on plain {x,y,z} joints (WebXR joint names), so it runs in Node tests without a headset.
const sub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
const len = (v) => Math.hypot(v.x, v.y, v.z);
const BONES = ['metacarpal', 'phalanx-proximal', 'phalanx-intermediate', 'phalanx-distal', 'tip'];

// per finger (index..pinky): straight ≈ 1, curled into a fist ≈ 0.5 (chord from knuckle to tip over the bone path)
export function curls(j) {
  return ['index', 'middle', 'ring', 'pinky'].map((f) => {
    const p = BONES.map((b) => j[`${f}-finger-${b}`]);
    if (p.some((q) => !q)) return null;
    let path = 0;
    for (let i = 1; i < p.length; i++) path += len(sub(p[i], p[i - 1]));
    return path > 1e-4 ? len(sub(p[4], p[0])) / path : 1;
  });
}
// a fist curls all four fingers (pointing or pinching keeps one straight); open = all four straight. `was` adds hysteresis.
export const isFist = (j, was) => { const c = curls(j); return !c.includes(null) && Math.max(...c) < (was ? 0.82 : 0.75); };
export const isOpen = (j, was) => { const c = curls(j); return !c.includes(null) && Math.min(...c) > (was ? 0.8 : 0.88); };
export const isPinch = (j) => !!(j['thumb-tip'] && j['index-finger-tip']) && len(sub(j['thumb-tip'], j['index-finger-tip'])) < 0.02;

// unit vector out of the palm; the left hand is the mirror image of the right
export function palmNormal(j, side) {
  const w = j.wrist, i = j['index-finger-phalanx-proximal'], p = j['pinky-finger-phalanx-proximal'];
  if (!w || !i || !p) return null;
  const a = sub(i, w), b = sub(p, w), s = side === 'left' ? -1 : 1;
  const n = { x: (a.y * b.z - a.z * b.y) * s, y: (a.z * b.x - a.x * b.z) * s, z: (a.x * b.y - a.y * b.x) * s }, l = len(n);
  return l > 1e-8 ? { x: n.x / l, y: n.y / l, z: n.z / l } : null;
}

// Two fists held together: the first motion past its threshold claims the hold — pull apart = explode,
// twist the hand-to-hand line = turn, move both = push away / lift. The others stay frozen until a fist opens.
export const LOCK = { explode: 0.05, rotate: 0.26, move: 0.06 };   // metres, radians, metres
export const twoHandStart = (L, R, s) => ({ d: len(sub(R, L)), ang: Math.atan2(R.z - L.z, R.x - L.x), mid: mid(L, R), mode: null, ...s });
const mid = (L, R) => ({ x: (L.x + R.x) / 2, y: (L.y + R.y) / 2, z: (L.z + R.z) / 2 });
export function twoHand(start, L, R, fwd) {
  const dd = len(sub(R, L)) - start.d, m = sub(mid(L, R), start.mid), mf = m.x * fwd.x + m.z * fwd.z, mv = Math.hypot(mf, m.y);
  let da = Math.atan2(R.z - L.z, R.x - L.x) - start.ang; da = Math.atan2(Math.sin(da), Math.cos(da));
  if (!start.mode) {
    const r = { explode: Math.abs(dd) / LOCK.explode, rotate: Math.abs(da) / LOCK.rotate, move: mv / LOCK.move };
    const best = Object.keys(r).reduce((a, b) => (r[b] > r[a] ? b : a));
    if (r[best] >= 1) start.mode = best;
  }
  const dz = (v, z) => (Math.abs(v) < z ? 0 : v - Math.sign(v) * z), o = { mode: start.mode, explode: start.explode, yaw: start.yaw, dist: start.dist, height: start.height };
  if (start.mode === 'explode') o.explode = Math.min(1, Math.max(0, start.explode + dz(dd, LOCK.explode) * 1.8));   // ~55 cm of pull = fully apart
  else if (start.mode === 'rotate') o.yaw = start.yaw - dz(da, LOCK.rotate) * 1.5;
  else if (start.mode === 'move' && mv > LOCK.move) { const k = 1 - LOCK.move / mv; o.dist = start.dist + mf * k * 2.5; o.height = start.height + m.y * k * 1.5; }
  return o;
}
