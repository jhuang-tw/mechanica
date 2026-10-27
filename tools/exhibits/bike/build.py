# Road bicycle exhibit, built from scratch for Mechanica: one GLB node per semantic part, plus thumb.jpg.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/bike/build.py -- public/exhibits/bike
# Model frame (Blender): metres, ground z = 0, front = +x, drive (chain) side = -y. glTF export turns that into
# front +x, up +y, drive side +z. Every node's origin is its pivot, so the app turns a part with node.rotateOnAxis(extras.axis).
# Node ids = the `parts[].id` of public/exhibits/bike/manifest.json (checked at export). All nodes sit flat under the scene
# except pedal_l / pedal_r, which are children of crank; spin axes are glTF -z (Blender +y) so positive turns forward.
# Run tools/exhibits/bike/cad.py first: chainring, cassette, cranks, hubs and jockey wheels come from its STLs.
import bpy, bmesh, sys, os, json
from math import sin, cos, atan2, pi, radians
from mathutils import Vector as V, Matrix

OUT = os.path.abspath(sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'public/exhibits/bike')   # holds manifest.json; gets thumb.jpg
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model.raw.glb')   # tools/optimize-glb.mjs turns it into OUT/model.glb
TAU = 2 * pi
Y = V((0, 1, 0))
CAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cad', 'out')
# CAD parts are modelled in mm about +z; these put CAD z on the bike's axle (+90 deg about x: z -> -y = drive side)
TO_DRIVE = Matrix.Rotation(pi / 2, 4, 'X') @ Matrix.Scale(0.001, 4)
TO_LEFT = Matrix.Rotation(-pi / 2, 4, 'X') @ Matrix.Scale(0.001, 4)

# ---------------------------------------------------------------- geometry (metres)
WR = 0.311                      # rim bead seat radius (700c)
TR = 0.0135                     # tyre section radius (~25 mm)
WHEEL = WR + 2 * TR - 0.002     # wheel radius on the ground
RA = V((-0.41, 0, WHEEL))       # rear axle
FA = V((0.575, 0, WHEEL))       # front axle
BB = V((0, 0, 0.27))            # bottom bracket
HA, SA = radians(73), radians(73.5)
U = V((-cos(HA), 0, sin(HA)))   # steering axis, pointing up
PERP = V((sin(HA), 0, cos(HA))) # forward, perpendicular to the steering axis
AXP = FA - PERP * 0.045         # fork offset (rake)
HB = AXP + U * 0.37             # head tube bottom (= fork crown)
HT = HB + U * 0.15              # head tube top
SD = V((-cos(SA), 0, sin(SA)))
STT = BB + SD * 0.52            # seat tube top
RING, COGS = 50, [11, 12, 13, 14, 15, 17, 19, 21, 23, 25, 28]
COG = 5                         # the chain sits on the 17T at rest
PITCH = 0.0127
rT = lambda n: PITCH / (2 * sin(pi / n))
CHAIN_Y = -0.044                # chain line
CRANK = 0.1725

MATS = {   # base colour (linear), metallic, roughness
    'paint':  ((0.50, 0.03, 0.02), 0.3, 0.28),
    'black':  ((0.012, 0.012, 0.013), 0.0, 0.6),
    'rubber': ((0.015, 0.015, 0.015), 0.0, 0.85),
    'alu':    ((0.78, 0.79, 0.80), 1.0, 0.32),
    'steel':  ((0.45, 0.46, 0.47), 1.0, 0.4),
    'gum':    ((0.33, 0.19, 0.08), 0.0, 0.7),
    'dark':   ((0.05, 0.05, 0.055), 1.0, 0.45),   # inner chain plates, so the links alternate bright/dark at a distance
}

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
        bpy.ops.wm.stl_import(filepath=os.path.join(CAD, name + '.stl'))
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
        rings, ref = [], None
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            if ref is None: ref = Y if abs(t.dot(Y)) < 0.9 else V((1, 0, 0))
            rings.append(self.ring(p, t, rad[i], seg, ref)); ref = (rings[-1][0].co - p).normalized()
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

    def sprocket(self, c, n, t, r_in, mat):
        """Toothed annulus in the xz plane (axis = y), n teeth on a chain pitch circle."""
        rp = rT(n); outer = []
        for k in range(n):
            for da, dr in ((-0.5, -0.0042), (-0.2, 0.0032), (0.2, 0.0032), (0.5, -0.0042)):
                a = TAU * (k + 0.5 + da) / n; outer.append((rp + dr) * V((cos(a), 0, sin(a))))
        m = len(outer); inner = [r_in * V((cos(TAU * i / m), 0, sin(TAU * i / m))) for i in range(m)]
        lay = lambda pts, y: [self.bm.verts.new(c + p + V((0, y, 0))) for p in pts]
        o0, o1, i0, i1 = lay(outer, -t / 2), lay(outer, t / 2), lay(inner, -t / 2), lay(inner, t / 2)
        self.bridge(o1, o0, mat); self.bridge(i0, i1, mat); self.bridge(o0, i0, mat); self.bridge(i1, o1, mat)

# ---------------------------------------------------------------- parts
PARTS = {}   # id -> dict(m=Mesh, pivot, parent, axis, explode)

def part(pid, pivot=None, parent=None, axis=None, explode=(0, 0, 0)):
    PARTS[pid] = dict(m=Mesh(), pivot=V(pivot) if pivot is not None else None, parent=parent, axis=axis, explode=V(explode))
    return PARTS[pid]['m']

def frame():
    m = part('frame', explode=(0, 0, 0))
    ht0, ht1 = HB - U * 0.005, HT + U * 0.005
    m.tube(ht0, ht1, 0.019, 'paint', 16)                                          # head tube
    m.tube(BB + SD * 0.03, STT, 0.0145, 'paint', 14)                              # seat tube
    m.tube(BB + SD * 0.035 + PERP * 0.02, HB + U * 0.025, 0.0175, 'paint', 14)    # down tube
    m.tube(STT - SD * 0.035, HT - U * 0.03, 0.0135, 'paint', 14)                  # top tube
    m.disc(BB, Y, 0.022, 0.072, 'paint', 20)                                      # BB shell
    for s in (-1, 1):
        drop = RA + V((0, s * 0.066, 0))
        m.sweep([BB + V((0, s * 0.03, -0.005)), BB.lerp(drop, 0.45) + V((0, s * 0.048, 0)), drop], [0.011, 0.01, 0.0075], 'paint', 10)   # chainstay
        m.sweep([drop, drop.lerp(STT - SD * 0.06, 0.5) + V((0, -s * 0.012, 0)), STT - SD * 0.06 + V((0, s * 0.016, 0))], [0.0075, 0.0085, 0.009], 'paint', 10)   # seatstay
        m.box(drop + V((0.004, 0, -0.004)), (0.03, 0.005, 0.032), 'paint')       # dropout
    m.tube(STT - SD * 0.13 + V((0, -0.03, 0)), STT - SD * 0.13 + V((0, 0.03, 0)), 0.005, 'paint', 8)   # brake bridge
    m.tube(STT - SD * 0.01, STT + SD * 0.012, 0.0165, 'black', 14)                # seat clamp

def fork():
    m = part('fork', pivot=HB, axis=U, explode=(0.25, 0, 0.05))
    m.tube(HB - U * 0.01, HT + U * 0.035, 0.0145, 'black', 12)                   # steerer
    m.box(HB - U * 0.015, (0.035, 0.105, 0.035), 'black', Matrix.Rotation(-(pi / 2 - HA), 3, 'Y'))   # crown
    for s in (-1, 1):
        top = HB - U * 0.03 + V((0, s * 0.045, 0)); tip = FA + V((0, s * 0.052, 0))
        mid = top.lerp(tip, 0.6) + PERP * 0.012
        m.sweep([top, mid, tip + V((0, 0, 0.012)), tip], [0.0125, 0.0105, 0.008, 0.007], 'black', 10)
    m.tube(HT + U * 0.006, HT + U * 0.03, 0.0175, 'alu', 14)                      # headset spacers + top cap

def handlebar():
    stem0 = HT + U * 0.02; dirS = (PERP * 0.92 + U * 0.25).normalized(); stem1 = stem0 + dirS * 0.10
    st = part('stem', pivot=stem0, axis=U, explode=(0.1, 0, 0.2))
    st.tube(stem0 - dirS * 0.02, stem1, 0.016, 'alu', 12)
    st.tube(stem1 + V((0, -0.02, 0)), stem1 + V((0, 0.02, 0)), 0.0185, 'alu', 12)   # bar clamp
    m = part('handlebar', pivot=stem1, axis=V((0, 1, 0)), explode=(0.15, 0, 0.3))
    pts = []
    for s in (-1, 1):
        side = [stem1 + V((0.0, s * 0.07, 0)), stem1 + V((0.0, s * 0.19, 0)), stem1 + V((0.04, s * 0.205, -0.01)),
                stem1 + V((0.075, s * 0.21, -0.05)), stem1 + V((0.07, s * 0.21, -0.11)), stem1 + V((0.035, s * 0.21, -0.135)), stem1 + V((-0.04, s * 0.21, -0.13))]
        pts.append(side)
    m.sweep(pts[0][::-1] + pts[1], 0.012, 'black', 10)                            # drop bar (taped)
    for hood in (p[3] for p in pts):                                              # brake/shift levers on the hoods
        m.box(hood + V((0.02, 0, 0.015)), (0.05, 0.026, 0.032), 'black', Matrix.Rotation(radians(-15), 3, 'Y'))   # hood body
        m.sweep([hood + V((0.04, 0, 0.012)), hood + V((0.05, 0, -0.03)), hood + V((0.035, 0, -0.085))], [0.006, 0.006, 0.005], 'alu', 8)   # blade

def wheel(pid, axle, explode):
    m = part(pid, pivot=axle, axis=V((0, 1, 0)), explode=explode)
    front = pid == 'front_wheel'
    m.stl('hub_front' if front else 'hub_rear', 'alu', Matrix.Translation(axle) @ TO_DRIVE)
    # flange planes and spoke-hole radius as in cad.py (rear: drive-side flange closer in, room for the cassette)
    fy = {1: 0.027, -1: -0.027} if front else {1: 0.027, -1: -0.020}; fr = 0.018 if front else 0.020
    m.disc(axle, Y, WR + 0.002, 0.02, 'black', 72, r_in=WR - 0.024)               # rim
    for k in range(24):                                                           # 12 spokes per flange, one per hole
        s = 1 if k % 2 else -1; h = radians(30 * (k // 2)); a = h + radians(30 if s < 0 else -15)
        hub = axle + V((cos(h) * fr, fy[s], sin(h) * fr)); rim = axle + V((cos(a) * (WR - 0.02), s * 0.003, sin(a) * (WR - 0.02)))
        m.tube(hub, rim, 0.0011, 'steel', 4, caps=False)
    m.torus(axle, Y, WR + TR - 0.001, TR, 'rubber', 72, 10)
    m.torus(axle, Y, WR + 0.004, 0.0105, 'gum', 72, 6)                            # tan sidewalls peeking out
    return m

def drivetrain():
    m = part('crank', pivot=BB, axis=V((0, 1, 0)), explode=(0, -0.25, -0.1))
    m.disc(BB, Y, 0.012, 0.14, 'steel', 12)                                       # spindle
    # CAD arms: drive arm down with its spider in the ring plane (arm face 24 mm outboard of the chain line), left arm up
    m.stl('crank_right', 'alu', Matrix.Translation(BB + V((0, CHAIN_Y - 0.024, 0))) @ TO_DRIVE)
    m.stl('crank_left', 'alu', Matrix.Translation(BB + V((0, -CHAIN_Y + 0.024, 0))) @ TO_LEFT)
    pedals = [BB + V((0, CHAIN_Y - 0.024, -CRANK)), BB + V((0, -CHAIN_Y + 0.024, CRANK))]

    r = part('chainring', pivot=BB, axis=V((0, 1, 0)), explode=(0, -0.18, 0.05))
    r.stl('chainring', 'steel', Matrix.Translation(BB + V((0, CHAIN_Y, 0))) @ TO_DRIVE)

    for (pos, pid, s) in ((pedals[0], 'pedal_r', -1), (pedals[1], 'pedal_l', 1)):
        p = part(pid, pivot=pos, parent='crank', axis=V((0, 1, 0)), explode=(0, s * 0.3, 0))
        p.disc(pos + V((0, s * 0.03, 0)), Y, 0.006, 0.06, 'steel', 8)            # axle
        p.box(pos + V((0, s * 0.06, 0)), (0.11, 0.07, 0.014), 'black')           # platform
        p.box(pos + V((0.04, s * 0.06, 0.012)), (0.012, 0.07, 0.01), 'black')    # cleat edge

    c = part('cassette', pivot=RA, axis=V((0, 1, 0)), explode=(-0.15, -0.2, 0))
    c.stl('cassette', 'steel', Matrix.Translation(RA + V((0, -0.064, 0))) @ TO_DRIVE)   # 11T outermost

    # rear derailleur: hanger on the drop-out, parallelogram, cage with two jockey wheels under the 17T
    cogR = rT(COGS[COG]); cy = -0.064 + COG * 0.0039
    j1 = RA + V((0.0, cy, -cogR - 0.025)); j2 = j1 + V((0.012, 0, -0.07))
    d = part('rear_derailleur', pivot=j1, axis=V((0, 1, 0)), explode=(-0.1, -0.25, -0.1))
    bk = RA + V((-0.016, -0.072, -0.03)); pk = j1 + V((-0.012, -0.014, 0.014))   # B-knuckle on the hanger, P-knuckle over the cage
    d.box(RA + V((-0.006, -0.07, -0.014)), (0.022, 0.004, 0.034), 'black', Matrix.Rotation(0.5, 3, 'Y'))   # hanger
    d.disc(bk, Y, 0.010, 0.016, 'black', 16)
    for dz in (-0.006, 0.008): d.sweep([bk + V((0, 0, dz)), pk + V((0, 0, dz))], 0.0035, 'alu', 8)   # parallelogram links
    d.disc(pk, Y, 0.009, 0.016, 'black', 16)
    for j in (j1, j2): d.stl('jockey', 'black', Matrix.Translation(j) @ TO_DRIVE)
    for s in (-1, 1): d.box(j1.lerp(j2, 0.5) + V((0, s * 0.006, 0)), (0.03, 0.002, 0.1), 'alu', Matrix.Rotation(-0.17, 3, 'Y'))

    f = part('front_derailleur', pivot=BB + SD * 0.2, axis=SD, explode=(0.05, -0.25, 0.1))
    fc = BB + V((0, CHAIN_Y, 0)) + V((-cos(radians(60)), 0, sin(radians(60)))) * (rT(RING) + 0.012)
    f.tube(BB + SD * 0.19 + V((0, -0.016, 0)), BB + SD * 0.19 + V((0, 0.016, 0)), 0.018, 'black', 14, caps=False)   # band clamp
    f.box(fc + V((0, -0.008, 0.01)), (0.07, 0.002, 0.025), 'alu', Matrix.Rotation(-0.25, 3, 'Y'))
    f.box(fc + V((0, 0.008, 0.01)), (0.07, 0.002, 0.02), 'alu', Matrix.Rotation(-0.25, 3, 'Y'))
    f.tube(fc + V((0, 0, 0.02)), BB + SD * 0.19 + V((0, -0.01, 0)), 0.004, 'black', 6)

    # chain: links along ring top -> cog top, cog bottom -> jockeys -> ring bottom
    ch = part('chain', explode=(0, -0.35, 0))
    ringC, cogC = BB + V((0, CHAIN_Y, 0)), RA + V((0, cy, 0))
    rr, cr = rT(RING), cogR
    def arc(c, r, a0, a1, n): return [c + V((cos(a0 + (a1 - a0) * i / n) * r, 0, sin(a0 + (a1 - a0) * i / n) * r)) for i in range(n + 1)]
    path = [ringC + V((0, 0, rr))] + [cogC + V((0, 0, cr))] + arc(cogC, cr, pi / 2, pi * 1.25, 5)[1:] + [j1 + V((-0.006, 0, 0)), j2 + V((0.006, 0, -0.005)), ringC + V((0.04, 0, -rr))] \
        + arc(ringC, rr, -pi / 2, pi / 2, 16)[1:]
    pts = []
    for a, b in zip(path, path[1:]):
        n = max(1, round((b - a).length / PITCH))
        pts += [a.lerp(b, i / n) for i in range(n)]
    for i, p in enumerate(pts):   # one pitch: roller + pin at p, then a waisted plate pair to q, outer (bright) / inner (dark) alternating
        q = pts[(i + 1) % len(pts)]; t = (q - p)
        if t.length < 1e-6: continue
        rot = Matrix.Rotation(-atan2(t.z, t.x), 3, 'Y')
        ch.disc(p, Y, 0.0039, 0.0058, 'dark', 8)                                    # roller
        ch.disc(p, Y, 0.0018, 0.0112, 'steel', 6)                                   # pin
        outer = i % 2 == 0; w, mat = (0.0048, 'steel') if outer else (0.0037, 'dark')
        for sy in (-1, 1):
            o = V((0, sy * w, 0))
            for e in (p, q): ch.disc(e + o, Y, 0.0042, 0.0009, mat, 8)             # round plate ends
            ch.box(p.lerp(q, 0.5) + o, (PITCH * 0.9, 0.0009, 0.0052), mat, rot)    # waist

def brakes():
    for pid, parent, c, s, ex in (('brake_front', None, HB - U * 0.03 + PERP * 0.012, 1, (0.2, 0, 0.15)),
                                  ('brake_rear', None, STT - SD * 0.13 + V((-0.012, 0, 0)), -1, (-0.2, 0, 0.15))):
        m = part(pid, pivot=c, parent=parent, axis=V((1, 0, 0)), explode=ex)
        m.disc(c, V((1, 0, 0)), 0.005, 0.03, 'steel', 8)
        axle = FA if pid == 'brake_front' else RA
        for side in (-1, 1):    # caliper arms down to the rim, pads at the braking track
            pad = axle + (c - axle).normalized() * (WR - 0.012) + V((0, side * 0.013, 0))
            m.sweep([c + V((0, side * 0.01, 0)), c.lerp(pad, 0.5) + V((0, side * 0.03, 0)), pad + V((0, side * 0.006, 0))], [0.006, 0.005, 0.005], 'alu', 8)
            m.box(pad, (0.03, 0.006, 0.01), 'black', Matrix.Rotation(0, 3, 'Y'))

def saddle():
    top = STT + SD * 0.2
    p = part('seatpost', pivot=STT, axis=SD, explode=(0, 0, 0.25))
    p.tube(STT - SD * 0.08, top, 0.0136, 'black', 12)
    p.box(top + V((0, 0, 0.008)), (0.05, 0.03, 0.014), 'alu')
    s = part('saddle', pivot=top, axis=V((0, 1, 0)), explode=(0, 0, 0.4))
    prof = [(-0.12, 0.072), (-0.09, 0.07), (-0.04, 0.05), (0.02, 0.03), (0.08, 0.02), (0.14, 0.014)]
    rings = []
    for x, w in prof:
        c = top + V((x, 0, 0.04 + 0.006 * (x < -0.06)))
        rings.append([s.bm.verts.new(c + V((0, w * cos(a), 0.018 * sin(a) * (0.5 if sin(a) < 0 else 1)))) for a in (TAU * i / 12 for i in range(12))])
    for a, b in zip(rings, rings[1:]): s.bridge(a, b, 'black')
    s.cap(rings[0], 'black', True); s.cap(rings[-1], 'black')
    for sd in (-1, 1): s.sweep([top + V((-0.09, sd * 0.03, 0.03)), top + V((0, sd * 0.02, 0.012)), top + V((0.1, sd * 0.012, 0.025))], 0.0035, 'steel', 6)   # rails

def build():
    frame(); fork(); handlebar()
    wheel('front_wheel', FA, (0.45, 0, 0)); wheel('rear_wheel', RA, (-0.45, 0, 0))
    drivetrain(); brakes(); saddle()

# ---------------------------------------------------------------- scene, export, thumbnail
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
            ob, par = obs[pid], obs[p['parent']]
            ob.parent = par; ob.location = ob.location - par.location   # no rotations anywhere: offsets subtract
    return obs

def lights_camera(res, engine):
    sc = bpy.context.scene; sc.render.engine = engine; sc.render.resolution_x, sc.render.resolution_y = res
    if engine == 'CYCLES':
        sc.cycles.samples = 48; sc.cycles.use_denoising = True
        try:   # Jim's PC: AMD GPU through HIP
            prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'HIP'; prefs.get_devices()
            for d in prefs.devices: d.use = True
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

# look pass before export: whole bike from both sides and front, plus a close-up of the drivetrain
VIEWS = {'drive_side': ((0.55, -2.6, 0.75), (0.07, 0, 0.5), 50), 'left_side': ((-0.3, 2.6, 0.9), (0.07, 0, 0.5), 50),
         'front': ((2.4, -0.9, 1.1), (0.07, 0, 0.5), 50), 'drivetrain': ((-0.05, -0.85, 0.45), (-0.2, -0.04, 0.3), 50)}

def preview(folder):
    os.makedirs(folder, exist_ok=True); sc = lights_camera((640, 480), 'CYCLES'); sc.cycles.samples = 24
    sc.render.image_settings.file_format = 'PNG'
    for name, (loc, target, lens) in VIEWS.items(): shoot(os.path.join(folder, name + '.png'), loc, target, lens)

def thumbnail(path):
    sc = lights_camera((512, 512), 'CYCLES'); sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 85
    shoot(path, *VIEWS['drive_side'])

def check_manifest():
    with open(os.path.join(OUT, 'manifest.json'), encoding='utf-8') as f: ids = {p['id'] for p in json.load(f)['parts']}
    assert ids == set(PARTS), f'manifest vs model: missing {ids - set(PARTS)}, extra {set(PARTS) - ids}'

if __name__ == '__main__':
    for ob in list(bpy.data.objects): bpy.data.objects.remove(ob)
    build(); check_manifest(); make_objects()
    if '--preview' in sys.argv:   # look first, export later
        preview(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview')); sys.exit(0)
    bpy.ops.export_scene.gltf(filepath=RAW, export_format='GLB', export_extras=True, export_yup=True,
                              export_apply=False, export_cameras=False, export_lights=False, export_materials='EXPORT')
    if '--no-thumb' not in sys.argv: thumbnail(os.path.join(OUT, 'thumb.jpg'))
    tris = sum(len(ob.data.polygons) for ob in bpy.data.objects if ob.type == 'MESH')
    print(f'bike: {len(PARTS)} parts, {tris} faces ->', OUT)
