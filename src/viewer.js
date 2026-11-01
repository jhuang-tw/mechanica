// 3D view: renderer, camera, orbit controls, loading an exhibit, tapping parts, and the optional VR session.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { Rig } from './rig.js';
import { Choreo } from './choreo.js';
import { Studio } from './look.js';

const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
const cache = new Map();   // url -> Promise<gltf>
export const preload = (url) => (cache.has(url) || cache.set(url, loader.loadAsync(url)), cache.get(url));

export class Viewer {
  constructor(canvas, { onPick, panel } = {}) {
    this.panel = panel;   // the element covering the right side, if any: the view is centred on what's left
    const r = this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    r.setPixelRatio(Math.min(devicePixelRatio, 2));
    r.xr.enabled = true;
    const scene = this.scene = new THREE.Scene();
    this.stage = new THREE.Group();   // the exhibit sits on this; VR moves the stage, not the camera
    scene.add(this.stage);
    this.studio = new Studio(r, scene, this.stage, matchMedia('(pointer: coarse)').matches);
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.02, 100);
    this.controls = new OrbitControls(this.camera, canvas);
    Object.assign(this.controls, { enableDamping: true, minDistance: 0.4, maxDistance: 6, maxPolarAngle: Math.PI * 0.55 });
    this.onPick = onPick;
    // a drag that turns, zooms or pans the camera hands it to the user: no glide fights it, and in a lesson the steps stop re-aiming it
    let dragging = false;
    this.controls.addEventListener('start', () => (dragging = true));
    this.controls.addEventListener('end', () => (dragging = false));
    this.controls.addEventListener('change', () => { if (dragging) { this.goal = null; this.spin = null; this.userView = true; } });
    this.pickTaps(canvas);
    addEventListener('resize', () => this.resize());
    this.resize();
    const timer = new THREE.Timer(); timer.connect(document);
    r.setAnimationLoop(() => {
      const dt = Math.min(timer.update().getDelta(), 0.1);
      this.choreo?.update(dt); this.rig?.update(dt); this.ride?.update(dt);
      if (r.xr.isPresenting) this.vr?.update(dt);
      else if (this.spin) this.circle(dt);
      if (!r.xr.isPresenting && this.goal) {   // glide to a framing, then hand the camera back to the user
        const k = Math.min(1, dt * 3);
        this.controls.target.lerp(this.goal.target, k); this.camera.position.lerp(this.goal.pos, k);
        if (this.camera.position.distanceTo(this.goal.pos) < 0.005) this.goal = null;
      }
      if (!r.xr.isPresenting) this.controls.update();
      this.studio.update();
      r.render(scene, this.camera);
    });
  }

  resize() {
    const { clientWidth: w, clientHeight: h } = this.renderer.domElement.parentElement;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    const left = this.panel?.getBoundingClientRect().left ?? w;
    const side = left > w * 0.3 && left < w - 1;
    if (side) this.camera.setViewOffset(w, h, (w - left) / 2, 0, w, h); else this.camera.clearViewOffset();
    this.seen = (side ? left : w) / h;   // the aspect of the part of the canvas the panel leaves clear
    this.camera.updateProjectionMatrix();
  }

  async load(manifest, base) {
    const gltf = await preload(base + manifest.model);
    if (this.model) this.stage.remove(this.model);
    this.model = gltf.scene;   // kept: the rig resets it on every visit
    this.stage.add(this.model);
    this.rig = new Rig(this.model, manifest);
    this.studio.fit(this.model, manifest.look);
    this.rig.onIsolate = (ids) => { if (!this.riding && !(this.lessonMode && this.userView)) this.focus(ids); };
    this.choreo = new Choreo(this.rig);
    this.frame();
    this.vr?.fitStage();
    return this.rig;
  }

  // camera to a three-quarter view of the whole model
  frame() {
    this.goal = null; this.userView = false;
    const box = new THREE.Box3().setFromObject(this.model), s = box.getSize(new THREE.Vector3()).length();
    Object.assign(this.controls, { minDistance: s * 0.05, maxDistance: s * 4 });
    this.fit(box, new THREE.Vector3(...(this.rig?.m.view || [0.55, 0.35, 1])).normalize());   // manifest `view`: the side worth seeing first (a cutaway)
    this.camera.position.copy(this.goal.pos); this.controls.target.copy(this.goal.target); this.goal = null;
    this.controls.update();
  }
  // one shot of a tour: glide to the parts (null: the whole machine, framed wider the more it is pulled apart), then circle
  // `orbit` degrees around it over `seconds`. In VR the headset is the camera, so only the parts light up.
  // Returns the parts it took out of the way (a close-up cuts away whatever faded part sits between the camera and the
  // subject, all along the orbit), so the caller can show them again.
  shot(ids, { explode = 0, orbit = 0, seconds = 5, keep = [] } = {}) {
    const n = this.shotN = (this.shotN || 0) + 1;
    let cut = [];
    if (ids?.length) { this.outside(this.focus(ids, 0.4), this.boxAt(explode)); cut = this.cutaway(new Set([...ids, ...keep]), orbit, explode); }
    else if (explode < 0.3) this.fill(this.boxAt(explode), this.camera.position.clone().sub(this.controls.target).normalize());
    else {   // pulled apart: from the side of its long axis (an engine's parts line up along the shaft), filling the frame
      const box = this.boxAt(explode), d = box.getSize(new THREE.Vector3()), dir = d.x >= d.z ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(1, 0, 0);
      if (dir.dot(this.camera.position.clone().sub(this.controls.target)) < 0) dir.negate();   // the side the camera is already on
      this.fill(box, dir.setY(0.3).normalize());
      orbit = Math.max(-25, Math.min(25, orbit));   // a wide turn would swing the long side away again
      // once the parts have landed, frame them again from their real vertices (the estimate above runs a little wide)
      setTimeout(() => {
        if (this.shotN !== n || this.userView || !this.model) return;
        const at = this.goal ? this.goal.pos.clone().sub(this.goal.target) : this.camera.position.clone().sub(this.controls.target);
        this.fill(new THREE.Box3().setFromObject(this.model), at.normalize(), 1.04, this.corners());
      }, 3000);
    }
    this.spin = orbit ? { rate: THREE.MathUtils.degToRad(orbit) / seconds, left: seconds } : null;
    return cut;
  }
  cutaway(keep, orbit, explode) {
    if (!this.goal) return [];
    const { target, pos } = this.goal, y = new THREE.Vector3(0, 1, 0), ray = new THREE.Ray(), hit = new THREE.Vector3(), b = new THREE.Box3(), cut = [];
    const eyes = [0, 0.5, 1].map((k) => pos.clone().sub(target).applyAxisAngle(y, THREE.MathUtils.degToRad(orbit * k)).add(target));
    for (const [id, p] of this.rig.parts) {
      if (keep.has(id) || !p.obj.visible) continue;
      let holds = false;   // a part carrying a kept part (a case around its gears) would take it along
      p.obj.traverse((o) => { if (o !== p.obj && keep.has(o.name)) holds = true; });
      if (holds) continue;
      b.setFromObject(p.obj);
      if (b.isEmpty()) continue;
      const m = p.obj.parent.matrixWorld, v = p.explodeVec.clone().multiplyScalar(explode - this.rig.explode).applyMatrix4(m).sub(new THREE.Vector3().applyMatrix4(m));
      b.translate(v);
      if (eyes.some((e) => { const d = e.distanceTo(target); ray.set(e, target.clone().sub(e).normalize()); return ray.intersectBox(b, hit) && e.distanceTo(hit) < d * 0.9; })) cut.push(id);
    }
    this.rig.hide(cut);
    return cut;
  }
  // push the camera back along its line of sight until it is clear of the whole machine's box
  outside(ok, box) {
    if (!ok || !this.goal) return;
    const dir = this.goal.pos.clone().sub(this.goal.target).normalize(), exit = new THREE.Ray(this.goal.target, dir).intersectBox(box.clone().expandByScalar(box.getSize(new THREE.Vector3()).length() * 0.06), new THREE.Vector3());
    if (exit && exit.distanceTo(this.goal.target) > this.goal.pos.distanceTo(this.goal.target)) this.goal.pos.copy(exit);
  }
  // where the machine will be once the explode reaches `t` (it eases there over half a second): each part's box moved along its explode vector
  boxAt(t) {
    const box = new THREE.Box3(), b = new THREE.Box3(), o = new THREE.Vector3(), v = new THREE.Vector3();
    for (const p of this.rig.parts.values()) {
      if (!p.obj.visible) continue;
      b.setFromObject(p.obj);
      if (b.isEmpty()) continue;
      const m = p.obj.parent.matrixWorld;
      v.copy(p.explodeVec).multiplyScalar(t - this.rig.explode).applyMatrix4(m).sub(o.set(0, 0, 0).applyMatrix4(m));
      box.union(b.translate(v));
    }
    return box.isEmpty() ? new THREE.Box3().setFromObject(this.model) : box;
  }
  // the corners of every visible mesh's box: far tighter than one box around a machine pulled apart in all directions
  corners() {
    const pts = [], b = new THREE.Box3();
    this.model.traverseVisible((o) => {
      if (!o.isMesh || o.material.opacity < 0.05) return;
      b.setFromObject(o);
      if (!b.isEmpty()) for (let i = 0; i < 8; i++) pts.push(new THREE.Vector3(i & 1 ? b.max.x : b.min.x, i & 2 ? b.max.y : b.min.y, i & 4 ? b.max.z : b.min.z));
    });
    return pts;
  }
  // close enough that the box's corners (or the given points) just fit the clear part of the view, looking along -dir
  fill(box, dir, margin = 1.06, pts = null) {
    const c = box.getCenter(new THREE.Vector3()), v = THREE.MathUtils.degToRad(this.camera.fov) / 2, tv = Math.tan(v), th = tv * (this.seen || this.camera.aspect);
    const right = new THREE.Vector3(0, 1, 0).cross(dir).normalize(), up = dir.clone().cross(right).normalize(), k = new THREE.Vector3();
    let dist = 0;
    if (pts?.length) { box = new THREE.Box3().setFromPoints(pts); box.getCenter(c); }
    const all = pts?.length ? pts : Array.from({ length: 8 }, (_, i) => new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z));
    // centre on the middle of what the camera will see, not of the box: then both sides can come to the edge
    let lo = Infinity, hi = -Infinity, dn = Infinity, upm = -Infinity;
    for (const q of all) { const x = q.clone().sub(c); lo = Math.min(lo, x.dot(right)); hi = Math.max(hi, x.dot(right)); dn = Math.min(dn, x.dot(up)); upm = Math.max(upm, x.dot(up)); }
    c.addScaledVector(right, (lo + hi) / 2).addScaledVector(up, (dn + upm) / 2);
    for (const q of all) {
      k.copy(q).sub(c);
      dist = Math.max(dist, k.dot(dir) + Math.abs(k.dot(right)) / th, k.dot(dir) + Math.abs(k.dot(up)) / tv);
    }
    const target = c.clone(); if ((this.seen || this.camera.aspect) < 1) target.y -= (box.max.y - box.min.y) * 0.3;   // portrait: above the bottom sheet
    this.goal = { target, pos: target.clone().addScaledVector(dir, dist * margin) };
  }
  circle(dt) {
    const a = this.spin.rate * Math.min(dt, this.spin.left), y = new THREE.Vector3(0, 1, 0);
    if ((this.spin.left -= dt) <= 0) this.spin = null;
    const around = (p, c) => p.sub(c).applyAxisAngle(y, a).add(c);
    around(this.camera.position, this.controls.target);
    if (this.goal) around(this.goal.pos, this.goal.target);
  }
  // glide to the given parts, keeping the current viewing direction
  focus(ids, near = 0.15) {
    const box = new THREE.Box3();
    for (const id of ids) { const p = this.rig.parts.get(id); if (p) box.expandByObject(p.obj); }
    if (box.isEmpty()) return false;
    // look from the side those parts are on (an engine at the front is seen from the front, not through a wheel)
    const all = new THREE.Box3().setFromObject(this.model), size = all.getSize(new THREE.Vector3()).length();
    const out = box.getCenter(new THREE.Vector3()).sub(all.getCenter(new THREE.Vector3())).setY(0);
    const dir = this.camera.position.clone().sub(this.controls.target).normalize();
    if (out.length() > size * 0.05) dir.addScaledVector(out.normalize(), 1.5).setY(0.5).normalize();
    this.fit(box, dir, size * near);
    return true;
  }
  fit(box, dir, min = 0) {
    const c = box.getCenter(new THREE.Vector3()), s = Math.max(box.getSize(new THREE.Vector3()).length(), min);   // not closer than a share of the whole model
    // far enough that the bounding sphere fits the narrower field of view (portrait phones: the horizontal one)
    const v = THREE.MathUtils.degToRad(this.camera.fov), fov = Math.min(v, 2 * Math.atan(Math.tan(v / 2) * this.camera.aspect));
    const target = c.clone(); target.y -= this.camera.aspect < 1 ? s * 0.22 : 0;   // portrait: the model sits above the bottom sheet
    this.goal = { target, pos: target.clone().addScaledVector(dir, (s / 2) / Math.sin(fov / 2) * 0.95) };
  }

  // a tap (not a drag) on a part picks it; one finger dragging a movable part moves it (rig.grab), anywhere else orbits; two fingers pinch and pan
  pickTaps(canvas) {
    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(), at = new THREE.Vector3();
    const cast = (e) => { const b = canvas.getBoundingClientRect(); ndc.set(((e.clientX - b.left) / b.width) * 2 - 1, -((e.clientY - b.top) / b.height) * 2 + 1); ray.setFromCamera(ndc, this.camera); return ray; };
    let down = null;
    // capture phase, so a grab is decided before OrbitControls sees the finger
    canvas.addEventListener('pointerdown', (e) => {
      if (down) {   // a second finger ends any part drag; OrbitControls never saw the first finger then, so it is replayed for the pinch
        down.two = true;
        if (down.g) { this.rig.release(down.g); down.g = null; canvas.dispatchEvent(new PointerEvent('pointerdown', down.e)); }
        return;
      }
      if (!this.rig) return;
      down = { x: e.clientX, y: e.clientY, id: e.pointerId, e, g: this.grabAt(cast(e)) };
      if (!down.g) return;
      e.stopImmediatePropagation();
      plane.setFromNormalAndCoplanarPoint(this.camera.getWorldDirection(at), down.g.at);   // the finger moves the part across the screen
      canvas.setPointerCapture(e.pointerId);
    }, true);
    canvas.addEventListener('pointermove', (e) => {
      if (e.pointerId !== down?.id || !down.g) return;
      down.e = e;
      if (cast(e).ray.intersectPlane(plane, at)) { this.rig.drag(down.g, down.g.at, at); down.g.at.copy(at); }
    });
    const up = (e) => {
      if (e.pointerId !== down?.id) return;
      const tap = !down.two && Math.hypot(e.clientX - down.x, e.clientY - down.y) <= 8, id = down.g?.id;
      this.rig?.release(down.g); down = null;
      if (tap && e.type === 'pointerup' && this.rig) this.onPick?.(id ?? this.hit(cast(e)));
    };
    canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up);
  }
  hits(ray) { return ray.intersectObject(this.model, true).filter((h) => h.object.visible && !(h.object.material.opacity < 0.5)); }
  hit(ray) { const h = this.hits(ray)[0]; return h ? this.rig.partOf(h.object) : null; }
  // the movable part under a ray, held: {…rig handle, at: the world point grabbed, dist: along the ray}
  grabAt(ray) {
    const h = this.hits(ray)[0], id = h && this.rig.partOf(h.object), g = id && this.rig.grab(id);
    return g ? Object.assign(g, { at: h.point.clone(), dist: h.distance }) : null;
  }

  // ---- VR (optional): see vr.js ----
  static async vrSupported() { try { return !!(await navigator.xr?.isSessionSupported('immersive-vr')); } catch { return false; } }
  async enterVR(app) {
    const { VR } = await import('./vr.js');
    this.vr = new VR(this, app);
    try { await this.vr.start(); } catch (e) { this.vr.end(); throw e; }
    return this.vr;
  }
}
