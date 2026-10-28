// Undo the phone pass of an exhibit GLB (meshopt + quantization) so Blender's glTF importer, which has no meshopt decoder
// in the bpy wheel, can read it: e.g. to reuse a published Tripo shell where the Tripo source is not at hand.
// usage: node tools/decode-glb.mjs <in.glb> <out.glb>
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dequantize } from '@gltf-transform/functions';
import { MeshoptDecoder } from 'meshoptimizer';

const [inp, out] = process.argv.slice(2);
if (!inp || !out) { console.error('usage: decode-glb.mjs <in.glb> <out.glb>'); process.exit(1); }
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(inp);
await doc.transform(dequantize());
for (const e of doc.getRoot().listExtensionsUsed()) if (/meshopt|quantization/i.test(e.extensionName)) e.dispose();
await io.write(out, doc);
console.log(`${inp} -> ${out}`);
