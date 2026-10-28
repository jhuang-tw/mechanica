// Studio look: a softbox environment for reflections, a gradient backdrop, key/fill/rim lights and a soft-shadowed floor
// that fades into the backdrop. Sized to each model; manifest `look` = {exposure, env, key} tunes it per exhibit.
import * as THREE from 'three';

const SKY = new THREE.Color(0x3c4655), HORIZON = new THREE.Color(0x232a34), GROUND = new THREE.Color(0x12161c);

// vertical gradient on a sphere (y = 1 top, -1 bottom); used for the reflection room and the visible backdrop
function dome(r, top, mid, bottom) {
  const g = new THREE.SphereGeometry(r, 48, 24), p = g.attributes.position, c = [], col = new THREE.Color();
  for (let i = 0; i < p.count; i++) {
    const y = p.getY(i) / r;
    col.lerpColors(mid, y > 0 ? top : bottom, Math.min(1, Math.abs(y) * (y > 0 ? 1.4 : 3)));
    c.push(col.r, col.g, col.b);
  }
  g.setAttribute('color', new THREE.Float32BufferAttribute(c, 3));
  return new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, depthWrite: false, fog: false }));
}

// the room the model reflects: dim walls, a big overhead softbox, a strip light each side and a warm bounce card low in front
function envScene() {
  const s = new THREE.Scene();
  s.add(dome(10, new THREE.Color(0.55, 0.57, 0.62), new THREE.Color(0.24, 0.25, 0.28), new THREE.Color(0.07, 0.07, 0.08)));
  const box = (w, h, i, pos, tint = 0xffffff) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(tint).multiplyScalar(i), side: THREE.DoubleSide }));
    m.position.set(...pos); m.lookAt(0, 0, 0); s.add(m);
  };
  box(6, 4, 6, [1, 7, 2]);                     // overhead key softbox
  box(1.2, 7, 4, [7, 1.5, -2]);                // right strip (long highlight down car flanks, tubes)
  box(1.2, 7, 2.5, [-7, 1.5, 1]);              // left strip, weaker
  box(5, 1.5, 1.2, [0, -1, 7], 0xffe2c4);      // warm bounce card in front, low
  box(4, 3, 3, [-2, 4, -7]);                   // back softbox: rim reflections
  return s;
}

// bare metal: a faint roughness grain in object space, so a reflection breaks up a little instead of looking like plastic
const NOISE = `varying vec3 vGrain;
float gh(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
float grainNoise(vec3 p) {
  vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(gh(i), gh(i + vec3(1, 0, 0)), f.x), mix(gh(i + vec3(0, 1, 0)), gh(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(gh(i + vec3(0, 0, 1)), gh(i + vec3(1, 0, 1)), f.x), mix(gh(i + vec3(0, 1, 1)), gh(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}`;
// every exhibit material: a highlight that keeps the real material (a warm rim glow, `m.userData.rim.value` 0..1, set by
// the rig) and, on bare metal, the grain above
function dress(m, grain) {
  const rim = m.userData.rim = { value: 0 };
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uRim = rim;
    let f = sh.fragmentShader.replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
float rimK = 1.0 - abs(dot(normal, normalize(vViewPosition)));
totalEmissiveRadiance += uRim * vec3(1.0, 0.62, 0.15) * (1.3 * rimK * rimK * rimK * rimK);`);
    f = `uniform float uRim;\n${f}`;
    if (grain) {
      sh.uniforms.uGrain = grain;
      sh.vertexShader = `uniform float uGrain;\nvarying vec3 vGrain;\n${sh.vertexShader}`.replace('#include <begin_vertex>', '#include <begin_vertex>\nvGrain = position * uGrain;');
      f = `${NOISE}\n${f}`.replace('#include <roughnessmap_fragment>',
        '#include <roughnessmap_fragment>\nroughnessFactor = clamp(roughnessFactor * (0.88 + 0.24 * (0.65 * grainNoise(vGrain) + 0.35 * grainNoise(vGrain * 3.7))), 0.04, 1.0);');
    }
    sh.fragmentShader = f;
  };
  m.customProgramCacheKey = () => (grain ? 'look-grain' : 'look');
  m.needsUpdate = true;
}

export class Studio {
  constructor(renderer, scene, stage, mobile) {
    this.stage = stage;
    this.renderer = renderer;
    renderer.toneMapping = THREE.NeutralToneMapping;   // keeps paint colours true, unlike ACES' hue shifts
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    const pm = new THREE.PMREMGenerator(renderer);
    scene.environment = pm.fromScene(envScene(), 0.02).texture; pm.dispose();
    scene.background = HORIZON;
    this.backdrop = dome(60, SKY, HORIZON, GROUND); this.backdrop.renderOrder = -1;
    // floor: soft shadow catcher fading to transparent at its rim, so there is no visible disc edge
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const x = c.getContext('2d'), gr = x.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, '#fff'); gr.addColorStop(0.45, '#fff'); gr.addColorStop(1, '#000');
    x.fillStyle = gr; x.fillRect(0, 0, 128, 128);
    this.floor = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
      new THREE.MeshStandardMaterial({ color: 0x2b333e, roughness: 0.8, metalness: 0, transparent: true, alphaMap: new THREE.CanvasTexture(c), depthWrite: false }));
    this.floor.receiveShadow = true; this.floor.renderOrder = -1;
    // contact shadow: a soft dark blob right under the model's footprint (the key's shadow falls off to one side)
    const b = document.createElement('canvas'); b.width = b.height = 64;
    const bx = b.getContext('2d'), bg = bx.createRadialGradient(32, 32, 0, 32, 32, 32);
    bg.addColorStop(0, 'rgba(0,0,0,0.75)'); bg.addColorStop(0.6, 'rgba(0,0,0,0.35)'); bg.addColorStop(1, 'rgba(0,0,0,0)');
    bx.fillStyle = bg; bx.fillRect(0, 0, 64, 64);
    this.blob = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(b), transparent: true, depthWrite: false }));
    this.blob.renderOrder = -1;
    this.key = new THREE.DirectionalLight(0xfff4e8, 2.2);
    this.key.castShadow = true;
    const sm = this.key.shadow; sm.mapSize.setScalar(mobile ? 1024 : 2048); sm.radius = 4; sm.bias = -0.0004; sm.normalBias = 0.01;
    this.fill = new THREE.DirectionalLight(0xc8d8ff, 0.35);
    this.rim = new THREE.DirectionalLight(0xffffff, 1.4);
    scene.add(this.backdrop);
    stage.add(this.floor, this.blob, this.key, this.key.target, this.fill, this.rim, this.fill.target, this.rim.target);   // VR moves and scales the stage: floor and shadows go along
  }

  // place lights, shadow frustum and floor around the model; `look` from the manifest
  fit(model, look = {}) {
    model.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    const box = new THREE.Box3().setFromObject(model).applyMatrix4(this.stage.matrixWorld.clone().invert()), c = box.getCenter(new THREE.Vector3()), r = box.getSize(new THREE.Vector3()).length() / 2;
    const at = (l, x, y, z) => { l.position.set(c.x + x * r, box.min.y + y * r, c.z + z * r); l.target.position.copy(c); };
    at(this.key, 0.9, 2.2, 1.4); at(this.fill, -1.6, 0.6, 1.0); at(this.rim, -0.6, 1.4, -2.0);
    this.r = r; this.k = 0;
    this.key.shadow.radius = 3 + 3 * Math.min(1, r);   // a pocket watch gets a crisper shadow than a car
    this.floor.position.set(c.x, box.min.y - r * 0.002, c.z); this.floor.scale.setScalar(r * 5);
    const sz = box.getSize(new THREE.Vector3());
    this.blob.position.set(c.x, box.min.y - r * 0.001, c.z); this.blob.scale.set(sz.x * 1.25, 1, sz.z * 1.25);
    this.renderer.toneMappingExposure = look.exposure ?? 1;
    const env = look.env ?? 1;
    const ns = { value: 1 / (r * 0.006) };
    model.traverse((o) => {
      if (o.isMesh) for (const m of [].concat(o.material)) { m.envMapIntensity = env; dress(m, m.metalness > 0.5 && !m.roughnessMap && ns); }
    });
    this.key.intensity = 2.2 * (look.key ?? 1); this.rim.intensity = 1.4 * (look.key ?? 1);
  }

  // the shadow frustum is in world units: follow the stage scale (VR shows a watch scaled up)
  update() {
    const k = this.stage.getWorldScale(new THREE.Vector3()).x;
    if (k === this.k) return;
    const cam = this.key.shadow.camera, d = this.r * 1.15 * (this.k = k);
    Object.assign(cam, { left: -d, right: d, top: d, bottom: -d, near: this.r * 0.5 * k, far: this.r * 6 * k }); cam.updateProjectionMatrix();
  }
}
