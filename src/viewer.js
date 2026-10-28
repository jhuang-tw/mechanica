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
    Object.assign(this.controls, { enableDamping: true, enablePan: false, minDistance: 0.4, maxDistance: 6, maxPolarAngle: Math.PI * 0.55 });
    this.onPick = onPick;
    // a drag that turns or zooms the camera hands it to the user: no glide fights it, and in a lesson the steps stop re-aiming it
    let dragging = false;
    this.controls.addEventListener('start', () => (dragging = true));
    this.controls.addEventListener('end', () => (dragging = false));
    this.controls.addEventListener('change', () => { if (dragging) { this.goal = null; this.userView = true; } });
    this.pickTaps(canvas);
    addEventListener('resize', () => this.resize());
    this.resize();
    const clock = new THREE.Clock();
    r.setAnimationLoop(() => {
      const dt = Math.min(clock.getDelta(), 0.1);
      this.choreo?.update(dt); this.rig?.update(dt);
      if (r.xr.isPresenting) this.vr?.update(dt);
      else if (this.goal) {   // glide to a framing, then hand the camera back to the user
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
    if (left > w * 0.3 && left < w - 1) this.camera.setViewOffset(w, h, (w - left) / 2, 0, w, h); else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
  }

  async load(manifest, base) {
    const gltf = await preload(base + manifest.model);
    if (this.model) this.stage.remove(this.model);
    this.model = gltf.scene;   // kept: the rig resets it on every visit
    this.stage.add(this.model);
    this.rig = new Rig(this.model, manifest);
    this.studio.fit(this.model, manifest.look);
    this.rig.onIsolate = (ids) => { if (!(this.lessonMode && this.userView)) this.focus(ids); };
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
  // glide to the given parts, keeping the current viewing direction
  focus(ids) {
    const box = new THREE.Box3();
    for (const id of ids) { const p = this.rig.parts.get(id); if (p) box.expandByObject(p.obj); }
    if (box.isEmpty()) return;
    // look from the side those parts are on (an engine at the front is seen from the front, not through a wheel)
    const all = new THREE.Box3().setFromObject(this.model), size = all.getSize(new THREE.Vector3()).length();
    const out = box.getCenter(new THREE.Vector3()).sub(all.getCenter(new THREE.Vector3())).setY(0);
    const dir = this.camera.position.clone().sub(this.controls.target).normalize();
    if (out.length() > size * 0.05) dir.addScaledVector(out.normalize(), 1.5).setY(0.5).normalize();
    this.fit(box, dir, size * 0.15);
  }
  fit(box, dir, min = 0) {
    const c = box.getCenter(new THREE.Vector3()), s = Math.max(box.getSize(new THREE.Vector3()).length(), min);   // not closer than a share of the whole model
    // far enough that the bounding sphere fits the narrower field of view (portrait phones: the horizontal one)
    const v = THREE.MathUtils.degToRad(this.camera.fov), fov = Math.min(v, 2 * Math.atan(Math.tan(v / 2) * this.camera.aspect));
    const target = c.clone(); target.y -= this.camera.aspect < 1 ? s * 0.22 : 0;   // portrait: the model sits above the bottom sheet
    this.goal = { target, pos: target.clone().addScaledVector(dir, (s / 2) / Math.sin(fov / 2) * 0.95) };
  }

  // a tap (not a drag) on a part picks it; one finger dragging a movable part moves it (rig.grab), anywhere else orbits
  pickTaps(canvas) {
    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(), at = new THREE.Vector3();
    const cast = (e) => { const b = canvas.getBoundingClientRect(); ndc.set(((e.clientX - b.left) / b.width) * 2 - 1, -((e.clientY - b.top) / b.height) * 2 + 1); ray.setFromCamera(ndc, this.camera); return ray; };
    let down = null;
    // capture phase, so a grab is decided before OrbitControls sees the finger
    canvas.addEventListener('pointerdown', (e) => {
      if (down?.g) return e.stopImmediatePropagation();   // a second finger during a drag does nothing
      if (down || !this.rig) return;
      down = { x: e.clientX, y: e.clientY, id: e.pointerId, g: this.grabAt(cast(e)) };
      if (!down.g) return;
      e.stopImmediatePropagation();
      plane.setFromNormalAndCoplanarPoint(this.camera.getWorldDirection(at), down.g.at);   // the finger moves the part across the screen
      canvas.setPointerCapture(e.pointerId);
    }, true);
    canvas.addEventListener('pointermove', (e) => {
      if (e.pointerId !== down?.id || !down.g) return;
      if (cast(e).ray.intersectPlane(plane, at)) { this.rig.drag(down.g, down.g.at, at); down.g.at.copy(at); }
    });
    const up = (e) => {
      if (e.pointerId !== down?.id) return;
      const tap = Math.hypot(e.clientX - down.x, e.clientY - down.y) <= 8, id = down.g?.id;
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
