// Vector icons for the VR panels, drawn straight onto a canvas so they look the same on every headset browser
// (emoji fonts differ between Quest Browser, Chrome and Wolvic, and some show empty boxes). Each icon is drawn on a
// 100 x 100 grid in one colour, scaled into a size x size box centred on (cx, cy).
const TAU = Math.PI * 2;

const ICONS = {
  gear(g) {
    g.beginPath();
    for (let i = 0; i < 8; i++) for (const [da, r] of [[-0.3, 30], [-0.17, 44], [0.17, 44], [0.3, 30]]) {
      const a = (i * TAU) / 8 + da; g.lineTo(50 + r * Math.cos(a), 50 + r * Math.sin(a));
    }
    g.closePath(); g.moveTo(64, 50); g.arc(50, 50, 14, 0, TAU, true); g.fill('evenodd');
  },
  close(g) { line(g, 11, [25, 25, 75, 75], [75, 25, 25, 75]); },
  prev(g) { line(g, 12, [62, 16, 30, 50, 62, 84]); },
  next(g) { line(g, 12, [38, 16, 70, 50, 38, 84]); },
  // a lesson: a play button in a ring
  lesson(g) {
    g.lineWidth = 7; g.beginPath(); g.arc(50, 50, 40, 0, TAU); g.stroke();
    g.beginPath(); g.moveTo(40, 30); g.lineTo(70, 50); g.lineTo(40, 70); g.closePath(); g.fill();
  },
  // AI tutor: a mortarboard
  tutor(g) {
    g.beginPath(); g.moveTo(50, 18); g.lineTo(94, 38); g.lineTo(50, 58); g.lineTo(6, 38); g.closePath(); g.fill();
    g.beginPath(); g.moveTo(26, 50); g.lineTo(26, 70); g.quadraticCurveTo(50, 88, 74, 70); g.lineTo(74, 50); g.lineTo(50, 61); g.closePath(); g.fill();
    line(g, 5, [88, 41, 88, 70]); g.beginPath(); g.arc(88, 74, 6, 0, TAU); g.fill();
  },
  // guess first: a question mark
  guess(g) {
    line(g, 10, null); g.beginPath(); g.moveTo(32, 34); g.quadraticCurveTo(32, 12, 51, 12); g.quadraticCurveTo(70, 12, 70, 32);
    g.quadraticCurveTo(70, 44, 56, 52); g.quadraticCurveTo(50, 56, 50, 66); g.stroke();
    g.beginPath(); g.arc(50, 84, 7, 0, TAU); g.fill();
  },
  // explode: four blocks pushed out from the centre
  explode(g) {
    for (const [x, y] of [[8, 8], [62, 8], [8, 62], [62, 62]]) rrect(g, x, y, 30, 30, 5), g.fill();
    line(g, 6, [42, 42, 48, 48], [58, 42, 52, 48], [42, 58, 48, 52], [58, 58, 52, 52]);
  },
  // put together: the same four blocks closed into one square
  assemble(g) {
    for (const [x, y] of [[16, 16], [52, 16], [16, 52], [52, 52]]) rrect(g, x, y, 32, 32, 4), g.fill();
  },
  // reset: an arrow coming back round
  reset(g) {
    g.lineWidth = 10; g.beginPath(); g.arc(50, 52, 32, -Math.PI * 0.6, Math.PI * 1.15); g.stroke();
    g.beginPath(); g.moveTo(22, 4); g.lineTo(52, 18); g.lineTo(24, 38); g.closePath(); g.fill();
  },
  mic(g) {
    rrect(g, 36, 6, 28, 52, 14); g.fill();
    g.lineWidth = 7; g.beginPath(); g.arc(50, 44, 26, 0, Math.PI); g.stroke();
    line(g, 7, [50, 70, 50, 88], [34, 92, 66, 92]);
  },
  stop(g) { rrect(g, 22, 22, 56, 56, 8); g.fill(); },
  exit(g) {
    line(g, 8, [42, 14, 16, 14, 16, 86, 42, 86]);
    line(g, 9, [38, 50, 88, 50], [68, 30, 88, 50, 68, 70]);
  },
};

// round-capped polylines; each argument is [x0, y0, x1, y1, ...]
function line(g, w, ...runs) {
  g.lineWidth = w;
  for (const r of runs) {
    if (!r) continue;
    g.beginPath(); g.moveTo(r[0], r[1]);
    for (let i = 2; i < r.length; i += 2) g.lineTo(r[i], r[i + 1]);
    g.stroke();
  }
}
function rrect(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }

export const ICON_IDS = Object.keys(ICONS);

export function drawIcon(g, id, cx, cy, size, color) {
  const draw = ICONS[id];
  if (!draw) return;
  g.save();
  g.translate(cx - size / 2, cy - size / 2); g.scale(size / 100, size / 100);
  g.fillStyle = g.strokeStyle = color; g.lineCap = g.lineJoin = 'round';
  draw(g);
  g.restore();
}
