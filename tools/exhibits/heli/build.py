# Helicopter exhibit (generic light single-turbine, two-blade teetering rotor), built from scratch for Mechanica.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/heli/build.py -- public/exhibits/heli [--preview]
# Run tools/exhibits/heli/cad.py first (gearbox gears, swashplate, rotor hub and tail gears come from its STLs).
# Model frame (Blender): metres, skids on z = 0, nose = +x, left = +y. glTF: nose +x, up +y, right = +z.
# Main rotor turns counter-clockwise seen from above: mast, hub, blades, upper swashplate and pitch links spin about glTF +y.
# The rotating parts hang on the mast; blades hang on the hub and feather about their own span axis (extras.axis).
# The outer shell is a Tripo3D mesh (tools/exhibits/heli/tripo/body.glb, kept out of git): stretched onto the CAD hub and tail rotor,
# its rotors and skids cut away, decimated and split along its own pieces and panel lines into fuselage, canopy, four doors,
# transmission and engine cowlings, tail boom and tail fins.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths
import common

S = Matrix.Scale(0.001, 4)
Z = V((0, 0, 1)); X = V((1, 0, 0))
TO_X = Matrix.Rotation(pi / 2, 4, 'Y') @ S     # CAD z -> Blender +x
TO_Y = Matrix.Rotation(-pi / 2, 4, 'X') @ S    # CAD z -> Blender +y
def at(p, M=S, rz=0): return Matrix.Translation(p) @ M @ Matrix.Rotation(rz, 4, 'Z')

# ---------------------------------------------------------------- layout (metres)
BEVEL_Z = 1.95                       # output bevel tooth face
PLAN_Z = 2.15                        # planetary stage
SWASH_Z = 2.55
HUB_Z = 2.95
R_BLADE, CHORD = 5.35, 0.30
ENGINE = V((-0.95, 0, 2.05))         # turboshaft centre, axis x
TAIL_GB = V((-6.30, 0, 2.20))
TAIL_ROTOR = V((-6.36, -0.24, 2.30))
CTRL = V((1.50, 0, 0.19))          # pilot controls moved forward onto the Tripo cockpit floor, in front of the right-hand seat

common.MATS.update({   # base colour (linear), metallic, roughness
    'alu':    ((0.62, 0.63, 0.65), 1.0, 0.35),
    'steel':  ((0.50, 0.51, 0.53), 1.0, 0.28),
    'dark':   ((0.06, 0.06, 0.07), 0.8, 0.45),
    'black':  ((0.015, 0.015, 0.017), 0.0, 0.55),
    'blade':  ((0.20, 0.21, 0.23), 0.1, 0.45),
    'tip':    ((0.60, 0.42, 0.04), 0.1, 0.40),     # yellow tip stripe so the blades read while spinning
    'brass':  ((0.60, 0.42, 0.15), 1.0, 0.35),
    'hot':    ((0.30, 0.18, 0.10), 1.0, 0.45),
    'red':    ((0.50, 0.04, 0.03), 0.2, 0.40),
})

def airfoil(chord, t=0.12, n=10):
    """NACA 00xx half-cosine sampled, leading edge at 0, chord along +u; returns (u, v) loop."""
    up = []
    for i in range(n + 1):
        u = (1 - cos(pi * i / n)) / 2
        v = 5 * t * (0.2969 * u ** 0.5 - 0.126 * u - 0.3516 * u ** 2 + 0.2843 * u ** 3 - 0.1036 * u ** 4)
        up.append((u * chord, v * chord))
    return up + [(u, -v) for u, v in up[-2:0:-1]]

def blade(m, root, span_dir, lead_dir, r0, r1, chord, mat, twist=8.0, tip_mat=None):
    """Lofted blade from r0 to r1 along span_dir; quarter chord on the span axis; washout `twist` degrees."""
    up = span_dir.cross(lead_dir).normalized()
    secs = [0, 0.15, 0.5, 0.85, 0.92, 1.0]
    rings = []
    for f in secs:
        r = r0 + (r1 - r0) * f; tw = radians(twist * (0.5 - f))
        ld = lead_dir * cos(tw) + up * sin(tw); nu = up * cos(tw) - lead_dir * sin(tw)
        c = root + span_dir * r
        rings.append([m.bm.verts.new(c + ld * (chord * 0.25 - u) + nu * v) for u, v in airfoil(chord)])
    for i, (a, b) in enumerate(zip(rings, rings[1:])): m.bridge(a, b, tip_mat if tip_mat and i >= 4 else mat)
    m.cap(rings[0], mat, True); m.cap(rings[-1], tip_mat or mat)

def gearbox():
    m = part('main_gearbox', explode=(0, -0.9, 0))
    m.stl('ring_gear', 'alu', at(V((0, 0, PLAN_Z))))
    m.sweep([V((0, 0, 1.80)), V((0, 0, BEVEL_Z + 0.06)), V((0, 0, PLAN_Z - 0.03))], [0.16, 0.27, 0.24], 'alu', 32, caps=False)   # lower case
    for a in (0, 120, 240):                                                                         # mounting struts to the roof
        d = V((cos(radians(a + 30)), sin(radians(a + 30)), 0))
        m.tube(V((0, 0, 1.92)) + d * 0.25, V((0, 0, 1.70)) + d * 0.55, 0.018, 'steel', 8)
    inp = part('input_shaft', pivot=V((-0.30, 0, BEVEL_Z + 0.02)), axis=X, explode=(-0.5, 0, -0.3))
    inp.stl('bevel_input', 'steel', at(V((-0.30, 0, BEVEL_Z + 0.02)), TO_X))
    inp.tube(V((-0.30, 0, BEVEL_Z + 0.02)), ENGINE + V((0.36, 0, 0)), 0.022, 'steel', 12)
    for x in (-0.38, -0.47): inp.disc(V((x, 0, ENGINE.z + (BEVEL_Z + 0.02 - ENGINE.z) * 0.5)), X, 0.035, 0.012, 'black', 12)   # flex couplings
    b = part('bevel_gear', pivot=V((0, 0, BEVEL_Z)), axis=Z, explode=(0, 0, -0.6))
    b.stl('bevel_output', 'steel', at(V((0, 0, BEVEL_Z - 0.05))))
    b.tube(V((0, 0, BEVEL_Z)), V((0, 0, PLAN_Z + 0.03)), 0.03, 'steel', 12)
    b.stl('sun', 'brass', at(V((0, 0, PLAN_Z))))
    p = part('planets', pivot=V((0, 0, PLAN_Z)), parent='mast', axis=Z, explode=(0, 0.6, 0))
    p.stl('planets', 'steel', at(V((0, 0, PLAN_Z))))

def rotor():
    ms = part('mast', pivot=V((0, 0, PLAN_Z)), axis=Z, explode=(0, 0, 1.0))
    ms.stl('carrier', 'steel', at(V((0, 0, PLAN_Z))))
    ms.tube(V((0, 0, PLAN_Z + 0.03)), V((0, 0, HUB_Z + 0.10)), 0.048, 'steel', 16)
    sl = part('swashplate_lower', pivot=V((0, 0, SWASH_Z)), explode=(0, 0, 0.35))                    # tilts and slides, does not spin
    sl.stl('swash_lower', 'alu', at(V((0, 0, SWASH_Z))))
    su = part('swashplate_upper', pivot=V((0, 0, SWASH_Z)), parent='mast', axis=Z, explode=(0, 0, 0.6))
    su.stl('swash_upper', 'steel', at(V((0, 0, SWASH_Z))))
    for k, a in ((1, 0), (2, 120), (3, 240)):                                                         # servos from the gearbox deck
        d = V((cos(radians(a)), sin(radians(a)), 0)); lug = V((0, 0, SWASH_Z)) + d * 0.215
        s = part(f'servo_{k}', pivot=lug, explode=(d.x * 0.5, d.y * 0.5, 0))
        base = V((0, 0, PLAN_Z - 0.05)) + d * 0.32
        s.tube(base, base.lerp(lug, 0.6), 0.03, 'dark', 12); s.tube(base.lerp(lug, 0.55), lug, 0.012, 'steel', 8)
        s.disc(base, V((-d.y, d.x, 0)), 0.03, 0.05, 'dark', 12)
    h = part('rotor_hub', pivot=V((0, 0, HUB_Z)), parent='mast', axis=V((0, 1, 0)), explode=(0, 0, 1.4))   # teeters about the pin (y)
    h.stl('hub', 'alu', at(V((0, 0, HUB_Z))))
    for k, s in ((1, 1), (2, -1)):
        horn = V((s * 0.33, s * 0.15, HUB_Z - 0.05)); lug = V((0, 0, SWASH_Z + 0.045)) + V((cos(radians(24 + 180 * (k - 1))), sin(radians(24 + 180 * (k - 1))), 0)) * 0.2
        pl = part(f'pitch_link_{k}', pivot=lug, parent='swashplate_upper', explode=(s * 0.3, s * 0.3, 0.9))
        pl.tube(lug, horn, 0.011, 'steel', 8); pl.disc(lug, Y, 0.02, 0.03, 'steel', 10); pl.disc(horn, Y, 0.02, 0.03, 'steel', 10)
        bl = part(f'blade_{k}', pivot=V((s * 0.42, 0, HUB_Z)), parent='rotor_hub', axis=V((s, 0, 0)), explode=(s * 1.2, 0, 1.6))
        blade(bl, V((0, 0, HUB_Z)), V((s, 0, 0)), V((0, s, 0)), 0.55, R_BLADE, CHORD, 'blade', 8.0, 'tip')
        bl.box(V((s * 0.62, 0, HUB_Z)), (0.30, 0.24, 0.06), 'alu')                                      # root fitting in the grip
    sc = part('scissors', pivot=V((0, 0, SWASH_Z + 0.2)), parent='mast', axis=Z, explode=(0.3, 0, 0.8))
    a, b2, c = V((0.15, 0, SWASH_Z + 0.06)), V((0.20, 0, SWASH_Z + 0.22)), V((0.06, 0, SWASH_Z + 0.30))
    sc.tube(a, b2, 0.012, 'steel', 8); sc.tube(b2, c, 0.012, 'steel', 8); sc.disc(b2, Y, 0.02, 0.03, 'steel', 10)

def engine():
    m = part('engine', pivot=ENGINE, explode=(-0.6, 0, 0.5))
    m.stl('turboshaft', 'alu', at(ENGINE + V((-0.01, 0, 0)), TO_X))
    m.disc(ENGINE + V((0.07, 0, 0)), X, 0.195, 0.05, 'dark', 32)                                      # combustor ring
    ex = ENGINE + V((-0.36, 0, 0.02)); m.tube(ex, ex + V((-0.30, 0, 0.26)), 0.12, 'hot', 20, caps=False)   # exhaust stack
    t = part('turbine', pivot=ENGINE + V((-0.12, 0, 0)), axis=X, explode=(-0.6, 0.6, 0.5))            # power turbine wheel behind a window
    hub = ENGINE + V((-0.12, 0, 0))
    t.disc(hub, X, 0.06, 0.05, 'steel', 16)
    for k in range(24):
        a = TAU * k / 24; d = V((0, cos(a), sin(a)))
        t.box(hub + d * 0.11, (0.04, 0.012, 0.10), 'hot', Matrix.Rotation(a, 3, 'X') @ Matrix.Rotation(radians(30), 3, 'Z'))

def tail():
    m = part('tail_driveshaft', pivot=V((-1.45, 0, 1.97)), axis=X, explode=(0, 0, 0.6))
    a, b = V((-1.45, 0, 1.97)), TAIL_GB + V((0.10, 0, 0))
    m.tube(a, b, 0.025, 'alu', 12)
    for f in (0.2, 0.4, 0.6, 0.8): m.disc(a.lerp(b, f), (b - a).normalized(), 0.04, 0.03, 'black', 12)   # hanger bearings
    m.stl('tail_bevel_a', 'steel', at(TAIL_GB + V((0.06, 0, 0)), Matrix.Rotation(-pi / 2, 4, 'Y') @ S))
    g = part('tail_gearbox', explode=(-0.4, 0, 0.3))
    g.disc(TAIL_GB, Y, 0.09, 0.16, 'alu', 24); g.sweep([TAIL_GB + V((0.04, 0, 0)), TAIL_GB + V((0.16, 0, 0))], [0.07, 0.04], 'alu', 16, caps=False)
    r = part('tail_rotor', pivot=TAIL_ROTOR, axis=V((0, -1, 0)), explode=(-0.3, -0.6, 0))
    r.stl('tail_bevel_b', 'steel', at(TAIL_GB + V((0, -0.06, 0)), Matrix.Rotation(pi / 2, 4, 'X') @ S))
    r.tube(TAIL_GB + V((0, -0.06, 0)), TAIL_ROTOR, 0.02, 'steel', 10)
    r.stl('tail_hub', 'alu', at(TAIL_ROTOR, Matrix.Rotation(pi / 2, 4, 'X') @ S, pi / 2))
    for s in (1, -1):
        blade(r, TAIL_ROTOR, V((0, 0, s)), V((s, 0, 0)), 0.10, 0.80, 0.14, 'blade', 4.0, 'tip')

def controls():
    C = CTRL
    m = part('cyclic', pivot=C + V((1.30, -0.32, 0.60)), explode=(0.3, -0.4, 0.3))
    m.sweep([C + V((1.30, -0.32, 0.60)), C + V((1.32, -0.32, 0.95)), C + V((1.28, -0.32, 1.12))], [0.018, 0.016, 0.02], 'black', 10)
    m.disc(C + V((1.30, -0.32, 0.60)), V((0, 0, 1)), 0.06, 0.04, 'rubber' if 'rubber' in common.MATS else 'black', 12)
    m = part('collective', pivot=C + V((0.95, -0.05, 0.62)), axis=Y, explode=(0.2, 0.4, 0.3))
    m.sweep([C + V((0.95, -0.05, 0.62)), C + V((1.35, -0.07, 0.78)), C + V((1.52, -0.08, 0.80))], [0.02, 0.018, 0.024], 'black', 10)
    m = part('pedals', explode=(0.5, 0, 0))
    for y in (-0.42, -0.22): m.box(C + V((1.95, y, 0.52)), (0.04, 0.09, 0.16), 'alu', Matrix.Rotation(radians(-20), 3, 'Y'))
    m.tube(C + V((1.98, -0.48, 0.45)), C + V((1.98, -0.16, 0.45)), 0.012, 'steel', 8)
    m = part('control_rods', explode=(0, -0.5, 0.4))                                                  # mixing linkage up to the servos
    for k, a in enumerate((0, 120, 240)):
        d = V((cos(radians(a)), sin(radians(a)), 0)); top = V((0, 0, PLAN_Z - 0.05)) + d * 0.32
        m.sweep([C + V((1.0, -0.2 + 0.05 * k, 0.55)), V((0.6, -0.2 + 0.05 * k, 1.55)), top + V((0, 0, -0.05))], 0.008, 'steel', 6)

def airframe():
    m = part('skids', explode=(0, 0, -0.5))
    for s in (1, -1):
        m.sweep([V((-1.45, s * 1.0, 0.05)), V((1.55, s * 1.0, 0.05)), V((1.80, s * 1.0, 0.18))], 0.035, 'alu', 12)
    for x in (0.95, -0.75):
        m.sweep([V((x, 1.0, 0.07)), V((x, 0.85, 0.42)), V((x, 0.45, 0.58)), V((x, -0.45, 0.58)), V((x, -0.85, 0.42)), V((x, -1.0, 0.07))], 0.04, 'alu', 12)
    m = part('fuel_tank', explode=(0, 0, -0.7))
    m.box(V((-0.65, 0, 1.05)), (0.60, 0.90, 0.60), 'black')             # behind the cabin's rear wall, under the gearbox deck

# ---------------------------------------------------------------- Tripo shell
TRIPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tripo', 'body.glb')
SHELL_TRIS, TEX = 24000, 2048
FIT = (11.3, 8.55, 8.55)      # Tripo units -> metres; its heli is stubby: the length stretch puts its hub and tail rotor on the CAD's
HUB_X = 0.0824                # Tripo mast, along its length
BOOM_X, FINS_X = -2.17, -5.45 # boom joint and fin panel lines (fitted metres)

def shell_material(img, name, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Metallic'].default_value = 0.0; b.inputs['Roughness'].default_value = rough
    return m

def door_front(z): return 2.70 - max(0.0, z - 1.25) * 0.55      # front door's leading edge follows the windscreen frame

def classify(c, main, box, n):
    """Part id for a face of the main hull, or for a whole loose Tripo piece (box = its bounds); None = cut away (the CAD has its own)."""
    (x0, y0, z0), (x1, y1, z1) = box; x, y, z = c; s = 'l' if y > 0 else 'r'
    if not main:
        if z0 > 2.8 or (z0 > 2.4 and abs(x) < 0.8) or x1 < -6.15 or z0 < 0.1: return None   # main rotor, tail rotor, skids
        if x > 2.1 and z > 1.3 and z1 - z0 > 0.5: return 'canopy'
        if 2.7 < x < 3.1 and 0.2 < abs(y) < 0.32 and z1 < 1.1 and x1 - x0 < 0.3: return None              # Tripo's cyclic sticks
        if abs(y) > 0.55 and 0.75 < z < 2.0 and 0.1 < x < 2.75: return f'rear_door_{s}' if x < 1.55 else f'door_{s}'
        if z > 1.7 and -1.9 < x < 1.2: return 'engine_cowling' if x < -0.45 else 'transmission_cowling'
        if x < -4.85: return 'tail_fins'
        if x < BOOM_X: return 'tail_boom'
        return 'fuselage'
    if x < FINS_X: return 'tail_fins'
    if x < BOOM_X: return 'tail_boom'
    if abs(n.y) > 0.6 and abs(y) > 0.5 and 0.74 < z < 1.98 and 1.55 < x < door_front(z): return f'door_{s}'
    return 'fuselage'

HINGES = {   # id -> (pivot, axis, explode); the doors swing about their hinge line, the rest only slides
    'fuselage': (None, None, (0, 0, 0)), 'canopy': (None, None, (1.4, 0, 0.7)),
    'door_l': (V((2.55, 0.78, 1.3)), Z, (0.3, 1.3, 0)), 'door_r': (V((2.55, -0.78, 1.3)), Z, (0.3, -1.3, 0)),
    'rear_door_l': (V((0.2, 0.78, 1.3)), Z, (-0.2, 1.5, 0)), 'rear_door_r': (V((0.2, -0.78, 1.3)), Z, (-0.2, -1.5, 0)),
    'transmission_cowling': (None, None, (0.9, 0, 0.5)), 'engine_cowling': (None, None, (-0.5, 0, 1.0)),
    'tail_boom': (None, None, (-0.6, 0, -0.9)), 'tail_fins': (None, None, (-1.6, 0, -0.4))}

def islands(bm):
    """Tripo's loose pieces (doors, canopy, cowlings, rotor, skids...), biggest first."""
    seen, out = set(), []
    for f in bm.faces:
        if f in seen: continue
        st, comp = [f], []; seen.add(f)
        while st:
            g = st.pop(); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h not in seen: seen.add(h); st.append(h)
        out.append(comp)
    return sorted(out, key=len, reverse=True)

def tripo_body():
    if not os.path.exists(TRIPO): print('no Tripo body, shell skipped:', TRIPO); return
    bpy.ops.import_scene.gltf(filepath=TRIPO)
    ob = next(o for o in bpy.context.selected_objects if o.type == 'MESH'); me = ob.data
    me.transform(Matrix.Rotation(pi / 2, 4, 'Z') @ ob.matrix_world)            # Tripo nose is -y: turn it to +x
    for o in list(bpy.context.selected_objects):
        if o != ob: bpy.data.objects.remove(o)
    ob.parent = None; ob.matrix_world = Matrix.Identity(4)
    me.transform(Matrix.Diagonal(V((*FIT, 1))) @ Matrix.Translation(V((-HUB_X, 0, 0))))
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    ids = sorted(HINGES); pl = bm.faces.layers.int.new('part')
    for k, comp in enumerate(islands(bm)):
        vs = [v.co for f in comp for v in f.verts]; box = (V([min(v[i] for v in vs) for i in range(3)]), V([max(v[i] for v in vs) for i in range(3)]))
        whole = None if k == 0 else classify(sum(vs, V()) / len(vs), False, box, None)
        for f in comp:
            pid = classify(f.calc_center_median(), True, box, f.normal) if k == 0 else whole
            f[pl] = -1 if pid is None else ids.index(pid)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[pl] < 0], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)      # some Tripo triangles are wound backwards and shade black
    bm.to_mesh(me); bm.free()
    dec = ob.modifiers.new('d', 'DECIMATE'); dec.ratio = min(1, SHELL_TRIS / len(me.polygons)); dec.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='d')
    bm = bmesh.new(); bm.from_mesh(me); flipped = 0
    for f in bm.faces:   # a triangle wound against its neighbours shades black here and vanishes under back-face culling in the app
        around = sum((g.normal * g.calc_area() for v in f.verts for g in v.link_faces if g is not f), V((0, 0, 0)))
        if f.normal.dot(around) < 0: f.normal_flip(); flipped += 1
    bm.to_mesh(me); bm.free(); print('flipped', flipped)
    img = next(n.image for n in me.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE')
    img.scale(TEX, TEX); img.file_format = 'JPEG'
    shell_material(img, 'shell', 0.4); shell_material(img, 'shell_glass', 0.08)    # gloss paint; the canopy shines
    pa = me.attributes['part'].data
    for k, pid in enumerate(ids):
        piv, ax, ex = HINGES[pid]
        m = part(pid, pivot=piv, axis=ax, explode=ex); m.mats = ['shell_glass' if pid == 'canopy' else 'shell']
        b2 = bmesh.new(); b2.from_mesh(me)
        bmesh.ops.delete(b2, geom=[f for f in b2.faces if pa[f.index].value != k], context='FACES')
        for f in b2.faces: f.material_index = 0; f.smooth = True
        m.bm.free(); m.bm = b2
        print(pid, len(b2.faces), 'faces')
    bpy.data.objects.remove(ob)

_make_objects = common.make_objects
def make_objects():
    """Shell normals weighted by face area: Tripo's big flat triangles meet slivers at odd angles, and plain smoothing shades them dark."""
    obs = _make_objects()
    for pid in HINGES:
        if pid not in obs: continue
        ob = obs[pid]; wn = ob.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.mode = 'FACE_AREA'; wn.keep_sharp = True
        bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='wn')
    return obs
common.make_objects = make_objects

def build():
    gearbox(); rotor(); engine(); tail(); controls(); airframe(); tripo_body()

VIEWS = {'left_34': ((7.0, 8.5, 5.0), (-1.2, 0, 1.8), 30), 'rotor_head': ((1.6, 1.4, 3.3), (0, 0, 2.45), 40),
         'drive': ((0.6, -2.4, 2.4), (-0.6, 0, 2.05), 40), 'tail': ((-5.0, -1.6, 2.6), (-6.3, -0.2, 2.25), 40)}
if '--explode' in sys.argv:   # room for the shell parts flying off
    VIEWS = {'x_left_34': ((7.5, 10.5, 6.0), (-0.6, 0, 1.7), 30), 'x_right_34': ((6.5, -11.0, 5.5), (-0.6, 0, 1.6), 30)}
if '--ortho' in sys.argv:   # fitting views: near-orthographic side, front, top
    VIEWS = {'o_side': ((-1.0, -160, 1.6), (-1.0, 0, 1.6), 400), 'o_front': ((160, 0, 1.6), (0, 0, 1.6), 900),
             'o_top': ((-1.0, 0, 160), (-1.0, 0.001, 0), 400), 'r_34': ((5.5, -6.0, 3.0), (0.8, 0, 1.3), 35)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS.get('left_34'))
