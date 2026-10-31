// 坐上去: a first-person seat on a vehicle. The camera sits at the manifest's eye point and looks around under a drag,
// the road rolls back at the speed the driven wheel turns on screen, and the readout gives the real figures for that gear.
import * as THREE from 'three';

const TILE = 4;   // metres of road per texture repeat: one 2 m dash and a gap

function roadTexture() {
  const c = Object.assign(document.createElement('canvas'), { width: 256, height: 256 }), g = c.getContext('2d');
  g.fillStyle = '#2b2f35'; g.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 900; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * 0.05})`; g.fillRect(Math.random() * 256, Math.random() * 256, 2, 2); }
  g.fillStyle = '#e8e2d0'; g.fillRect(0, 124, 128, 8);                     // centre dash
  g.fillStyle = '#d9d4c4'; g.fillRect(0, 10, 256, 5); g.fillRect(0, 241, 256, 5);   // edge lines
  const t = new THREE.CanvasTexture(c); t.wrapS = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
}

export class Ride {
  constructor(viewer) { this.v = viewer; }

  // cfg: manifest `ride` { eye, look, wheel: { part, r }, gears: [drive ids], idle, redline, see: [part ids], hide?, lane?, road? }
  start(cfg) {
    const v = this.v, c = v.controls, m = v.model;
    this.cfg = cfg; this.see = false;
    this.saved = { pos: v.camera.position.clone(), target: c.target.clone(), fov: v.camera.fov, ...pick(c) };
    v.riding = true; v.goal = null; v.rig.setExplode(0);
    m.updateMatrixWorld(true);
    const eye = m.localToWorld(new THREE.Vector3(...cfg.eye)), ahead = m.localToWorld(new THREE.Vector3(...cfg.eye).add(new THREE.Vector3(...cfg.look).normalize().multiplyScalar(0.1)));
    // orbit a point 10 cm ahead with the drag reversed: looking around from the seat
    Object.assign(c, { minDistance: 0.1, maxDistance: 0.1, enableZoom: false, enablePan: false, rotateSpeed: -0.35, minPolarAngle: Math.PI * 0.15, maxPolarAngle: Math.PI * 0.85 });
    c.target.copy(ahead); v.camera.position.copy(eye); c.update();
    v.camera.fov = 70; v.camera.updateProjectionMatrix();   // a seat needs a wider view than the showcase
    // the road: along +x (the way the vehicle faces), centre line on the driver's left
    const len = 240, wide = cfg.road || 12;
    this.tex = roadTexture(); this.tex.repeat.set(len / TILE, 1);
    this.road = new THREE.Mesh(new THREE.PlaneGeometry(len, wide).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ map: this.tex, roughness: 0.92 }));
    this.road.position.set(0, 0.002, (cfg.lane ?? -1.75)); this.road.receiveShadow = true;
    m.add(this.road);
    v.studio.floor.visible = false;
    v.rig.hide(cfg.hide);   // a shell with painted-on windows would blind the seat: it opens up like a convertible
    this.thr = 0.3; this.gear(0);
  }

  // drive in gear i (0-based) at the current throttle; the rig turns slowed down, the readout is real
  gear(i) { this.g = Math.max(0, Math.min(this.cfg.gears.length - 1, i)); this.apply(); }
  throttle(t) { this.thr = Math.max(0, Math.min(1, t)); this.apply(); }
  apply() {
    const { rig } = this.v, cfg = this.cfg, id = cfg.gears[this.g], d = rig.m.drives.find((x) => x.id === id);
    const speed = 0.4 + this.thr * 2.6, wheel = Math.abs(d.moves.find((mv) => mv.part === cfg.wheel.part).ratio);
    rig.stop(); rig.drive(id, speed);
    this.roll = (d.rpm / 60) * 2 * Math.PI * speed * wheel * cfg.wheel.r;   // on-screen road speed, m/s
    const rpm = cfg.idle + this.thr * (cfg.redline - cfg.idle);
    this.read = { gear: this.g + 1, rpm: Math.round(rpm / 50) * 50, kmh: Math.round((rpm / 60) * wheel * 2 * Math.PI * cfg.wheel.r * 3.6) };
  }

  // 透視: the body goes glassy and the drivetrain shows while it runs
  xray(on) {
    const { rig } = this.v;
    this.see = on;
    if (on) rig.isolate(this.cfg.see); else { rig.isolated = null; rig.lit.clear(); rig.paint(); }
  }

  update(dt) { if (this.tex) this.tex.offset.x = (this.tex.offset.x + (this.roll * dt) / TILE) % 1; }

  stop() {
    const v = this.v, c = v.controls;
    if (!v.riding) return;
    v.riding = false;
    this.road.removeFromParent(); this.road.geometry.dispose(); this.road.material.dispose(); this.tex.dispose(); this.tex = null;
    v.studio.floor.visible = true;
    v.rig.show(this.cfg.hide);
    v.camera.fov = this.saved.fov; v.camera.updateProjectionMatrix();
    Object.assign(c, this.saved.opts); c.target.copy(this.saved.target); v.camera.position.copy(this.saved.pos); c.update();
  }
}
const pick = (c) => ({ opts: { minDistance: c.minDistance, maxDistance: c.maxDistance, enableZoom: c.enableZoom, enablePan: c.enablePan, rotateSpeed: c.rotateSpeed, minPolarAngle: c.minPolarAngle, maxPolarAngle: c.maxPolarAngle } });
