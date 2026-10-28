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
    this.parts = new Map();   // id -> { obj, def, base: {pos, quat}, angle, offset, explodeVec, meshes }
    const box = new THREE.Box3().setFromObject(root);
    this.size = box.getSize(new THREE.Vector3()).length() || 1;
    const centre = box.getCenter(new THREE.Vector3());
    const ids = new Set(manifest.parts.map((p) => p.id));
    for (const def of manifest.parts) {
      const obj = root.getObjectByName(def.id);
      if (!obj) { console.warn(`model has no node "${def.id}"`); continue; }
      const meshes = [], own = (o) => {   // this part's meshes, not those of parts nested inside it (a wheel inside its knuckle)
        if (o.isMesh) { o.material = o.material.clone(); o.userData.part = def.id; meshes.push({ o, base: { opacity: o.material.opacity, transparent: o.material.transparent, emissive: o.material.emissive?.clone() } }); }
        for (const c of o.children) if (!ids.has(c.name)) own(c);
      };
      own(obj);
      // explode: the model's own vector (node extras `explode`, metres) or straight out from the centre;
      // parts inside other parts ride with their parent unless they have their own vector.
      // shortcut: offsets are applied in the parent's space, so non-part container nodes must be unrotated and unscaled
      const c = new THREE.Box3().setFromObject(obj).getCenter(new THREE.Vector3()).sub(centre), ex = obj.userData.explode;
      let nested = false;   // inside another part (pedals on the crank)
      for (let o = obj.parent; o && o !== root; o = o.parent) if (ids.has(o.name)) nested = true;
      this.parts.set(def.id, {
        obj, def, meshes, nested,
        base: { pos: obj.position.clone(), quat: obj.quaternion.clone() },
        axis: new THREE.Vector3(...(def.axis || obj.userData.axis || [0, 0, 1])).normalize(),
        angle: 0, offset: new THREE.Vector3(),
        explodeVec: Array.isArray(ex) ? new THREE.Vector3(...ex) : nested ? new THREE.Vector3()
          : (c.lengthSq() < 1e-6 ? new THREE.Vector3(0, 1, 0) : c.normalize()).multiplyScalar(this.size * 0.2),
      });
    }
    this.explode = 0; this.explodeTarget = 0;
    this.tweens = []; this.spins = new Map();   // part id -> rad/s
    this.swings = new Map();   // part id -> { amp (rad), w (rad/s), t }: back-and-forth, like a steering wheel
    this.linkages = (manifest.linkages || []).filter((l) => (l.type === 'slider_crank' && this.parts.has(l.crank)) || (l.type === 'swashplate' && this.parts.has(l.mast)));
    this.lit = new Set(); this.isolated = null;
    this.fault = null;   // a repair challenge: { def, stops } — the parts in `stops` don't take the drive's motion until repair
  }

  ids(list) { return (list || []).filter((id) => this.parts.has(id)); }
  partOf(object) { for (let o = object; o; o = o.parent) if (o.userData.part) return o.userData.part; return null; }

  // ---- looks ----
  highlight(ids) { this.lit = new Set(this.ids(ids)); this.paint(); }
  isolate(ids) { this.isolated = new Set(this.ids(ids)); this.lit = new Set(this.isolated); this.paint(); this.onIsolate?.([...this.isolated]); }
  paint() {
    for (const [id, p] of this.parts) {
      const ghost = this.isolated && !this.isolated.has(id), lit = this.lit.has(id);
      for (const { o, base } of p.meshes) {
        if (o.material.transparent !== (ghost || base.transparent)) { o.material.transparent = ghost || base.transparent; o.material.needsUpdate = true; }
        o.material.opacity = ghost ? GHOST : base.opacity;
        o.material.depthWrite = !ghost;
        if (o.material.userData.rim) o.material.userData.rim.value = lit ? 1 : 0;   // look.js: rim glow, the material stays visible
        else if (o.material.emissive) o.material.emissive.copy(lit ? AMBER : base.emissive).multiplyScalar(lit ? 0.45 : 1);
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
      const to = (DIRS[dir] ? new THREE.Vector3(...DIRS[dir]) : p.explodeVec.clone().normalize()).multiplyScalar(amount * this.size * 0.5);
      this.tween(duration, 0, 1, (k) => p.offset.lerpVectors(from, to, k));
    }
  }
  // a real mechanism: every part in the drive turns at its ratio; speed −1…1, 0 stops it
  drive(id, speed = 0.5) {
    const d = this.m.drives?.find((x) => x.id === id);
    if (!d) return false;
    for (const mv of d.moves) {
      const p = this.parts.get(mv.part);
      if (!p || this.fault?.stops.has(mv.part)) continue;
      if (!d.swing) { this.spin(mv.part, speed ? (d.rpm / 60) * TAU * speed * mv.ratio : 0); continue; }
      // a move with `slide` (metres, at full swing) slides back and forth instead of turning, like the lenses on an IPD rail
      if (speed) this.swings.set(mv.part, { amp: (d.swing * mv.ratio * Math.sign(speed) * Math.PI) / 180, w: (TAU / (mv.period || d.period || 4)) * Math.abs(speed), t: 0, oneWay: !!d.oneWay, slide: mv.slide && new THREE.Vector3(...mv.slide).multiplyScalar(Math.sign(speed)) });
      else if (this.swings.delete(mv.part)) { p.angle = 0; if (mv.slide) p.offset.set(0, 0, 0); }
    }
    return true;
  }
  spin(id, rad) { if (rad) this.spins.set(id, rad); else this.spins.delete(id); }
  stop() { this.spins.clear(); for (const [id, s] of this.swings) { const p = this.parts.get(id); p.angle = 0; if (s.slide) p.offset.set(0, 0, 0); } this.swings.clear(); }
  setExplode(t) { this.explodeTarget = Math.min(1, Math.max(0, t)); }

  reset() {
    this.tweens = []; this.stop(); this.lit.clear(); this.isolated = null; this.explodeTarget = 0;
    for (const p of this.parts.values()) { p.angle = 0; p.offset.set(0, 0, 0); p.obj.visible = true; }
    this.brokenLook();
    this.paint();
  }
  // ---- repair challenge: a manifest fault breaks the drive (parts in `stops` stay still) and can show the damage
  // (`look.detach`: the broken part sits out of place). reset() keeps the fault; setFault(null) repairs it.
  setFault(def) { this.fault = def ? { def, stops: new Set(this.ids(def.stops)) } : null; this.reset(); }
  brokenLook() {
    const l = this.fault?.def.look;
    if (l?.detach) for (const id of this.ids(l.detach.parts || this.fault.def.broken)) {
      const p = this.parts.get(id);
      p.offset.copy(DIRS[l.detach.dir] ? new THREE.Vector3(...DIRS[l.detach.dir]) : p.explodeVec.clone().normalize()).multiplyScalar((l.detach.amount ?? 0.1) * this.size * 0.5);
    }
    for (const id of this.ids(l?.hide)) this.parts.get(id).obj.visible = false;
  }

  // ---- hands-on: drag a part with a finger or a VR hand. What it does comes from the manifest: a part in a drive
  // (or a piston, rod or blade on its crank or mast, or a pedal riding its crank) turns the whole mechanism at its
  // ratios, a door or lever stays within its swing, a part with its own axis turns alone, anything else pulls out
  // along its explode direction. Parts marked `fixed` don't move (dragging them orbits the view instead).
  grab(id) {
    const members = (l) => [l.crank, l.mast, l.hub, ...(l.plates || []), ...(l.blades || []), ...(l.cylinders || []).flatMap((c) => [c.piston, c.rod, c.valve, ...(c.slides || []), ...(c.follow || [])])];
    for (let o = this.parts.get(id)?.obj; o && o !== this.root; o = o.parent) {
      const p = this.parts.get(o.name);
      if (p?.obj !== o) continue;
      if (p.def.fixed) { if (o.name === id) return null; break; }   // a part on a fixed base still moves itself
      const l = this.linkages.find((x) => members(x).includes(o.name)), at = l ? l.crank || l.mast : o.name, drive = this.driveOf(at);
      const mv = drive?.moves.find((m) => m.part === at);
      if (drive) return this.hold(id, { part: at, mv, drive: drive.oneWay ? { ...drive, moves: [mv] } : drive });   // oneWay panels (doors, hood) hang on their own hinges
    }
    const p = this.parts.get(id);
    if (!p) return null;
    if (p.def.axis || p.obj.userData.axis) return this.hold(id, { part: id, mv: { part: id, ratio: 1 } });
    return this.hold(id, { part: id, pull: (p.explodeVec.lengthSq() ? p.explodeVec.clone() : new THREE.Vector3(0, 1, 0)).normalize() });
  }
  // the drive this part is the input of (the biggest one), else the smallest it is in: a bike's rear wheel coasts without the crank
  driveOf(id) {
    const n = (d) => d.moves.length * (d.moves[0].part === id ? -1 : 1);
    return (this.m.drives || []).filter((d) => d.moves.some((mv) => mv.part === id)).sort((a, b) => n(a) - n(b))[0];
  }
  hold(id, h) {
    for (const mv of h.drive?.moves || []) { this.spins.delete(mv.part); this.swings.delete(mv.part); }   // the hand takes over from the motor
    const p = this.parts.get(h.part), d = h.drive, slide = h.mv?.slide && new THREE.Vector3(...h.mv.slide);
    if (d?.swing) { h.amp = (d.swing * h.mv.ratio * Math.PI) / 180; h.k = slide ? p.offset.dot(slide) / slide.lengthSq() : p.angle / h.amp; }
    h.id = id; h.was = new Set(this.lit); this.lit.add(id); this.paint();
    return h;
  }
  // move a held part as the hand goes from `from` to `to` (world points)
  drag(h, from, to) {
    const p = this.parts.get(h.part), par = p.obj.parent, a = par.worldToLocal(from.clone()), d = par.worldToLocal(to.clone()).sub(a);   // in the part's parent space
    if (h.pull) { p.offset.copy(h.pull).multiplyScalar(Math.min(this.size * 0.3, Math.max(0, p.offset.dot(h.pull) + d.dot(h.pull)))); return; }
    let da;
    if (h.mv.slide) { const v = new THREE.Vector3(...h.mv.slide); da = (d.dot(v) / v.lengthSq()) * h.amp; }
    else {   // the angle the hand sweeps around the part's axis
      const axis = p.axis.clone().applyQuaternion(p.base.quat), r = a.sub(p.obj.position);
      r.addScaledVector(axis, -r.dot(axis));
      da = d.dot(axis.clone().cross(r)) / Math.max(r.lengthSq(), (this.size * 0.03) ** 2);
    }
    if (!h.drive) { p.angle += da; return; }
    // a fault splits the drive: turning the input leaves the stopped parts still, turning a stopped part moves only those
    const side = (mv) => !this.fault || this.fault.stops.has(mv.part) === this.fault.stops.has(h.part);
    if (!h.drive.swing) { for (const mv of h.drive.moves) { const q = this.parts.get(mv.part); if (q && side(mv)) q.angle += (da * mv.ratio) / h.mv.ratio; } return; }
    h.k = Math.min(1, Math.max(h.drive.oneWay ? 0 : -1, h.k + da / h.amp));
    for (const mv of h.drive.moves) {
      const q = this.parts.get(mv.part);
      if (!side(mv)) continue;
      if (q && mv.slide) q.offset.set(...mv.slide).multiplyScalar(h.k); else if (q) q.angle = ((h.drive.swing * mv.ratio * Math.PI) / 180) * h.k;
    }
  }
  release(h) { if (h) { this.lit = h.was; this.paint(); } }

  tween(dur, from, to, set) { this.tweens.push({ t: 0, dur: Math.max(dur, 0.01), from, to, set }); }

  update(dt) {
    this.tweens = this.tweens.filter((w) => { w.t += dt; const k = Math.min(1, w.t / w.dur); w.set(w.from + (w.to - w.from) * ease(k)); return k < 1; });
    for (const [id, w] of this.spins) this.parts.get(id).angle += w * dt;
    // swings: back and forth, or with oneWay 0 → amp → 0 (a door)
    for (const [id, s] of this.swings) { const a = (s.t += dt) * s.w, k = s.oneWay ? (1 - Math.cos(a)) / 2 : Math.sin(a), p = this.parts.get(id); if (s.slide) p.offset.copy(s.slide).multiplyScalar(k); else p.angle = s.amp * k; }
    this.explode += (this.explodeTarget - this.explode) * Math.min(1, dt * 6);
    const q = new THREE.Quaternion();
    for (const p of this.parts.values()) {
      p.obj.quaternion.copy(p.base.quat).multiply(q.setFromAxisAngle(p.axis, p.angle));
      p.obj.position.copy(p.base.pos).add(p.offset).addScaledVector(p.explodeVec, this.explode);
    }
    for (const l of this.linkages) if (l.type === 'swashplate') this.swashplate(l); else this.sliderCrank(l);
  }

  // engine: each piston (and anything in `slides`, like a crosshead) moves along `up`; the rod swings from the crankpin
  // to the wrist pin; parts in `follow` (coupling rods) move with the crankpin without turning; an optional valve
  // slides `valveAmp` metres, `valveLead` radians ahead of the crank. Pin offsets turn with the crank itself,
  // so the motion follows the crank's axis and direction.
  sliderCrank(l) {
    const crank = this.parts.get(l.crank), up = new THREE.Vector3(...(l.up || [0, 1, 0]));
    const axis = crank.axis.clone().applyQuaternion(crank.base.quat), r = l.r, L = l.L;
    const pin = (a) => up.clone().applyAxisAngle(axis, a).multiplyScalar(r);   // crankpin, from the crank centre
    const wrist = (a) => { const q = pin(a), along = q.dot(up), side = q.clone().addScaledVector(up, -along); return up.clone().multiplyScalar(along + Math.sqrt(L * L - side.lengthSq())); };
    const rodDir = (a) => wrist(a).sub(pin(a)).normalize();
    for (const c of l.cylinders) {
      const a0 = c.phase || 0, a = crank.angle + a0, slide = wrist(a).dot(up) - wrist(a0).dot(up), move = pin(a).sub(pin(a0));
      for (const id of [c.piston, ...(c.slides || [])]) this.parts.get(id)?.obj.position.addScaledVector(up, slide);
      for (const id of c.follow || []) this.parts.get(id)?.obj.position.add(move);
      const rod = this.parts.get(c.rod);
      if (rod) {
        rod.obj.position.add(move);
        rod.obj.quaternion.copy(new THREE.Quaternion().setFromUnitVectors(rodDir(a0), rodDir(a))).multiply(rod.base.quat);
      }
      const valve = this.parts.get(c.valve);
      if (valve) valve.obj.position.addScaledVector(up, c.valveAmp * (Math.sin(a + c.valveLead) - Math.sin(a0 + c.valveLead)));
    }
  }

  // helicopter: the collective lever raises both plates and pitches both blades together; the cyclic stick tilts the
  // plates toward it and pitches each blade by sin(azimuth), so the disc (teetering hub) tilts 90° later, toward the stick.
  // The rotor turns about +y; blade i sits at azimuth mast.angle + i·2π/n.
  swashplate(l) {
    const lever = (c) => { const p = c && this.parts.get(c.part); return p ? Math.max(-1, Math.min(1, p.angle / ((c.max * Math.PI) / 180))) : 0; };
    const col = lever(l.collective), cyc = lever(l.cyclic), rad = Math.PI / 180, mast = this.parts.get(l.mast);
    const up = new THREE.Vector3(0, 1, 0), tilt = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -cyc * l.tilt * rad);   // front edge down
    const spin = mast.obj.quaternion.clone().multiply(mast.base.quat.clone().invert()), unspin = spin.clone().invert();
    for (const id of l.plates || []) {
      const p = this.parts.get(id);
      if (!p) continue;
      const q = p.obj.parent === mast.obj ? unspin.clone().multiply(tilt).multiply(spin) : tilt;   // a plate riding the mast tilts in world space
      p.obj.position.addScaledVector(up, col * l.rise);
      p.obj.quaternion.premultiply(q);
    }
    const blades = this.ids(l.blades), az = mast.angle, q = new THREE.Quaternion();
    blades.forEach((id, i) => {
      const p = this.parts.get(id), a = az + (i * TAU) / blades.length;
      p.obj.quaternion.copy(p.base.quat).multiply(q.setFromAxisAngle(p.axis, (col * l.pitch + cyc * l.cyclicPitch * Math.sin(a)) * rad));
    });
    const hub = this.parts.get(l.hub);   // teeter: blade 1 low at the front when the stick is forward
    if (hub) hub.obj.quaternion.copy(hub.base.quat).multiply(q.setFromAxisAngle(hub.axis, cyc * l.flap * rad * Math.cos(az)));
  }
}
