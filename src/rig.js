// Part rig: everything the app (and the AI) can do to an exhibit's parts, driven by its manifest.
// Pure three.js (no renderer, no DOM), so tests run it in Node. Every motion is relative to the pose the model loaded in,
// and reset() always gets back there.
import * as THREE from 'three';

const AMBER = new THREE.Color(1, 0.62, 0.15), GHOST = 0.1, TAU = Math.PI * 2;
const DIRS = { up: [0, 1, 0], down: [0, -1, 0], front: [1, 0, 0], back: [-1, 0, 0], left: [0, 0, -1], right: [0, 0, 1] };
const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

export class Rig {
  constructor(root, manifest) {
    this.root = root; this.m = manifest;
    this.parts = new Map();   // id -> { obj, def, base: {pos, quat}, angle, offset, explodeDir, meshes }
    const box = new THREE.Box3().setFromObject(root);
    this.size = box.getSize(new THREE.Vector3()).length() || 1;
    const centre = box.getCenter(new THREE.Vector3());
    const ids = new Set(manifest.parts.map((p) => p.id));
    for (const def of manifest.parts) {
      const obj = root.getObjectByName(def.id);
      if (!obj) { console.warn(`model has no node "${def.id}"`); continue; }
      const meshes = [];
      obj.traverse((o) => { if (o.isMesh) { o.material = o.material.clone(); o.userData.part = def.id; meshes.push({ o, base: { opacity: o.material.opacity, transparent: o.material.transparent, emissive: o.material.emissive?.clone() } }); } });
      // explode: straight out from the model's centre; parts inside other parts ride with their parent.
      // shortcut: offsets are applied in the parent's space, so non-part container nodes must be unrotated and unscaled
      const c = new THREE.Box3().setFromObject(obj).getCenter(new THREE.Vector3()).sub(centre);
      let nested = false;   // inside another part (pedals on the crank)
      for (let o = obj.parent; o && o !== root; o = o.parent) if (ids.has(o.name)) nested = true;
      this.parts.set(def.id, {
        obj, def, meshes, nested,
        base: { pos: obj.position.clone(), quat: obj.quaternion.clone() },
        axis: new THREE.Vector3(...(def.axis || [0, 0, 1])).normalize(),
        angle: 0, offset: new THREE.Vector3(),
        explodeDir: nested ? new THREE.Vector3() : (c.lengthSq() < 1e-6 ? new THREE.Vector3(0, 1, 0) : c.normalize()),
      });
    }
    this.explode = 0; this.explodeTarget = 0;
    this.tweens = []; this.spins = new Map();   // part id -> rad/s
    this.lit = new Set(); this.isolated = null;
  }

  ids(list) { return (list || []).filter((id) => this.parts.has(id)); }
  partOf(object) { for (let o = object; o; o = o.parent) if (o.userData.part) return o.userData.part; return null; }

  // ---- looks ----
  highlight(ids) { this.lit = new Set(this.ids(ids)); this.paint(); }
  isolate(ids) { this.isolated = new Set(this.ids(ids)); this.lit = new Set(this.isolated); this.paint(); }
  paint() {
    for (const [id, p] of this.parts) {
      const ghost = this.isolated && !this.isolated.has(id), lit = this.lit.has(id);
      for (const { o, base } of p.meshes) {
        if (o.material.transparent !== (ghost || base.transparent)) { o.material.transparent = ghost || base.transparent; o.material.needsUpdate = true; }
        o.material.opacity = ghost ? GHOST : base.opacity;
        o.material.depthWrite = !ghost;
        if (o.material.emissive) o.material.emissive.copy(lit ? AMBER : base.emissive).multiplyScalar(lit ? 0.45 : 1);
      }
    }
  }
  hide(ids) { for (const id of this.ids(ids)) this.parts.get(id).obj.visible = false; }
  show(ids) { for (const id of this.ids(ids)) this.parts.get(id).obj.visible = true; }

  // ---- motion ----
  // turn by `degrees` over `duration` s, or keep turning at `rpm` (0 stops)
  rotate(ids, { degrees, rpm, duration = 1.5 } = {}) {
    for (const id of this.ids(ids)) {
      const p = this.parts.get(id);
      if (rpm !== undefined) { if (rpm) this.spins.set(id, (rpm / 60) * TAU); else this.spins.delete(id); continue; }
      this.tween(duration, p.angle, p.angle + ((degrees ?? 90) * Math.PI) / 180, (v) => (p.angle = v));
    }
  }
  // pull parts out along a direction (`dir` from DIRS, or straight out from the centre); amount = share of the model's size
  detach(ids, { dir, amount = 0.3, duration = 1 } = {}) {
    for (const id of this.ids(ids)) {
      const p = this.parts.get(id), from = p.offset.clone();
      const to = (DIRS[dir] ? new THREE.Vector3(...DIRS[dir]) : p.explodeDir.clone()).multiplyScalar(amount * this.size * 0.5);
      this.tween(duration, 0, 1, (k) => p.offset.lerpVectors(from, to, k));
    }
  }
  // a real mechanism: every part in the drive turns at its ratio; speed −1…1, 0 stops it
  drive(id, speed = 0.5) {
    const d = this.m.drives?.find((x) => x.id === id);
    if (!d) return false;
    for (const mv of d.moves) if (this.parts.has(mv.part)) this.spin(mv.part, speed ? (d.rpm / 60) * TAU * speed * mv.ratio : 0);
    return true;
  }
  spin(id, rad) { if (rad) this.spins.set(id, rad); else this.spins.delete(id); }
  stop() { this.spins.clear(); }
  setExplode(t) { this.explodeTarget = Math.min(1, Math.max(0, t)); }

  reset() {
    this.tweens = []; this.spins.clear(); this.lit.clear(); this.isolated = null; this.explodeTarget = 0;
    for (const p of this.parts.values()) { p.angle = 0; p.offset.set(0, 0, 0); p.obj.visible = true; }
    this.paint();
  }

  tween(dur, from, to, set) { this.tweens.push({ t: 0, dur: Math.max(dur, 0.01), from, to, set }); }

  update(dt) {
    this.tweens = this.tweens.filter((w) => { w.t += dt; const k = Math.min(1, w.t / w.dur); w.set(w.from + (w.to - w.from) * ease(k)); return k < 1; });
    for (const [id, w] of this.spins) this.parts.get(id).angle += w * dt;
    this.explode += (this.explodeTarget - this.explode) * Math.min(1, dt * 6);
    const q = new THREE.Quaternion();
    for (const p of this.parts.values()) {
      p.obj.quaternion.copy(p.base.quat).multiply(q.setFromAxisAngle(p.axis, p.angle));
      p.obj.position.copy(p.base.pos).add(p.offset).addScaledVector(p.explodeDir, this.explode * this.size * 0.2);
    }
  }
}
