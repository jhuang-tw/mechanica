// VR mode: the exhibit at arm's length, hands drawn as joint nodes, a gear on the left inner wrist (or Y/B on a
// controller) opens the menu, two fists pull the model apart / turn / move it, a one-line subtitle fades out while
// the full answer is spoken. Holding the trigger or a pinch on a part drags it (see Rig.grab). Panels are canvas textures; a controller trigger, a pinch ray or an index-finger poke presses them.
import * as THREE from 'three';
import { isFist, isOpen, isPinch, palmNormal, twoHand, twoHandStart } from './gestures.js';

const JOINTS = ['wrist', 'thumb-metacarpal', 'thumb-phalanx-proximal', 'thumb-phalanx-distal', 'thumb-tip',
  ...['index', 'middle', 'ring', 'pinky'].flatMap((f) => ['metacarpal', 'phalanx-proximal', 'phalanx-intermediate', 'phalanx-distal', 'tip'].map((b) => `${f}-finger-${b}`))];
const C = { bg: '#141b24', btn: '#222c38', on: '#ffb13b', text: '#e8edf3', dim: '#8a97a6', rec: '#ff5a4f' };
const WHITE = new THREE.Color(0xdfe6ee), ORANGE = new THREE.Color(0xff9a2e), BLUE = new THREE.Color(0x4fb3ff);
const FONT = '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif';

// a flat panel of buttons drawn on a canvas; `buttons` = [{x, y, w, h, label?, img?, active?, on?}] in canvas pixels
class Panel {
  constructor(w, h, px = 1024) {
    this.canvas = Object.assign(document.createElement('canvas'), { width: px, height: Math.round((px * h) / w) });
    this.tex = new THREE.CanvasTexture(this.canvas); this.tex.colorSpace = THREE.SRGBColorSpace;
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: this.tex, transparent: true, toneMapped: false }));
    this.mesh.renderOrder = 10; this.mesh.visible = false; this.w = w; this.h = h; this.buttons = [];
  }
  draw(buttons, bg = C.bg) {
    const g = this.canvas.getContext('2d'), { width: W, height: H } = this.canvas;
    this.buttons = buttons;
    g.clearRect(0, 0, W, H); g.fillStyle = bg; g.beginPath(); g.roundRect(0, 0, W, H, 36); g.fill();
    for (const b of buttons) {
      g.fillStyle = b.active ? C.on : b.color || C.btn; g.beginPath(); g.roundRect(b.x, b.y, b.w, b.h, 18); g.fill();
      if (b.img?.complete && b.img.naturalWidth) { g.save(); g.beginPath(); g.roundRect(b.x + 6, b.y + 6, b.w - 12, b.h - 52, 14); g.clip(); g.drawImage(b.img, b.x + 6, b.y + 6, b.w - 12, b.h - 52); g.restore(); }
      g.fillStyle = b.active ? '#1a1206' : C.text; g.font = `${b.size || 34}px ${FONT}`; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(fit(g, b.label || '', b.w - 20), b.x + b.w / 2, b.img ? b.y + b.h - 24 : b.y + b.h / 2);
    }
    this.tex.needsUpdate = true;
  }
  // canvas-pixel button under a point in the panel's local space
  at(local) {
    const x = (local.x / this.w + 0.5) * this.canvas.width, y = (0.5 - local.y / this.h) * this.canvas.height;
    return this.buttons.find((b) => b.on && x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h);
  }
}
const fit = (g, t, w) => { if (g.measureText(t).width <= w) return t; while (t && g.measureText(t + '…').width > w) t = t.slice(0, -1); return t + '…'; };

export class VR {
  constructor(viewer, app) {
    this.v = viewer; this.app = app; this.xr = viewer.renderer.xr; this.scene = viewer.scene;
    this.root = new THREE.Group(); this.scene.add(this.root);   // everything VR adds, removed on exit
    this.menu = new Panel(0.56, 0.5); this.lessonPanel = new Panel(0.5, 0.12); this.sub = new Panel(1, 0.08, 1400);
    this.sub.mesh.material.depthTest = false; this.sub.mesh.renderOrder = 20;
    this.root.add(this.menu.mesh, this.lessonPanel.mesh, this.sub.mesh);
    this.gear = new THREE.Mesh(new THREE.CircleGeometry(0.016, 24), new THREE.MeshBasicMaterial({ map: gearTexture(), transparent: true, toneMapped: false }));
    this.gear.visible = false; this.root.add(this.gear);
    this.thumbs = {};
    for (const e of app.list) this.thumbs[e.id] = Object.assign(new Image(), { src: e.thumb, onload: () => this.menu.mesh.visible && this.drawMenu() });
    this.inputs = [0, 1].map((i) => this.input(i));
    this.ray = new THREE.Raycaster(); this.last = 0; this.subT = 99; this.place = { dist: 1, height: 0, yaw: 0 };
  }

  async start() {
    const session = await navigator.xr.requestSession('immersive-vr', { optionalFeatures: ['local-floor', 'hand-tracking'] });
    await this.xr.setSession(session);
    this.fitStage();
    session.addEventListener('end', () => this.end());
    this.say(this.app.ex.name);
  }
  end() {
    this.scene.remove(this.root);
    for (const s of this.inputs) { s.off(); this.scene.remove(s.ctl, s.hand); }
    const st = this.v.stage; st.position.set(0, 0, 0); st.rotation.set(0, 0, 0); st.scale.setScalar(1);
    this.v.vr = null; this.v.frame(); this.app.onExit?.();
  }

  // one controller / hand slot: target ray (trigger or pinch selects), joint nodes for a tracked hand
  input(i) {
    const ctl = this.xr.getController(i), hand = this.xr.getHand(i), s = { ctl, hand, src: null, fist: false, poke: new Map() };
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(0, 0, -1)]), new THREE.LineBasicMaterial({ color: 0x8fd3ff, transparent: true, opacity: 0.6 }));
    line.scale.z = 3; ctl.add(line);
    s.nodes = new THREE.InstancedMesh(new THREE.SphereGeometry(0.0075, 10, 8), new THREE.MeshBasicMaterial({ toneMapped: false }), JOINTS.length);
    s.nodes.frustumCulled = false; s.nodes.visible = false;
    for (let k = 0; k < JOINTS.length; k++) s.nodes.setColorAt(k, WHITE);
    // the renderer keeps these objects across sessions, so the listeners come off again in end()
    // hands and controllers can swap in either order, so a late "disconnected" must not clear the new source
    const on = { connected: (e) => (s.src = e.data), disconnected: (e) => { if (e.data === s.src) s.src = null; }, select: () => this.select(s) };
    for (const k in on) ctl.addEventListener(k, on[k]);
    s.off = () => { for (const k in on) ctl.removeEventListener(k, on[k]); ctl.remove(line); };
    this.scene.add(ctl, hand); this.root.add(s.nodes);
    return s;
  }

  // the exhibit stands in front of you: big machines on the floor at real size, small ones scaled up onto a table height
  fitStage() {
    const box = new THREE.Box3().setFromObject(this.v.model), s = box.getSize(new THREE.Vector3()).length(), k = s < 0.6 ? 0.6 / s : 1;
    this.v.stage.scale.setScalar(k);
    this.place = { dist: 0.45 + s * k * 0.45, height: s * k < 1.2 ? 0.75 - box.min.y * k : -box.min.y * k, yaw: 0 };
    this.v.rig.setExplode(0);
    this.applyPlace();
  }
  applyPlace() {
    const p = this.place;
    this.v.stage.position.set(0, p.height, -Math.max(0.3, p.dist)); this.v.stage.rotation.y = p.yaw;
  }

  // ---- per frame ----
  update(dt) {
    const head = this.xr.getCamera(), hp = head.getWorldPosition(new THREE.Vector3()), fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(head.quaternion).setY(0).normalize();
    this.head = { hp, fwd };
    const js = this.inputs.map((s) => this.joints(s));
    for (const [i, s] of this.inputs.entries()) this.drawHand(s, js[i]);
    const side = (h) => this.inputs.findIndex((s) => s.src?.handedness === h);
    const L = side('left'), R = side('right');
    // wrist gear: left hand open, palm toward your face; the right index tip pokes it
    const lj = js[L], n = lj && palmNormal(lj, 'left'), wrist = lj?.wrist;
    const show = !!(n && isOpen(lj, this.gear.visible) && wrist && new THREE.Vector3().subVectors(hp, wrist).normalize().dot(n) > 0.4);
    this.gear.visible = show;
    if (show) {
      this.gear.position.copy(wrist).addScaledVector(n, 0.025); this.gear.lookAt(this.gear.position.clone().add(n));
      const tip = js[R]?.['index-finger-tip'], touch = !!tip && tip.distanceTo(this.gear.position) < 0.025;
      if (touch && !this.gearTouch) this.once(() => this.toggleMenu(), 0.8);   // on the way in only, so a resting finger doesn't flicker it
      this.gearTouch = touch;
    } else this.gearTouch = false;
    // controllers: Y or B opens the menu; squeeze counts as a fist
    for (const s of this.inputs) {
      const b = s.src?.gamepad?.buttons;
      if (!b || s.src.hand) continue;
      if (b[5]?.pressed && !s.yb) this.toggleMenu();
      s.yb = !!b[5]?.pressed; s.fist = !!b[1]?.pressed;
    }
    // pokes on the panels
    for (const [i, s] of this.inputs.entries()) { const tip = js[i]?.['index-finger-tip']; if (tip) for (const p of [this.menu, this.lessonPanel]) this.poke(s, p, tip); }
    for (const [i, s] of this.inputs.entries()) this.dragHeld(s, js[i]);
    // two fists: explode / turn / move, one gesture per hold
    const a = this.inputs[L], b = this.inputs[R], pa = this.grabPoint(a, js[L]), pb = this.grabPoint(b, js[R]);
    if (pa && pb && a.fist && b.fist) {
      if (!this.hold) this.hold = twoHandStart(pa, pb, { explode: this.v.rig.explodeTarget, ...this.place });
      const o = twoHand(this.hold, pa, pb, { x: 0, y: 0, z: -1 });
      if (o.mode === 'spread') this.v.rig.setExplode(o.explode);
      Object.assign(this.place, { yaw: o.yaw, dist: o.dist, height: o.height }); this.applyPlace();
    } else this.hold = null;
    // subtitle: under your gaze, fades after a few seconds
    this.subT += dt;
    const op = Math.max(0, Math.min(1, 5 - this.subT));
    this.sub.mesh.visible = op > 0;
    if (op > 0) {
      this.sub.mesh.material.opacity = op;
      this.sub.mesh.position.copy(hp).addScaledVector(new THREE.Vector3(0, 0, -1).applyQuaternion(head.quaternion), 1.2).y -= 0.32;
      this.sub.mesh.quaternion.copy(head.quaternion);
    }
  }
  joints(s) {
    if (!s.src?.hand) return null;
    const j = {};
    for (const name of JOINTS) { const o = s.hand.joints?.[name]; if (!o?.visible) return null; j[name] = o.getWorldPosition(new THREE.Vector3()); }
    s.fist = isFist(j, s.fist);
    return j;
  }
  drawHand(s, j) {
    s.nodes.visible = !!j;
    s.ctl.children[0].visible = !j || !s.fist;
    if (!j) return;
    const m = new THREE.Matrix4(), pinch = isPinch(j);
    JOINTS.forEach((name, k) => {
      s.nodes.setMatrixAt(k, m.makeTranslation(j[name]));
      s.nodes.setColorAt(k, s.fist ? ORANGE : pinch && (name === 'thumb-tip' || name === 'index-finger-tip') ? BLUE : WHITE);
    });
    s.nodes.instanceMatrix.needsUpdate = true; s.nodes.instanceColor.needsUpdate = true;
  }
  grabPoint(s, j) { return s && (j ? j['middle-finger-metacarpal'] : s.src && !s.src.hand ? s.ctl.getWorldPosition(new THREE.Vector3()) : null); }
  once(fn, gap = 0.4) { const t = performance.now() / 1000; if (t - this.last > gap) { this.last = t; fn(); } }

  // index tip pushed through a panel from the front presses the button there
  poke(s, p, tip) {
    if (!p.mesh.visible) return s.poke.delete(p);
    const l = p.mesh.worldToLocal(tip.clone()), was = s.poke.get(p) ?? 1;
    s.poke.set(p, l.z);
    if (was > 0.004 && l.z <= 0.004 && Math.abs(l.x) < p.w / 2 && Math.abs(l.y) < p.h / 2) { const b = p.at(l); if (b) this.once(() => b.on()); }
  }
  aim(ctl) {
    this.ray.ray.origin.setFromMatrixPosition(ctl.matrixWorld);
    this.ray.ray.direction.set(0, 0, -1).transformDirection(ctl.matrixWorld);
    const panels = [this.menu, this.lessonPanel].filter((p) => p.mesh.visible).map((p) => p.mesh);
    return this.ray.intersectObjects(panels, false)[0];
  }
  // trigger / pinch ray: panels first, then the parts (unless that press dragged a part)
  select(s) {
    const hit = this.aim(s.ctl);
    if (hit) { const p = hit.object === this.menu.mesh ? this.menu : this.lessonPanel, b = p.at(p.mesh.worldToLocal(hit.point.clone())); return b && this.once(() => b.on(), 0.2); }
    if (!s.grab?.moved && !s.dragged) this.app.pick(this.v.hit(this.ray));
  }
  // holding the trigger / pinch on a part drags it: the grabbed point stays on the ray at the distance it was caught
  // polled each frame (trigger, or pinch for a hand) rather than selectstart/selectend, whose order differs between runtimes
  dragHeld(s, j) {
    const down = j ? isPinch(j) : !!s.src?.gamepad?.buttons[0]?.pressed;
    if (down && !s.down && !this.aim(s.ctl)) { s.grab = this.v.grabAt(this.ray); s.dragged = false; if (s.grab) s.grab.from = s.grab.at.clone(); }
    if (!down && s.grab) { s.dragged = s.grab.moved; this.v.rig.release(s.grab); s.grab = null; }
    s.down = down;
    const g = s.grab;
    if (!g) return;
    const o = new THREE.Vector3().setFromMatrixPosition(s.ctl.matrixWorld), to = new THREE.Vector3(0, 0, -1).transformDirection(s.ctl.matrixWorld).multiplyScalar(g.dist).add(o);
    this.v.rig.drag(g, g.at, to); g.at.copy(to);
    g.moved ||= to.distanceTo(g.from) > 0.02;
  }

  // ---- panels ----
  facing(mesh, ahead, below) {
    const { hp, fwd } = this.head || { hp: new THREE.Vector3(0, 1.6, 0), fwd: new THREE.Vector3(0, 0, -1) };
    mesh.position.copy(hp).addScaledVector(fwd, ahead).y -= below; mesh.lookAt(hp);
  }
  toggleMenu() {
    this.menu.mesh.visible = !this.menu.mesh.visible;
    if (this.menu.mesh.visible) { this.facing(this.menu.mesh, 0.5, 0.12); this.drawMenu(); }
  }
  drawMenu() {
    const a = this.app, B = [], W = 1024, pad = 24;
    const cols = 4, tw = (W - pad * (cols + 1)) / cols, th = 170;
    a.list.forEach((e, i) => B.push({ x: pad + (i % cols) * (tw + pad), y: pad + Math.floor(i / cols) * (th + pad), w: tw, h: th, img: this.thumbs[e.id], label: e.title, size: 28, active: a.ex.id === e.id, on: () => { this.menu.mesh.visible = false; a.open(e.id); } }));
    let y = pad + Math.ceil(a.list.length / cols) * (th + pad) + 6;
    const row = (items) => { const w = (W - pad * (items.length + 1)) / items.length; items.forEach((it, i) => B.push({ x: pad + i * (w + pad), y, w, h: 84, ...it })); y += 84 + pad; };
    const close = (fn) => () => { this.menu.mesh.visible = false; fn(); };
    row(a.ex.lessons.map((l) => ({ label: `⛓ ${l.title}`, size: 28, on: close(() => a.startLesson(l, false)) })));
    row([
      { label: '🎓 AI 家教', on: close(() => a.startTutor()) },
      { label: '❓ 先猜再看', on: close(() => a.quizLesson()) },
      { label: a.rig.explodeTarget > 0.5 ? '🧩 合起來' : '💥 拆開', on: () => { a.explode(a.rig.explodeTarget > 0.5 ? 0 : 1); this.drawMenu(); } },
      { label: '↺ 重設', on: close(() => { a.reset(); this.fitStage(); }) },
    ]);
    row([
      { label: a.recording ? '⏹ 說完了' : a.tutoring ? '🎤 回答家教' : '🎤 問 AI', color: a.recording ? C.rec : undefined, on: () => { a.talk(!a.recording); setTimeout(() => this.menu.mesh.visible && this.drawMenu(), 50); } },
      { label: '✕ 關選單', on: () => (this.menu.mesh.visible = false) },
      { label: '🚪 離開 VR', on: () => this.xr.getSession()?.end() },
    ]);
    const H = y + 2, canvas = this.menu.canvas;
    if (canvas.height !== H) { canvas.height = H; this.menu.h = (this.menu.w * H) / W; this.menu.mesh.geometry.dispose(); this.menu.mesh.geometry = new THREE.PlaneGeometry(this.menu.w, this.menu.h); }
    this.menu.draw(B);
  }
  // lesson bar (◀ step ▶ ✕) and quiz answers, near your hands while a lesson runs
  refresh() {
    const a = this.app, p = this.lessonPanel, L = a.lesson;
    if (!L) { p.mesh.visible = false; return; }
    const W = 1024, pad = 20, opts = a.quiz || [], H = 120 + opts.length * 100, B = [];
    B.push({ x: pad, y: pad, w: 140, h: 80, label: '◀', on: () => a.go(-1) }, { x: W - 2 * (140 + pad), y: pad, w: 140, h: 80, label: '▶', on: () => a.go(1) },
      { x: W - 140 - pad, y: pad, w: 140, h: 80, label: '✕', on: () => a.stopLesson() },
      { x: 180, y: pad, w: W - 180 - 2 * (140 + pad) - pad, h: 80, label: `${L.i + 1} / ${L.l.steps.length}`, color: C.bg, on: null });
    opts.forEach(([text], i) => B.push({ x: pad, y: 120 + i * 100, w: W - 2 * pad, h: 84, label: text, size: 32, on: () => a.answer(i) }));
    if (p.canvas.height !== H) { p.canvas.height = H; p.h = (p.w * H) / W; p.mesh.geometry.dispose(); p.mesh.geometry = new THREE.PlaneGeometry(p.w, p.h); }
    p.draw(B);
    if (!p.mesh.visible) { p.mesh.visible = true; this.facing(p.mesh, 0.45, 0.2); }
  }
  say(text) {
    const g = this.sub.canvas.getContext('2d'), { width: W, height: H } = this.sub.canvas;
    g.clearRect(0, 0, W, H); g.fillStyle = 'rgba(10,14,20,0.78)'; g.beginPath(); g.roundRect(0, 0, W, H, H / 2); g.fill();
    g.fillStyle = C.text; g.font = `56px ${FONT}`; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(fit(g, (text || '').match(/^[^。！？\n]*[。！？]?/)[0], W - 80), W / 2, H / 2);   // the first sentence on one line; the voice says the rest
    this.sub.tex.needsUpdate = true; this.subT = text ? 0 : 99;
  }
}

function gearTexture() {
  const c = Object.assign(document.createElement('canvas'), { width: 128, height: 128 }), g = c.getContext('2d');
  g.fillStyle = 'rgba(20,27,36,0.85)'; g.beginPath(); g.arc(64, 64, 62, 0, Math.PI * 2); g.fill();
  g.fillStyle = C.on; g.font = `84px ${FONT}`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('⚙', 64, 70);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
