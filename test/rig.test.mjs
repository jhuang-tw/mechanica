// Rig + choreography on the real exhibit models, in Node (no renderer).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { Rig } from '../src/rig.js';
import { Choreo, cleanSteps } from '../src/choreo.js';

const read = (f) => readFileSync(new URL(`../public/exhibits/${f}`, import.meta.url));
const exhibit = (id) => JSON.parse(read(`${id}/manifest.json`));
const loadModel = (id) => { const b = read(`${id}/model.glb`); return new Promise((ok, no) => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parse(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), '', (g) => ok(g.scene), no)); };
const manifest = exhibit('bike'), load = () => loadModel('bike');
const run = (rig, s, dt = 0.05) => { for (let t = 0; t < s; t += dt) rig.update(dt); };

for (const id of JSON.parse(read('index.json')).exhibits) {
  test(`${id}: every part, drive move, linkage and lesson part exists in the model`, async () => {
    const m = exhibit(id), root = await loadModel(id);
    const ids = new Set(m.parts.map((p) => p.id));
    for (const p of ids) assert.ok(root.getObjectByName(p), `model has ${p}`);
    for (const d of m.drives) for (const mv of d.moves) assert.ok(ids.has(mv.part), `${d.id}: ${mv.part}`);
    for (const l of m.linkages || []) for (const c of l.cylinders) assert.ok(ids.has(c.piston) && ids.has(c.rod), JSON.stringify(c));
    for (const l of m.lessons) for (const s of l.steps) {
      for (const p of s.parts) assert.ok(ids.has(p), `${l.id}: ${p}`);
      if (s.drive) assert.ok(m.drives.some((d) => d.id === s.drive));
      if (s.quiz) assert.equal(s.quiz.options.filter((o) => o[1] === true).length, 1, `${s.quiz.q}: one right answer`);
    }
  });
}

test('car: pistons and rods follow the crank (slider-crank), steering swings the knuckles', async () => {
  const m = exhibit('car'), rig = new Rig(await loadModel('car'), m), L = m.linkages[0];
  const p1 = rig.parts.get('piston_1'), p2 = rig.parts.get('piston_2'), rod = rig.parts.get('conrod_1'), crank = rig.parts.get('crankshaft');
  rig.update(0);
  assert.ok(p1.obj.position.distanceTo(p1.base.pos) < 1e-9, 'at rest the model pose is kept');
  for (const a of [0.7, Math.PI, 4]) {
    crank.angle = a; rig.update(0);
    assert.ok(Math.abs(p1.obj.position.distanceTo(rod.obj.position) - L.L) < 1e-6, `rod length kept at ${a}`);
  }
  crank.angle = Math.PI; rig.update(0);
  assert.ok(Math.abs(p1.base.pos.y - p1.obj.position.y - 2 * L.r) < 1e-6, 'cylinder 1 at bottom dead centre');
  assert.ok(Math.abs(p2.obj.position.y - p2.base.pos.y - 2 * L.r) < 1e-6, 'cylinder 2 at top dead centre');
  rig.reset(); rig.drive('steer', 1); run(rig, 1);
  const k = rig.parts.get('knuckle_fl'), w = rig.parts.get('steering_wheel');
  assert.ok(Math.abs(k.angle) > 0.05 && Math.abs(k.angle / w.angle - 0.0667) < 1e-6);
  rig.reset(); run(rig, 0.1);
  assert.equal(k.angle, 0);
});

test('drive turns the chain of parts at their ratios, reset puts everything back', async () => {
  const root = await load(), rig = new Rig(root, manifest);
  const crank = root.getObjectByName('crank'), q0 = crank.quaternion.clone(), wheel = rig.parts.get('rear_wheel');
  rig.drive('pedal', 1); run(rig, 1);
  assert.ok(Math.abs(wheel.angle / rig.parts.get('crank').angle - 2.94) < 1e-6);
  assert.ok(crank.quaternion.angleTo(q0) > 0.1);
  const fw = rig.parts.get('front_wheel');
  rig.setExplode(1); rig.isolate(['chain']); run(rig, 2);
  assert.ok(fw.obj.position.distanceTo(fw.base.pos) > 0.1, 'explode moves parts out');
  rig.reset(); run(rig, 3);
  assert.ok(crank.quaternion.angleTo(q0) < 1e-6);
  for (const p of rig.parts.values()) assert.ok(p.obj.position.distanceTo(p.base.pos) < 1e-3, `${p.def.id} back in place`);
});

test('cleanSteps drops unknown parts and actions, clamps numbers', () => {
  const s = cleanSteps([
    { do: 'rotate', parts: ['crank', 'rocket'], degrees: 99999, at: 2 },
    { do: 'launch_missiles', parts: ['frame'] },
    { do: 'drive', drive: 'warp', at: 0 },
    { do: 'drive', drive: 'pedal', speed: 9, duration: 50, at: -3 },
    { do: 'isolate', parts: ['nope'] },
  ], manifest);
  assert.deepEqual(s, [{ do: 'drive', at: 0, drive: 'pedal', speed: 1, duration: 10 }, { do: 'rotate', at: 2, parts: ['crank'], degrees: 1080 }]);
});

test('choreography plays steps on time and stops a timed drive', async () => {
  const rig = new Rig(await load(), manifest), c = new Choreo(rig);
  c.play(cleanSteps([{ do: 'isolate', parts: ['chainring'], at: 0 }, { do: 'drive', drive: 'pedal', at: 1, duration: 1 }], manifest));
  c.update(0.5); assert.ok(rig.isolated.has('chainring')); assert.equal(rig.spins.size, 0);
  c.update(0.6); assert.ok(rig.spins.size > 0);
  c.update(1.0); assert.equal(rig.spins.size, 0); assert.equal(c.playing, false);
});
