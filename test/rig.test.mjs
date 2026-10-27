// Rig + choreography on the placeholder bike, in Node (no renderer).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { Rig } from '../src/rig.js';
import { Choreo, cleanSteps } from '../src/choreo.js';

const manifest = JSON.parse(readFileSync(new URL('../public/exhibits/bike/manifest.json', import.meta.url), 'utf8'));
const glb = readFileSync(new URL('../public/exhibits/bike/model.glb', import.meta.url));
const load = () => new Promise((ok, no) => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parse(glb.buffer.slice(glb.byteOffset, glb.byteOffset + glb.byteLength), '', (g) => ok(g.scene), no));
const run = (rig, s, dt = 0.05) => { for (let t = 0; t < s; t += dt) rig.update(dt); };

test('manifest: every part, drive move and lesson part exists in the model', async () => {
  const root = await load();
  const ids = new Set(manifest.parts.map((p) => p.id));
  for (const id of ids) assert.ok(root.getObjectByName(id), `model has ${id}`);
  for (const d of manifest.drives) for (const m of d.moves) assert.ok(ids.has(m.part), `${d.id}: ${m.part}`);
  for (const l of manifest.lessons) for (const s of l.steps) {
    for (const p of s.parts) assert.ok(ids.has(p), `${l.id}: ${p}`);
    if (s.drive) assert.ok(manifest.drives.some((d) => d.id === s.drive));
    if (s.quiz) assert.equal(s.quiz.options.filter((o) => o[1] === true).length, 1, `${s.quiz.q}: one right answer`);
  }
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
