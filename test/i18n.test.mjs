// The English site: every manifest word has an English overlay, and nothing Chinese is left once it is laid over.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { localize } from '../src/localize.js';
import { S } from '../src/i18n.js';
import { exhibits, toolsFor, tutorTools, fixTools } from '../server/ai.mjs';

const load = (f) => JSON.parse(readFileSync(new URL(`../public/exhibits/${f}`, import.meta.url), 'utf8'));
const ids = load('index.json').exhibits;
const CJK = /[㐀-鿿　-〿＀-￯]/;
const chinese = (v, path = '') => typeof v === 'string' ? (CJK.test(v) ? [`${path}: ${v}`] : [])
  : Array.isArray(v) ? v.flatMap((x, i) => chinese(x, `${path}[${i}]`))
  : v && typeof v === 'object' ? Object.entries(v).flatMap(([k, x]) => chinese(x, `${path}.${k}`)) : [];

for (const id of ids) {
  test(`${id}: en.json covers the manifest`, () => {
    const m = load(`${id}/manifest.json`), o = load(`${id}/en.json`);
    for (const k of ['name', 'title', 'intro', 'suggest', 'looksLike']) assert.ok(o[k], `${id}.${k}`);
    for (const p of m.parts) assert.ok(o.parts[p.id]?.name && o.parts[p.id]?.info, `${id} part ${p.id}`);
    for (const d of m.drives || []) assert.ok(o.drives[d.id], `${id} drive ${d.id}`);
    for (const l of m.lessons || []) {
      const x = o.lessons[l.id];
      assert.ok(x?.title, `${id} lesson ${l.id}`);
      assert.equal(x.steps.length, l.steps.length, `${id} lesson ${l.id} steps`);
      l.steps.forEach((s, i) => {
        assert.ok(x.steps[i].say, `${id} ${l.id}[${i}].say`);
        assert.equal(!!x.steps[i].quiz, !!s.quiz, `${id} ${l.id}[${i}].quiz`);
        if (s.quiz) assert.equal(x.steps[i].quiz.options.length, s.quiz.options.length, `${id} ${l.id}[${i}] options`);
      });
    }
    for (const f of m.faults || []) for (const k of ['title', 'short', 'symptom', 'observe', 'hint', 'suspects', 'whys', 'cause', 'why', 'answer']) assert.ok(o.faults[f.id]?.[k], `${id} fault ${f.id}.${k}`);
    if (m.ride) assert.ok(o.ride?.hint, `${id} ride.hint`);
  });
  test(`${id}: no Chinese left in English`, () => {
    assert.deepEqual(chinese(localize(load(`${id}/manifest.json`), load(`${id}/en.json`))), []);
  });
}

test('a part added later falls back to its English search name', () => {
  const m = { parts: [{ id: 'gizmo', name: '小零件', en: 'tiny gizmo', info: '說明' }], lessons: [] };
  assert.deepEqual(localize(m, {}).parts[0], { id: 'gizmo', name: 'Tiny gizmo', en: 'tiny gizmo', info: 'Tiny gizmo', aliases: [] });
});

test('every UI string has English, and the English has no Chinese', () => {
  for (const [k, [zh, en]] of Object.entries(S)) {
    assert.ok(zh && en, k);
    const out = typeof en === 'function' ? en('x', 'y', 'z') : en;
    if (k !== 'switchTo' && k !== 'switchAria') assert.deepEqual(chinese(out), [], k);   // the switch names Chinese in Chinese
  }
});

test('the server reads the English exhibit and gives Muse English tools', () => {
  const e = exhibits('en').bike;
  assert.equal(e.name, 'Bicycle');
  assert.equal(exhibits().bike.name, '自行車');
  for (const tools of [toolsFor(e), tutorTools(e), fixTools(e, 'diagnose'), fixTools(e, 'explain')]) assert.deepEqual(chinese(tools), []);
});
