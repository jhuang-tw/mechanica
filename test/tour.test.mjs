// The Muse tour's scene checks, and the exhibit's own tour for every exhibit in both languages.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cleanTour, fallbackTour, TOUR } from '../src/tour.js';
import { exhibits } from '../server/ai.mjs';

test('cleanTour bounds count and length and drops unknown ids', () => {
  const e = exhibits()['bike'];
  const many = Array.from({ length: 20 }, (_, i) => ({ say: `第 ${i} 個鏡頭`, seconds: 10, focus: ['chain', 'x'], orbit: -999 }));
  const out = cleanTour(many, e);
  assert.equal(out.length, 6, 'stops at 60 s');
  assert.deepEqual([out[0].focus, out[0].orbit], [['chain'], -TOUR.orbit]);
  assert.deepEqual(cleanTour('nope', e), []);
  assert.deepEqual(cleanTour([{ say: 'a', seconds: '3' }, null, { seconds: 4 }], e).map((s) => s.seconds), [3]);
});

test('every exhibit has its own tour without Muse, in both languages', () => {
  for (const lang of [undefined, 'en']) for (const e of Object.values(exhibits(lang))) {
    const t = fallbackTour(e);
    assert.ok(t.length >= TOUR.scenes[0], `${e.id} ${lang}`);
    assert.ok(t.reduce((n, s) => n + s.seconds, 0) <= TOUR.total);
    assert.ok(t.some((s) => s.explode === 1) && t.some((s) => s.xray > 0.5));
  }
});
