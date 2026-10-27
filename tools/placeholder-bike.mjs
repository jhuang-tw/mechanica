// Placeholder bicycle made of primitives, so the whole app runs before the real model exists.
// Node names and pivots follow the manifest contract (docs/interfaces.md): one node per part id, origin at its rotation centre.
// `npm run model:placeholder` writes public/exhibits/bike/model.glb (the real Blender model replaces that file).
import { writeFileSync } from 'node:fs';
import * as THREE from 'three';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';

globalThis.FileReader ??= class { readAsArrayBuffer(b) { b.arrayBuffer().then((r) => { this.result = r; this.onloadend?.(); }); } };

const V = (x, y, z = 0) => new THREE.Vector3(x, y, z);
const mat = (color, metalness = 0.1, roughness = 0.5) => new THREE.MeshStandardMaterial({ color, metalness, roughness });
const RED = mat(0xc8322b, 0.3, 0.35), BLACK = mat(0x1b1b1b, 0, 0.8), STEEL = mat(0xb8bcc2, 0.9, 0.3), DARK = mat(0x3a3d42, 0.7, 0.4);

function tube(a, b, r, m) {   // cylinder from a to b
  const d = b.clone().sub(a), g = new THREE.CylinderGeometry(r, r, d.length(), 16);
  const mesh = new THREE.Mesh(g, m);
  mesh.position.copy(a).addScaledVector(d, 0.5);
  mesh.quaternion.setFromUnitVectors(V(0, 1), d.normalize());
  return mesh;
}
function part(id, origin, ...children) {   // node `id` at `origin`; children given in world coordinates
  const g = new THREE.Group();
  g.name = id; g.position.copy(origin);
  for (const c of children) { c.position.sub(origin); g.add(c); }
  return g;
}
const at = (mesh, p) => { mesh.position.copy(p); return mesh; };
const disc = (r, w, m, at) => { const c = new THREE.Mesh(new THREE.CylinderGeometry(r, r, w, 48).rotateX(Math.PI / 2), m); c.position.copy(at); return c; };
function wheel(id, at) {
  const tire = new THREE.Mesh(new THREE.TorusGeometry(0.322, 0.014, 12, 64), BLACK); tire.position.copy(at);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(0.305, 0.01, 8, 64), STEEL); rim.position.copy(at);
  const spokes = Array.from({ length: 12 }, (_, i) => { const a = (i / 12) * Math.PI * 2; return tube(at, at.clone().add(V(Math.cos(a) * 0.3, Math.sin(a) * 0.3)), 0.002, STEEL); });
  return part(id, at, tire, rim, disc(0.025, 0.1, DARK, at), ...spokes);
}

// side view: +x forward, +y up, z = sideways (drive side +z)
const R = V(-0.41, 0.336), F = V(0.58, 0.336), BB = V(0, 0.27), SEAT = V(-0.13, 0.78), HEAD_T = V(0.47, 0.78), HEAD_B = V(0.52, 0.62);
const root = new THREE.Group(); root.name = 'bike';
root.add(
  part('frame', V(0, 0), tube(BB, SEAT, 0.017, RED), tube(SEAT, HEAD_T, 0.016, RED), tube(BB, HEAD_B, 0.02, RED), tube(HEAD_B, HEAD_T, 0.022, RED),
    tube(R.clone().setZ(0.05), SEAT, 0.009, RED), tube(R.clone().setZ(-0.05), SEAT, 0.009, RED), tube(R.clone().setZ(0.05), BB, 0.011, RED), tube(R.clone().setZ(-0.05), BB, 0.011, RED)),
  part('fork', HEAD_B, tube(HEAD_B, F.clone().setZ(0.05), 0.012, DARK), tube(HEAD_B, F.clone().setZ(-0.05), 0.012, DARK)),
  part('stem', HEAD_T, tube(HEAD_T, V(0.57, 0.83), 0.014, DARK)),
  part('handlebar', V(0.57, 0.83), tube(V(0.57, 0.83, -0.21), V(0.57, 0.83, 0.21), 0.012, BLACK),
    tube(V(0.57, 0.83, 0.21), V(0.64, 0.74, 0.21), 0.012, BLACK), tube(V(0.57, 0.83, -0.21), V(0.64, 0.74, -0.21), 0.012, BLACK)),
  part('seatpost', SEAT, tube(SEAT, V(-0.17, 0.92), 0.013, DARK)),
  part('saddle', V(-0.17, 0.93), at(new THREE.Mesh(new THREE.BoxGeometry(0.27, 0.04, 0.12), BLACK), V(-0.17, 0.94))),
  wheel('front_wheel', F), wheel('rear_wheel', R),
  part('chainring', BB.clone().setZ(0.07), disc(0.1, 0.006, STEEL, BB.clone().setZ(0.07))),
  part('cassette', R.clone().setZ(0.07), ...[0.055, 0.045, 0.035].map((r, i) => disc(r, 0.004, STEEL, R.clone().setZ(0.06 + i * 0.006)))),
  part('chain', BB, tube(V(0, 0.37, 0.07), V(-0.41, 0.381, 0.07), 0.004, DARK), tube(V(0, 0.17, 0.07), V(-0.41, 0.291, 0.07), 0.004, DARK)),
  part('rear_derailleur', V(-0.41, 0.25, 0.08), at(new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.09, 0.02), DARK), V(-0.41, 0.25, 0.08))),
  part('front_derailleur', V(-0.03, 0.4, 0.07), at(new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.02, 0.02), DARK), V(-0.03, 0.4, 0.07))),
  part('brake_front', V(0.53, 0.66), at(new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.05, 0.1), DARK), V(0.53, 0.66))),
  part('brake_rear', V(-0.3, 0.65), at(new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.05, 0.1), DARK), V(-0.3, 0.65))),
);
// crank with both pedals as its children: they ride around with it
const crank = part('crank', BB, tube(BB.clone().setZ(0.085), V(0, 0.27 - 0.17, 0.085), 0.01, STEEL), tube(BB.clone().setZ(-0.085), V(0, 0.27 + 0.17, -0.085), 0.01, STEEL), tube(BB.clone().setZ(-0.09), BB.clone().setZ(0.09), 0.012, STEEL));
const pedal = (id, y, z) => { const p = part(id, V(0, y, z), at(new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.015, 0.06), BLACK), V(0, y, z))); p.position.sub(BB); return p; };
crank.add(pedal('pedal_r', 0.1, 0.12), pedal('pedal_l', 0.44, -0.12));
root.add(crank);

new GLTFExporter().parse(root, (glb) => {
  writeFileSync(new URL('../public/exhibits/bike/model.glb', import.meta.url), Buffer.from(glb));
  console.log(`placeholder bike: ${(glb.byteLength / 1024).toFixed(0)} kB`);
}, (e) => { throw e; }, { binary: true });
