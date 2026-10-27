// Phone pass for an exhibit GLB: weld, error-bounded simplify, quantize normals, meshopt-compress (src/viewer.js decodes it).
// POSITION is never quantized: that would add a scale to every node and move the part pivots the manifest relies on.
// usage: node tools/optimize-glb.mjs <in.glb> <out.glb> [simplify error, default 0.0005; < 0 skips simplify]
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions';
import { dedup, weld, simplify, prune, reorder, quantize } from '@gltf-transform/functions';
import { MeshoptSimplifier, MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';

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
  ...(+err < 0 ? [] : [simplify({ simplifier: MeshoptSimplifier, error: +err, lockBorder: true })]),
  prune({ keepLeaves: true, keepExtras: true }),
  reorder({ encoder: MeshoptEncoder, target: 'size' }),
  quantize({ pattern: /^(NORMAL|TEXCOORD_\d+|COLOR_\d+)$/, quantizeNormal: 8, quantizeTexcoord: 12, quantizeColor: 8 }),
);
if (names() !== n0) throw new Error('optimize changed the node set; part ids would break');
doc.createExtension(EXTMeshoptCompression).setRequired(true).setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.FILTER });
await io.write(out, doc);
console.log(`${inp}: ${Math.round(t0)} -> ${Math.round(tris())} tris`);
