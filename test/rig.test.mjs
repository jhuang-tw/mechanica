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
// Node has no image decoder: textures load as 1×1 stand-ins (the rig only needs nodes and materials)
globalThis.self ??= globalThis;
globalThis.createImageBitmap ??= async () => ({ width: 1, height: 1, close() {} });
const loadModel = (id) => { const b = read(`${id}/model.glb`); return new Promise((ok, no) => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parse(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), '', (g) => ok(g.scene), no)); };
const manifest = exhibit('bike'), load = () => loadModel('bike');
const run = (rig, s, dt = 0.05) => { for (let t = 0; t < s; t += dt) rig.update(dt); };

for (const id of JSON.parse(read('index.json')).exhibits) {
  test(`${id}: every part, drive move, linkage and lesson part exists in the model`, async () => {
    const m = exhibit(id), root = await loadModel(id);
    const ids = new Set(m.parts.map((p) => p.id));
    for (const p of ids) assert.ok(root.getObjectByName(p), `model has ${p}`);
    for (const d of m.drives) for (const mv of d.moves) assert.ok(ids.has(mv.part), `${d.id}: ${mv.part}`);
    for (const l of m.linkages || []) {
      if (l.type === 'swashplate') for (const id of [l.mast, l.hub, ...l.plates, ...l.blades, l.collective.part, l.cyclic.part]) assert.ok(ids.has(id), id);
      else for (const c of l.cylinders) assert.ok(ids.has(c.piston) && ids.has(c.rod), JSON.stringify(c));
    }
    for (const l of m.lessons) for (const s of l.steps) {
      for (const p of s.parts) assert.ok(ids.has(p), `${l.id}: ${p}`);
      for (const d of [].concat(s.drive || [])) assert.ok(m.drives.some((x) => x.id === d), d);
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

test('steam: crossheads keep the rod length, coupling rods stay level, right crank leads left by 90°', async () => {
  const m = exhibit('steam'), rig = new Rig(await loadModel('steam'), m), L = m.linkages[0], wheel = rig.parts.get('wheelset_2');
  const part = (id) => rig.parts.get(id);
  for (const a of [0, 0.8, 2.5, 4.4]) {
    wheel.angle = a; rig.update(0);
    for (const s of 'lr') {
      const d = part(`crosshead_${s}`).obj.position.clone().sub(part(`connecting_rod_${s}`).obj.position).setZ(0).length();
      assert.ok(Math.abs(d - L.L) < 1e-6, `${s} rod length at ${a}`);
      assert.ok(part(`coupling_rod_${s}`).obj.quaternion.angleTo(part(`coupling_rod_${s}`).base.quat) < 1e-9, 'coupling rod does not turn');
      assert.equal(part(`crosshead_${s}`).obj.position.x, part(`piston_${s}`).obj.position.x - part(`piston_${s}`).base.pos.x + part(`crosshead_${s}`).base.pos.x);
    }
  }
});

test('heli: collective lifts both plates and pitches both blades alike; forward cyclic tips the plate and the disc forward', async () => {
  const m = exhibit('heli'), rig = new Rig(await loadModel('heli'), m), part = (id) => rig.parts.get(id), L = m.linkages[0];
  const world = (id) => part(id).obj.getWorldPosition(new THREE.Vector3()), tip = (id) => new THREE.Vector3(id === 'blade_1' ? 3 : -3, 0, 0).applyMatrix4(part(id).obj.matrixWorld);
  const pitch = (id) => part(id).obj.quaternion.angleTo(part(id).base.quat) * 180 / Math.PI;
  const y0 = [world('swashplate_lower').y, world('swashplate_upper').y];
  part('collective').angle = (12 * Math.PI) / 180; rig.update(0); rig.root.updateMatrixWorld(true);
  assert.ok(Math.abs(world('swashplate_lower').y - y0[0] - L.rise) < 1e-6 && Math.abs(world('swashplate_upper').y - y0[1] - L.rise) < 1e-6, 'plates rise together');
  assert.ok(Math.abs(pitch('blade_1') - 8) < 1e-6 && Math.abs(pitch('blade_2') - 8) < 1e-6, 'both blades +8°');
  rig.reset(); part('cyclic').angle = (10 * Math.PI) / 180;
  for (const a of [0, 1.1, 2.7]) {   // whatever the mast angle, the plates tilt front-down and the disc is lowest at the front
    part('mast').angle = a; rig.update(0); rig.root.updateMatrixWorld(true);
    for (const id of ['swashplate_lower', 'swashplate_upper']) assert.ok(new THREE.Vector3(0, 1, 0).applyQuaternion(part(id).obj.getWorldQuaternion(new THREE.Quaternion())).x > 0.1, `${id} tips forward at ${a}`);
    const t1 = tip('blade_1'), t2 = tip('blade_2'), front = t1.x > t2.x ? t1 : t2, back = front === t1 ? t2 : t1;
    if (Math.abs(t1.x - t2.x) > 1) assert.ok(front.y < back.y, `disc lower in front at ${a}`);
  }
  rig.reset(); rig.drive('power', 1); rig.update(1);
  assert.ok(Math.abs(part('mast').angle / part('input_shaft').angle - 0.0669) < 1e-9);
});

test('car: the doors swing out one way (front-left outward to -z) and close again', async () => {
  const m = exhibit('car'), rig = new Rig(await loadModel('car'), m), door = rig.parts.get('door_fl'), hood = rig.parts.get('hood');
  const edge = () => new THREE.Vector3(-1, 0, 0).applyQuaternion(door.obj.quaternion);   // the door's rear edge, from its hinge
  rig.drive('open', 1);
  for (const t of [0.5, 1, 1, 0.5]) { rig.update(t); assert.ok(edge().z <= 1e-9, 'never into the car'); }   // 3 s = half the 6 s period: fully open
  assert.ok(Math.abs(door.angle + (70 * Math.PI) / 180) < 1e-6 && edge().z < -0.9);
  assert.ok(new THREE.Vector3(1, 0, 0).applyQuaternion(hood.obj.quaternion).y > 0.5, 'hood front lifts');
  rig.update(3); assert.ok(Math.abs(door.angle) < 1e-6, 'closed after a full period');
});

test('quest: the IPD wheel turns while both eye modules slide apart and back; stop puts them back', async () => {
  const m = exhibit('quest'), rig = new Rig(await loadModel('quest'), m), part = (id) => rig.parts.get(id);
  const gap = () => part('eye_carriage_r').obj.position.z - part('eye_carriage_l').obj.position.z, g0 = gap();
  rig.drive('ipd', 1); rig.update(1);   // a quarter of the 4 s period: fully wide
  assert.ok(Math.abs(gap() - g0 - 0.008) < 1e-6, 'IPD +8 mm');
  assert.ok(Math.abs(part('ipd_wheel').angle - Math.PI) < 1e-6, 'wheel half a turn');
  rig.stop(); rig.update(0);
  assert.ok(Math.abs(gap() - g0) < 1e-9);
});

test('jet: HP spool turns 3× the LP spool, cowls open outward, the reverser slides aft and back', async () => {
  const m = exhibit('jet'), rig = new Rig(await loadModel('jet'), m), part = (id) => rig.parts.get(id);
  rig.drive('run', 1); rig.update(1);
  assert.ok(Math.abs(part('hp_shaft').angle / part('fan').angle - 3) < 1e-9 && Math.abs(part('radial_driveshaft').angle / part('hp_shaft').angle - 1.5) < 1e-9);
  rig.reset(); rig.drive('cowls', 1); rig.drive('reverse', 1); rig.update(2.5);   // half the 5 s reverser period: fully aft
  const down = (id) => new THREE.Vector3(0, -1, 0).applyQuaternion(part(id).obj.quaternion);
  assert.ok(down('fan_cowl_left').z < -0.5 && down('fan_cowl_right').z > 0.5, 'cowls swing outward');
  assert.ok(Math.abs(part('thrust_reverser').offset.x + 0.4) < 1e-6);
  rig.stop(); rig.update(0); assert.equal(part('thrust_reverser').offset.x, 0);
});

test('watch: seconds hand 60x and hour hand 1/12 of the minute hand; the fork flicks 10 deg at twice the balance rate', async () => {
  const m = exhibit('watch'), rig = new Rig(await loadModel('watch'), m), part = (id) => rig.parts.get(id);
  rig.drive('run', 1); rig.update(1);
  const min = part('minute_hand').angle;
  assert.ok(Math.abs(part('seconds_hand').angle / min - 60) < 1e-9 && Math.abs(part('hour_hand').angle / min - 1 / 12) < 1e-9 && Math.abs(part('escape_wheel').angle / min - 720) < 1e-9);
  rig.reset(); rig.drive('tick', 1); rig.update(0.25);   // a quarter of the fork's 1 s period: its peak
  assert.ok(Math.abs(part('pallet_fork').angle - (10 * Math.PI) / 180) < 1e-6);
  assert.ok(Math.abs(part('balance').angle - (270 * Math.PI) / 180 * Math.sin(Math.PI / 4)) < 1e-6);
});

test('steam: the smokebox door swings out to the front and the cab roof lifts at the back', async () => {
  const rig = new Rig(await loadModel('steam'), exhibit('steam')), q = (id) => rig.parts.get(id).obj.quaternion;
  rig.drive('open', 1); rig.update(3);   // half the 6 s period: fully open
  assert.ok(new THREE.Vector3(0, 0, -1).applyQuaternion(q('smokebox_door')).x > 0.9, 'door edge swings forward');
  assert.ok(new THREE.Vector3(-1, 0, 0).applyQuaternion(q('cab_roof')).y > 0.5, 'roof rear edge lifts');
});

test('moto: pistons follow the slider-crank formula on the tilted bore, left 90 deg behind; 6th gear turns the wheel faster', async () => {
  const rig = new Rig(await loadModel('moto'), exhibit('moto')), part = (id) => rig.parts.get(id), up = new THREE.Vector3(0.258819, 0.965926, 0);
  const r = 0.035, L = 0.13, s = (f) => r * Math.cos(f) + Math.sqrt(L * L - (r * Math.sin(f)) ** 2);
  const pos = (id) => part(id).obj.position.dot(up), r0 = pos('piston_r'), l0 = pos('piston_l');
  rig.drive('engine', 1); rig.update(0.5);   // 40 rpm: a third of a turn
  const f = part('crankshaft').angle;
  assert.ok(Math.abs(pos('piston_r') - r0 - (s(f) - s(0))) < 1e-6);
  assert.ok(Math.abs(pos('piston_l') - l0 - (s(f - Math.PI / 2) - s(-Math.PI / 2))) < 1e-6);
  const wheel = (g) => { rig.reset(); rig.drive(g, 1); rig.update(1); return part('wheel_rear').angle; };
  assert.ok(Math.abs(wheel('gear6') / wheel('gear1') - (65 / 24) / (44 / 45)) < 1e-4);
});
