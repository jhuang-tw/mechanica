# Shared Blender side of every exhibit build: per-part bmesh builder, node export (origin = pivot, extras axis/explode),
# studio preview renders, thumbnail and GLB export. An exhibit's build.py defines MATS, VIEWS and build(), then calls run().
import bpy, bmesh, sys, os, json
from math import sin, cos, atan2, pi, radians
from mathutils import Vector as V, Matrix

TAU = 2 * pi
Y = V((0, 1, 0))
MATS = {}           # filled by the exhibit: name -> (base colour linear, metallic, roughness)
CAD_DIR = ['']      # the exhibit's cad/out folder (STLs in mm)

def material(name):
    if name in bpy.data.materials: return bpy.data.materials[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; c, met, rough = MATS[name]
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Metallic'].default_value = met; b.inputs['Roughness'].default_value = rough
    return m

# ---------------------------------------------------------------- mesh builder: one bmesh per part, faces tagged by material
class Mesh:
    def __init__(self): self.bm, self.mats = bmesh.new(), []
    def mi(self, mat):
        if mat not in self.mats: self.mats.append(mat)
        return self.mats.index(mat)
    def face(self, vs, mat):
        f = self.bm.faces.new(vs); f.material_index = self.mi(mat); f.smooth = True; return f

    def stl(self, name, mat, M):
        """Append a CAD STL, transformed by the 4x4 M (mm -> bike metres), all faces in one material."""
        bpy.ops.wm.stl_import(filepath=os.path.join(CAD_DIR[0], name + '.stl'))
        ob = bpy.context.selected_objects[0]; me = ob.data; me.transform(M)
        n = len(self.bm.faces); self.bm.from_mesh(me); self.bm.faces.ensure_lookup_table()
        for f in self.bm.faces[n:]: f.material_index = self.mi(mat); f.smooth = True
        bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)

    def ring(self, c, axis, r, seg, ref=None):
        axis = axis.normalized(); ref = ref or (Y if abs(axis.dot(Y)) < 0.9 else V((1, 0, 0)))
        a = axis.cross(ref).normalized(); b = axis.cross(a)
        return [self.bm.verts.new(c + (a * cos(t) + b * sin(t)) * r) for t in (TAU * i / seg for i in range(seg))]

    def bridge(self, r0, r1, mat):
        n = len(r0)
        for i in range(n): self.face([r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]], mat)

    def cap(self, r, mat, flip=False): self.face(r[::-1] if flip else r, mat)

    def sweep(self, pts, rad, mat, seg=10, caps=True):
        """Tube along a polyline; rad = number or per-point list."""
        rad = rad if isinstance(rad, list) else [rad] * len(pts)
        rings, d0 = [], None
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            ref = (Y if abs(t.dot(Y)) < 0.9 else V((1, 0, 0))) if d0 is None else d0.cross(t)   # keeps vertex 0 on the same side: no twist
            rings.append(self.ring(p, t, rad[i], seg, ref)); d0 = (rings[-1][0].co - p).normalized()
        for a, b in zip(rings, rings[1:]): self.bridge(a, b, mat)
        if caps: self.cap(rings[0], mat, True); self.cap(rings[-1], mat)

    def tube(self, a, b, r, mat, seg=10, caps=True): self.sweep([a, b], r, mat, seg, caps)

    def disc(self, c, axis, r, t, mat, seg=32, r_in=0):
        """Cylinder (or washer) of thickness t along axis."""
        ax = axis.normalized()
        o0, o1 = self.ring(c - ax * t / 2, ax, r, seg), self.ring(c + ax * t / 2, ax, r, seg)
        self.bridge(o0, o1, mat)
        if r_in:
            i0, i1 = self.ring(c - ax * t / 2, ax, r_in, seg), self.ring(c + ax * t / 2, ax, r_in, seg)
            self.bridge(i1, i0, mat); self.bridge(i0, o0, mat); self.bridge(o1, i1, mat)
        else: self.cap(o0, mat, True); self.cap(o1, mat)

    def torus(self, c, axis, R, r, mat, seg=64, sides=10, squash=1.0):
        ax = axis.normalized(); a = ax.cross(V((0, 0, 1)) if abs(ax.z) < 0.9 else V((1, 0, 0))).normalized(); b = ax.cross(a)
        rings = []
        for i in range(seg):
            t = TAU * i / seg; rd = a * cos(t) + b * sin(t)
            rings.append([self.bm.verts.new(c + rd * (R + r * cos(s)) + ax * r * squash * sin(s)) for s in (TAU * j / sides for j in range(sides))])
        for i in range(seg): self.bridge(rings[i], rings[(i + 1) % seg], mat)

    def box(self, c, size, mat, rot=Matrix.Identity(3)):
        sx, sy, sz = (s / 2 for s in size)
        vs = [self.bm.verts.new(c + rot @ V((x, y, z))) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)): self.face([vs[i] for i in f], mat)

PARTS = {}   # id -> dict(m=Mesh, pivot, parent, axis, explode)

def part(pid, pivot=None, parent=None, axis=None, explode=(0, 0, 0)):
    PARTS[pid] = dict(m=Mesh(), pivot=V(pivot) if pivot is not None else None, parent=parent, axis=axis, explode=V(explode))
    return PARTS[pid]['m']

def g(v): return [round(v.x, 5), round(v.z, 5), round(-v.y, 5)]   # Blender -> glTF axes

def make_objects():
    obs = {}
    for pid, p in PARTS.items():
        me = bpy.data.meshes.new(pid); p['m'].bm.to_mesh(me); p['m'].bm.free()
        for mat in p['m'].mats: me.materials.append(material(mat))
        piv = p['pivot'] or V((0, 0, 0))
        me.transform(Matrix.Translation(-piv))
        me.set_sharp_from_angle(angle=radians(40))
        ob = bpy.data.objects.new(pid, me); bpy.context.scene.collection.objects.link(ob)
        ob.location = piv; obs[pid] = ob
        if p['axis'] is not None: ob['axis'] = g(V(p['axis']).normalized())
        ob['explode'] = g(p['explode'])
    for pid, p in PARTS.items():
        if p['parent']:
            ob, par, pp = obs[pid], obs[p['parent']], PARTS[p['parent']]['pivot'] or V((0, 0, 0))
            ob.parent = par; ob.location = (p['pivot'] or V((0, 0, 0))) - pp   # no rotations anywhere: world pivots subtract (chains too)
    return obs

def lights_camera(res, engine):
    sc = bpy.context.scene; sc.render.engine = engine; sc.render.resolution_x, sc.render.resolution_y = res
    if engine == 'CYCLES':
        sc.cycles.samples = 48; sc.cycles.use_denoising = True
        try:   # Jim's PC: AMD GPU through HIP
            prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'HIP'; prefs.get_devices()
            hip = [d for d in prefs.devices if d.type == 'HIP']
            best = [d for d in hip if 'RX' in d.name] or hip                 # the discrete card only: no CPU, no iGPU
            for d in prefs.devices: d.use = d in best
            assert best, 'no HIP device'
            print('Cycles on', [d.name for d in best])
            sc.cycles.device = 'GPU'
        except Exception as e: print('GPU unavailable, CPU render:', e)
    if not sc.camera:
        w = bpy.data.worlds.new('w'); w.use_nodes = True; bg = w.node_tree.nodes['Background']   # light grey studio
        bg.inputs[0].default_value = (0.82, 0.84, 0.88, 1); bg.inputs[1].default_value = 0.9; sc.world = w
        sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3.5
        sun.rotation_euler = (radians(40), radians(15), radians(-30)); sc.collection.objects.link(sun)
        cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.lens = 50; sc.collection.objects.link(cam); sc.camera = cam
    return sc

def shoot(path, loc, target, lens=50):
    sc = bpy.context.scene; cam = sc.camera; cam.data.lens = lens; cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

def preview(folder, views):
    os.makedirs(folder, exist_ok=True); sc = lights_camera((640, 480), 'CYCLES'); sc.cycles.samples = 24
    sc.render.image_settings.file_format = 'PNG'
    for name, (loc, target, lens) in views.items(): shoot(os.path.join(folder, name + '.png'), loc, target, lens)

def thumbnail(path, view):
    sc = lights_camera((512, 512), 'CYCLES'); sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 85
    shoot(path, *view)

def run(script, build, views, thumb_view):
    """`blender -b --factory-startup -t 4 -P <exhibit>/build.py -- public/exhibits/<id> [--preview] [--no-thumb]`.
    The raw GLB goes next to the script (tools/optimize-glb.mjs makes OUT/model.glb from it). When OUT has a manifest,
    its part ids must equal the built nodes."""
    here = os.path.dirname(os.path.abspath(script)); name = os.path.basename(here)
    out = os.path.abspath(sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else f'public/exhibits/{name}')
    CAD_DIR[0] = os.path.join(here, 'cad', 'out')
    for ob in list(bpy.data.objects): bpy.data.objects.remove(ob)
    build()
    mf = os.path.join(out, 'manifest.json')
    if os.path.exists(mf):
        with open(mf, encoding='utf-8') as f: ids = {p['id'] for p in json.load(f)['parts']}
        assert ids == set(PARTS), f'manifest vs model: missing {ids - set(PARTS)}, extra {set(PARTS) - ids}'
    make_objects()
    if '--preview' in sys.argv:   # look first, export later; `--hide a,b` leaves those parts out of the shots
        hide = sys.argv[sys.argv.index('--hide') + 1].split(',') if '--hide' in sys.argv else []
        for pid in hide: bpy.data.objects[pid].hide_render = True
        if '--explode' in sys.argv:
            for pid, p in PARTS.items(): bpy.data.objects[pid].location += p['explode']
        preview(os.path.join(here, 'preview'), views); return
    os.makedirs(out, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(here, 'model.raw.glb'), export_format='GLB', export_extras=True, export_yup=True,
                              export_apply=False, export_cameras=False, export_lights=False, export_materials='EXPORT')
    if '--no-thumb' not in sys.argv: thumbnail(os.path.join(out, 'thumb.jpg'), thumb_view)
    tris = sum(len(ob.data.polygons) for ob in bpy.data.objects if ob.type == 'MESH')
    print(f'{name}: {len(PARTS)} parts, {tris} faces ->', out)
