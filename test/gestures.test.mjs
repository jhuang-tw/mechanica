// Hand gestures on synthetic joints: fist / open / pinch, palm direction, and the two-fist hold locking to one action.
import test from 'node:test';
import assert from 'node:assert/strict';
import { isFist, isOpen, isPinch, palmNormal, twoHand, twoHandStart } from '../src/gestures.js';

const v = (x, y, z) => ({ x, y, z });
// a right hand, palm down, fingers along -z (index on the thumb side, -x); `curl` folds the fingers under
function hand(curl) {
  const j = { wrist: v(0, 0, 0), 'thumb-tip': v(-0.05, -0.01, -0.06) };
  ['index', 'middle', 'ring', 'pinky'].forEach((f, i) => {
    const x = -0.03 + i * 0.02, pts = curl
      ? [v(x, 0, -0.03), v(x, 0, -0.07), v(x, -0.03, -0.08), v(x, -0.04, -0.06), v(x, -0.03, -0.045)]
      : [v(x, 0, -0.03), v(x, 0, -0.07), v(x, 0, -0.11), v(x, 0, -0.13), v(x, 0, -0.15)];
    ['metacarpal', 'phalanx-proximal', 'phalanx-intermediate', 'phalanx-distal', 'tip'].forEach((b, k) => (j[`${f}-finger-${b}`] = pts[k]));
  });
  return j;
}

test('fist, open hand and pinch are told apart', () => {
  assert.ok(isFist(hand(true)) && !isOpen(hand(true)));
  assert.ok(isOpen(hand(false)) && !isFist(hand(false)));
  const pinch = { ...hand(false), 'thumb-tip': hand(false)['index-finger-tip'] };
  assert.ok(isPinch(pinch) && !isPinch(hand(false)));
});

test('palm normal points out of the palm, mirrored for the left hand', () => {
  assert.ok(palmNormal(hand(false), 'right').y < -0.9, 'right palm down');
  const mirror = Object.fromEntries(Object.entries(hand(false)).map(([k, p]) => [k, v(-p.x, p.y, p.z)]));
  assert.ok(palmNormal(mirror, 'left').y < -0.9, 'left palm down');
});

test('two fists: one action per hold — pulling apart explodes, twisting turns, moving pushes away', () => {
  const L = v(-0.2, 1.2, -0.3), R = v(0.2, 1.2, -0.3), base = { explode: 0, yaw: 0, dist: 1, height: 0 }, fwd = v(0, 0, -1);
  let s = twoHandStart(L, R, base), o = twoHand(s, v(-0.35, 1.2, -0.3), v(0.35, 1.2, -0.3), fwd);
  assert.equal(o.mode, 'spread'); assert.ok(o.explode > 0.3 && o.yaw === 0 && o.dist === 1);
  s = twoHandStart(L, R, base); o = twoHand(s, v(-0.17, 1.2, -0.1), v(0.17, 1.2, -0.5), fwd);
  assert.equal(o.mode, 'twist'); assert.ok(o.yaw !== 0 && o.explode === 0);
  s = twoHandStart(L, R, base); o = twoHand(s, v(-0.2, 1.2, -0.5), v(0.2, 1.2, -0.5), fwd);
  assert.equal(o.mode, 'shift'); assert.ok(o.dist > 1.3, 'pushed away');
  o = twoHand(s, v(-0.4, 1.2, -0.5), v(0.4, 1.2, -0.5), fwd);
  assert.equal(o.mode, 'shift', 'stays locked'); assert.equal(o.explode, 0);
});
