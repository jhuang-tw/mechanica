// Hand-pose math on plain {x,y,z} joints (WebXR joint names), so it runs in Node tests without a headset.
const d3 = (a, b) => [a.x - b.x, a.y - b.y, a.z - b.z];
const mag = ([x, y, z]) => Math.sqrt(x * x + y * y + z * z);
const FINGERS = ['index', 'middle', 'ring', 'pinky'];

// how far a finger is folded, in degrees: the angle between its first bone (knuckle) and its last (tip)
function bend(j, f) {
  const k = j[`${f}-finger-metacarpal`], p = j[`${f}-finger-phalanx-proximal`], d = j[`${f}-finger-phalanx-distal`], t = j[`${f}-finger-tip`];
  if (!k || !p || !d || !t) return null;
  const a = d3(p, k), b = d3(t, d), c = (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (mag(a) * mag(b) || 1);
  return (Math.acos(Math.max(-1, Math.min(1, c))) * 180) / Math.PI;
}
const bends = (j) => FINGERS.map((f) => bend(j, f));
// fist: every finger folded (pointing or pinching leaves one out); open: every finger nearly straight. `was` = hysteresis.
export const isFist = (j, was) => { const b = bends(j); return !b.includes(null) && Math.min(...b) > (was ? 80 : 100); };
export const isOpen = (j, was) => { const b = bends(j); return !b.includes(null) && Math.max(...b) < (was ? 45 : 30); };
export const isPinch = (j) => !!(j['thumb-tip'] && j['index-finger-tip']) && mag(d3(j['thumb-tip'], j['index-finger-tip'])) < 0.02;

// unit vector out of the palm: across the knuckles × along the hand, mirrored for the left hand
export function palmNormal(j, side) {
  const w = j.wrist, m = j['middle-finger-metacarpal'], i = j['index-finger-metacarpal'], p = j['pinky-finger-metacarpal'];
  if (!w || !m || !i || !p) return null;
  const across = d3(p, i), along = d3(m, w), s = side === 'left' ? 1 : -1;
  const n = [across[1] * along[2] - across[2] * along[1], across[2] * along[0] - across[0] * along[2], across[0] * along[1] - across[1] * along[0]], l = mag(n);
  return l > 1e-9 ? { x: (s * n[0]) / l, y: (s * n[1]) / l, z: (s * n[2]) / l } : null;
}

// Two fists held together. Whichever of spread (hands apart), twist (turning the line between them) or shift
// (both hands moving) passes its threshold first owns the hold until a fist opens; the other two don't move.
const START = { spread: 0.05, twist: 0.25, shift: 0.06 };   // metres, radians, metres
const GAIN = { spread: 1.8, twist: 1.5, push: 2.5, lift: 1.5 };
const pose = (L, R) => ({ gap: mag(d3(R, L)), heading: Math.atan2(R.z - L.z, R.x - L.x), centre: { x: (L.x + R.x) / 2, y: (L.y + R.y) / 2, z: (L.z + R.z) / 2 } });
export const twoHandStart = (L, R, placed) => ({ from: pose(L, R), placed: { ...placed }, mode: null });
export function twoHand(hold, L, R, toward) {
  const now = pose(L, R), f = hold.from;
  const spread = now.gap - f.gap, twist = Math.atan2(Math.sin(now.heading - f.heading), Math.cos(now.heading - f.heading));
  const mv = d3(now.centre, f.centre), push = mv[0] * toward.x + mv[2] * toward.z, lift = mv[1], shift = Math.hypot(push, lift);
  hold.mode ||= [['spread', Math.abs(spread)], ['twist', Math.abs(twist)], ['shift', shift]].map(([k, v]) => [k, v / START[k]]).sort((a, b) => b[1] - a[1]).find(([, r]) => r >= 1)?.[0] || null;
  const past = (v, k) => Math.sign(v) * Math.max(0, Math.abs(v) - START[k]), p = { ...hold.placed, mode: hold.mode };
  if (hold.mode === 'spread') p.explode = Math.min(1, Math.max(0, p.explode + past(spread, 'spread') * GAIN.spread));
  if (hold.mode === 'twist') p.yaw -= past(twist, 'twist') * GAIN.twist;
  if (hold.mode === 'shift' && shift > 0) { const k = Math.max(0, shift - START.shift) / shift; p.dist += push * k * GAIN.push; p.height += lift * k * GAIN.lift; }
  return p;
}
