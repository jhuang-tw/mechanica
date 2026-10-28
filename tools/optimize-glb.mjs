// Phone pass for an exhibit GLB: weld, error-bounded simplify, quantize normals, meshopt-compress (src/viewer.js decodes it).
// POSITION is never quantized: that would add a scale to every node and move the part pivots the manifest relies on.
// usage: node tools/optimize-glb.mjs <in.glb> <out.glb> [simplify error, default 0.0005; < 0 skips simplify]
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions';
import { dedup, weld, simplify, prune, reorder, quantize } from '@gltf-transform/functions';
import { MeshoptSimplifier, MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';

// Simplify moves and merges vertices but keeps their old normals, which crumples flat castings and gear faces:
// recompute each vertex normal from the simplified triangles around it (area-weighted). Vertices split at hard edges
// stay split, so creases stay sharp.
const renormal = () => (doc) => {
  for (const mesh of doc.getRoot().listMeshes()) for (const prim of mesh.listPrimitives()) {
    const pos = prim.getAttribute('POSITION'), nor = prim.getAttribute('NORMAL'), idx = prim.getIndices();
    if (!pos || !nor || !idx) continue;
    const P = pos.getArray(), I = idx.getArray(), N = new Float32Array(pos.getCount() * 3), O = new Float32Array(N.length), e = [0, 0, 0];
    for (let v = 0; v < pos.getCount(); v++) O.set(nor.getElement(v, e), v * 3);   // as floats: a spliced-in node may be quantized
    for (let t = 0; t < I.length; t += 3) {
      const a = I[t] * 3, b = I[t + 1] * 3, c = I[t + 2] * 3;
      const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2], vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      for (const k of [a, b, c]) {   // facing taken from the old normal: scan shells (Tripo) wind their triangles either way
        const s = nx * O[k] + ny * O[k + 1] + nz * O[k + 2] < 0 ? -1 : 1;
        N[k] += s * nx; N[k + 1] += s * ny; N[k + 2] += s * nz;
      }
    }
    for (let k = 0; k < N.length; k += 3) {
      const l = Math.hypot(N[k], N[k + 1], N[k + 2]);
      if (l > 0) { O[k] = N[k] / l; O[k + 1] = N[k + 1] / l; O[k + 2] = N[k + 2] / l; }
    }
    nor.setNormalized(false).setArray(O);
  }
};

const [inp, out, err = '0.0005'] = process.argv.slice(2);
if (!inp || !out) { console.error('usage: optimize-glb.mjs <in.glb> <out.glb> [error]'); process.exit(1); }
await Promise.all([MeshoptSimplifier.ready, MeshoptEncoder.ready, MeshoptDecoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder });
const doc = await io.read(inp);
const tris = () => doc.getRoot().listMeshes().flatMap((m) => m.listPrimitives()).reduce((s, p) => s + (p.getIndices()?.getCount() ?? 0) / 3, 0);
const names = () => doc.getRoot().listNodes().map((n) => n.getName()).sort().join();
const t0 = tris(), n0 = names();
await doc.transform(
  dedup(),
  weld(),
  ...(+err < 0 ? [] : [simplify({ simplifier: MeshoptSimplifier, error: +err, lockBorder: true }), renormal()]),
  prune({ keepLeaves: true, keepExtras: true }),
  reorder({ encoder: MeshoptEncoder, target: 'size' }),
  quantize({ pattern: /^(NORMAL|TEXCOORD_\d+|COLOR_\d+)$/, quantizeNormal: 8, quantizeTexcoord: 12, quantizeColor: 8 }),
);
if (names() !== n0) throw new Error('optimize changed the node set; part ids would break');
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.FILTER });
await io.write(out, doc);
console.log(`${inp}: ${Math.round(t0)} -> ${Math.round(tris())} tris`);
