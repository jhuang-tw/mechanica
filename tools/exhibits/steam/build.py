# Steam locomotive exhibit (generic 0-6-0 tank engine), built from scratch for Mechanica: one GLB node per semantic part.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/steam/build.py -- public/exhibits/steam [--preview]
# Run tools/exhibits/steam/cad.py first (wheels, cylinders, pistons, valves and crossheads come from its STLs).
# Model frame (Blender): metres, rail top z = 0, smokebox = +x, engine's left = +y. glTF: front +x, up +y, right = +z.
# Wheelsets spin about glTF -z (Blender +y): a positive turn drives forward. Right cranks lead the left by 90 deg; at rest the
# right crankpins are on top and the left ones at the front. Everything else in the motion sits where that crank angle puts it;
# the app moves pistons, crossheads, rods and valve gear as linkages (see the node list sent with the model).
# The outer shell is a Tripo3D mesh (tools/exhibits/steam/tripo/body.glb, kept out of git): aligned to the CAD axles, its wheels,
# motion and frames cut away, decimated and split along its panel lines into smokebox, boiler cladding, side tanks, cab and roof.
# Without it, `--shell <glb>` reuses the shell parts of a published model (node tools/decode-glb.mjs public/exhibits/steam/model.glb <glb>).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths
import common

S = Matrix.Scale(0.001, 4)
NY = Matrix.Rotation(pi / 2, 4, 'X') @ S      # CAD z -> Blender -y, CAD y -> +z
PY = Matrix.Rotation(-pi / 2, 4, 'X') @ S     # CAD z -> Blender +y, CAD y -> -z
def at(p, M=S, rz=0): return Matrix.Translation(p) @ M @ Matrix.Rotation(rz, 4, 'Z')

# ---------------------------------------------------------------- layout (metres)
AZ = 0.60                                     # axle height = tread radius
AXLES = [1.45, 0.0, -1.45]
WY = 0.75                                     # wheel tread centre, |y|
CRANK, ROD = 0.30, 1.90
PHI = {1: 0.0, -1: pi / 2}                    # crank angle in the xz plane (from +x towards +z): left at front, right on top
CYL0, CY = 2.35, 1.00                         # cylinder back cover x, cylinder axis |y|
VZ = AZ + 0.34                                # valve axis height
GY = 1.06                                     # valve gear plane |y|
LINK = V((1.00, 0, 0.95))                     # expansion link trunnion (x, -, z)
BOILER_Z, BOILER_R = 2.10, 0.72               # centred in the Tripo boiler shell
TUBE_X, SB_X = 2.45, 2.72                     # front tube plate, chimney / blastpipe axis
BEAMS = (3.49, -2.77)                         # buffer beams under the shell's footplate ends

def pin(axle_x, side, r=CRANK, extra=0.0):
    a = PHI[side] + extra
    return V((axle_x + r * cos(a), 0, AZ + r * sin(a)))
def crosshead_x(side):
    p = pin(0, side); return p.x + (ROD ** 2 - (p.z - AZ) ** 2) ** 0.5
def Yv(v, y): return V((v.x, y, v.z))

common.MATS.update({   # base colour (linear), metallic, roughness
    'paint':  ((0.02, 0.02, 0.022), 0.2, 0.45),   # black loco paint
    'red':    ((0.35, 0.03, 0.02), 0.2, 0.40),
    'steel':  ((0.55, 0.56, 0.58), 1.0, 0.28),
    'iron':   ((0.10, 0.10, 0.11), 0.8, 0.55),
    'copper': ((0.80, 0.36, 0.20), 1.0, 0.35),
    'brass':  ((0.70, 0.50, 0.18), 1.0, 0.30),
    'wood':   ((0.18, 0.10, 0.05), 0.0, 0.80),
    'glow':   ((1.00, 0.35, 0.05), 0.0, 0.60),
})

X, Z = V((1, 0, 0)), V((0, 0, 1))

def closed(m, make):
    """Run make() and point the faces it added outwards (a closed solid)."""
    n = len(m.bm.faces); make(); m.bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(m.bm, faces=m.bm.faces[n:])

def rod(m, a, b, w0, w1, t, mat, bosses=(), flute=False, cups=()):
    """Flat rod in the xz plane at a.y: tapered web from a to b (heights w0 -> w1), thickness t along y, round bosses (pos, r).
    flute: raised flanges along both edges of the outer face (an I-section, as forged rods are); cups: oil cups on these bosses."""
    d = (b - a); L = d.length; d.normalize(); n = V((-d.z, 0, d.x))
    pts = [a + n * w0 / 2, b + n * w1 / 2, b - n * w1 / 2, a - n * w0 / 2]
    vs = [[m.bm.verts.new(p + V((0, dy, 0))) for p in pts] for dy in (-t / 2, t / 2)]
    m.face(vs[0][::-1], mat); m.face(vs[1], mat)
    for i in range(4): m.face([vs[0][i], vs[0][(i + 1) % 4], vs[1][(i + 1) % 4], vs[1][i]], mat)
    for c, r in bosses: m.disc(c, Y, r, t * 1.3, mat, 20)
    if flute:
        ra, rb = bosses[0][1], bosses[-1][1]; out = V((0, (1 if a.y > 0 else -1) * t / 2, 0))
        for e in (1, -1):
            p0 = a + d * ra * 0.9 + n * e * (w0 / 2 - 0.011) + out; p1 = b - d * rb * 0.9 + n * e * (w1 / 2 - 0.011) + out
            rod(m, p0, p1, 0.022, 0.022, 0.014, mat)
        for c, r in bosses: m.disc(c + out, Y, r * 0.55, 0.014, mat, 16)                  # bush faces
    for c, r in cups: oil_cup(m, c, r, mat)

def oil_cup(m, c, r, mat):
    """Oil cup with its cap on top of a boss of radius r."""
    m.tube(c + Z * r * 0.8, c + Z * (r + 0.05), 0.022, mat, 10); m.disc(c + Z * (r + 0.058), Z, 0.026, 0.016, mat, 10)

def prism(m, prof, x0, x1, mat):
    """Straight extrusion along x of a closed (y, z) profile."""
    def make():
        r0 = [m.bm.verts.new(V((x0, y, z))) for y, z in prof]; r1 = [m.bm.verts.new(V((x1, y, z))) for y, z in prof]
        m.bridge(r0, r1, mat); m.cap(r0, mat, True); m.cap(r1, mat)
    closed(m, make)

def arc_block(m, c, r0, r1, a0, a1, w, mat, seg=6):
    """Solid ring segment about the y axis through c (angles in the xz plane from +x towards +z), width w along y."""
    def make():
        ring = lambda r, dy: [m.bm.verts.new(c + V((r * cos(a), dy, r * sin(a)))) for a in (a0 + (a1 - a0) * i / seg for i in range(seg + 1))]
        q = [ring(r0, -w / 2), ring(r1, -w / 2), ring(r1, w / 2), ring(r0, w / 2)]
        for k in range(4):
            for i in range(seg): m.face([q[k][i], q[k][i + 1], q[(k + 1) % 4][i + 1], q[(k + 1) % 4][i]], mat)
        m.face([q[k][0] for k in range(4)], mat); m.face([q[k][-1] for k in range(4)][::-1], mat)
    closed(m, make)

def wheelsets():
    for i, x in enumerate(AXLES, 1):
        m = part(f'wheelset_{i}', pivot=V((x, 0, AZ)), axis=Y, explode=(0, 0, -0.9))
        m.tube(V((x, -WY - 0.085, AZ)), V((x, WY + 0.085, AZ)), 0.079, 'steel', 16)                    # axle, through the hubs
        for side in (1, -1):
            c = V((x, side * WY, AZ))
            m.stl('wheel', 'red', at(c, PY if side > 0 else NY, -PHI[side] if side > 0 else PHI[side]))
            p = Yv(pin(x, side), side * WY)
            reach = 0.20 if x == 0 else 0.15
            m.tube(p + V((0, side * 0.05, 0)), p + V((0, side * reach, 0)), 0.05, 'steel', 14)           # crankpin
            m.disc(c + V((0, side * 0.095, 0)), Y, 0.06, 0.02, 'steel', 16)                              # axle end
            if x != 0: m.disc(p + V((0, side * (reach + 0.01), 0)), Y, 0.068, 0.025, 'steel', 16)       # crankpin collar
            if x == 0:                                                                                   # return crank on the main pin
                e = Yv(pin(0, side, 0.13, -pi / 2 * side), side * (GY - 0.02))
                rod(m, Yv(p, side * (GY - 0.02)), e, 0.12, 0.08, 0.04, 'steel', [(e, 0.045)])
                m.tube(e, e + V((0, side * 0.06, 0)), 0.025, 'steel', 8)

def motion(side):
    s = 'l' if side > 0 else 'r'; y = side * CY
    xc = crosshead_x(side); X = V((xc, y, AZ))
    m = part(f'cylinder_{s}', explode=(0.35, side * 0.6, 0)); m.stl(f'cylinder_{s}', 'iron', at(V((CYL0, y, AZ))))
    for c, r, nb in ((V((CYL0 + 0.762, y, AZ)), 0.27, 12), (V((CYL0 + 0.782, y, VZ)), 0.16, 8)):     # front covers, studded
        m.disc(c, X, r, 0.025, 'iron', 32); m.disc(c + X * 0.03, X, r * 0.45, 0.04, 'iron', 20)
        for k in range(nb):
            t = TAU * (k + 0.5) / nb; m.disc(c + V((0.018, r * 0.86 * cos(t), r * 0.86 * sin(t))), X, 0.016, 0.016, 'iron', 6)
    for x in (CYL0 + 0.09, CYL0 + 0.66):                                                                 # drain cocks
        m.tube(V((x, y, AZ - 0.25)), V((x, y, AZ - 0.33)), 0.018, 'iron', 8); m.box(V((x, y, AZ - 0.30)), (0.05, 0.04, 0.03), 'iron')
    part(f'piston_{s}', pivot=X, explode=(0.9, side * 0.9, 0)).stl('piston', 'steel', at(X + V((0.85, 0, 0))))
    part(f'crosshead_{s}', pivot=X, explode=(0.4, side * 0.9, -0.2)).stl('crosshead', 'steel', at(X))
    vc = V((CYL0 + 0.375, y, VZ))
    v = part(f'valve_{s}', pivot=vc, explode=(0.6, side * 0.9, 0.3)); v.stl('valve', 'brass', at(vc))

    mp = Yv(pin(0, side), side * 0.95)
    m = part(f'connecting_rod_{s}', pivot=mp, axis=Y, explode=(0.2, side * 0.6, -0.15))
    rod(m, mp, Yv(X, side * 0.95), 0.16, 0.11, 0.05, 'steel', [(mp, 0.11), (Yv(X, side * 0.95), 0.075)], flute=True,
        cups=[(mp, 0.11), (Yv(X, side * 0.95), 0.075)])
    a, b = Yv(pin(AXLES[0], side), side * 0.875), Yv(pin(AXLES[2], side), side * 0.875)
    m = part(f'coupling_rod_{s}', pivot=Yv(pin(0, side), side * 0.875), explode=(0, side * 0.45, -0.1))
    mid = Yv(pin(0, side), side * 0.875)
    for p0, p1, ra, rb in ((a, mid, 0.09, 0.1), (mid, b, 0.1, 0.09)):
        rod(m, p0, p1, 0.11, 0.11, 0.045, 'steel', [(p0, ra), (p1, rb)], flute=True)
    for c, r in ((a, 0.09), (mid, 0.1), (b, 0.09)): oil_cup(m, c, r, 'steel')

    # Walschaerts gear, in the plane |y| = GY
    e = Yv(pin(0, side, 0.13, -pi / 2 * side), side * GY)
    lk = Yv(LINK, side * GY); tail = lk + V((0, 0, -0.26))
    m = part(f'eccentric_rod_{s}', pivot=e, axis=Y, explode=(0, side * 0.7, -0.3))
    rod(m, e, tail, 0.07, 0.06, 0.035, 'steel', [(e, 0.06), (tail, 0.045)])
    m = part(f'expansion_link_{s}', pivot=lk, axis=Y, explode=(0, side * 0.7, 0.3))
    R = 1.0; cen = lk + V((R, 0, 0))                                       # slot arc centred on the radius rod's far end
    arc = [cen + V((-R * cos(t), 0, R * sin(t))) for t in [(-0.27 + 0.54 * i / 8) for i in range(9)]]
    for off in (-0.035, 0.035): m.sweep([p + V((off, 0, 0)) for p in arc], 0.018, 'steel', 8)
    m.disc(lk, Y, 0.05, 0.12, 'steel', 16); m.disc(arc[0] + V((0, 0, 0)), Y, 0.04, 0.06, 'steel', 12)
    die = lk + V((0, 0, 0.12)); top = V((xc - 0.30, side * GY, VZ + 0.06))
    m = part(f'radius_rod_{s}', pivot=die, axis=Y, explode=(0, side * 0.8, 0.45))
    rod(m, die, top, 0.06, 0.06, 0.03, 'steel', [(die, 0.05), (top, 0.04)])
    low = V((top.x, side * GY, AZ - 0.25))
    m = part(f'combination_lever_{s}', pivot=V((top.x, side * GY, VZ)), axis=Y, explode=(0.1, side * 0.85, 0.2))
    rod(m, top, low, 0.07, 0.05, 0.03, 'steel', [(top, 0.04), (V((top.x, side * GY, VZ)), 0.035), (low, 0.035)])
    m.tube(V((top.x, side * GY, VZ)), V((CYL0 + 0.375 - 0.75, side * CY, VZ)), 0.02, 'steel', 8)     # valve spindle crosshead link
    drop = V((xc, side * GY, AZ - 0.25))
    m = part(f'union_link_{s}', pivot=drop, axis=Y, explode=(0.1, side * 0.85, -0.35))
    rod(m, drop, low, 0.05, 0.05, 0.03, 'steel', [(drop, 0.035), (low, 0.035)])
    m.box(V((xc, side * (CY + GY) / 2, AZ - 0.13)), (0.06, 0.08, 0.26), 'steel')                       # crosshead drop arm

def frames():
    m = part('frames', explode=(0, 0, 0))
    for side in (1, -1):
        m.box(V((0.36, side * 0.60, 0.72)), (6.14, 0.03, 0.62), 'paint')
        for x in AXLES:                                                                                  # axleboxes
            m.box(V((x, side * 0.63, AZ)), (0.30, 0.06, 0.34), 'iron')
        m.box(V((LINK.x, side * (GY - 0.08), LINK.z)), (0.12, 0.08, 0.5), 'paint')                     # motion bracket
        for z in (AZ - 0.12, AZ + 0.12): m.tube(V((CYL0 - 1.04, side * CY, z)), V((CYL0 - 1.04, side * 0.62, z)), 0.02, 'paint', 8)   # slide bar hangers
    for x in BEAMS:                                                                                     # buffer beams up to the footplate
        m.box(V((x, 0, 1.07)), (0.12, 2.4, 0.58), 'red')
        sx = 1 if x > 0 else -1; face = x + sx * 0.06
        for side in (1, -1): buffer(m, V((face, side * 0.87, 1.0)), sx)
        coupling(m, V((face, 0, 1.0)), sx)
        for y in (-0.6, 0, 0.6): m.box(V((face + sx * 0.03, y, 1.30)), (0.06, 0.05, 0.12), 'iron')        # lamp irons
        m.sweep([V((face + sx * 0.02, 0.42, 0.86)), V((face + sx * 0.08, 0.42, 0.86)), V((face + sx * 0.08, 0.42, 1.28)),
                 V((face + sx * 0.14, 0.42, 1.32))], 0.035, 'iron', 10)                                    # brake pipe standpipe
        m.sweep([V((face + sx * 0.14, 0.42, 1.32)), V((face + sx * 0.24, 0.40, 1.15)), V((face + sx * 0.26, 0.36, 0.86))],
                0.045, 'paint', 10)                                                                          # its hose, hung up
        m.disc(V((face + sx * 0.26, 0.36, 0.84)), Z, 0.06, 0.05, 'iron', 12)
        for side in (1, -1):                                                                                 # guard irons ahead of the end wheels
            gx = sx * 2.22
            m.sweep([V((gx, side * 0.6, 0.48)), V((gx, side * 0.7, 0.30)), V((gx, side * 0.76, 0.07))], 0.018, 'paint', 8)
    m.tube(V((-0.2, -0.55, 1.08)), V((-0.2, 0.55, 1.08)), 0.03, 'paint', 8)
    for side in (1, -1):
        m.box(V(((BEAMS[0] + BEAMS[1]) / 2, side * 1.368, 1.28)), (BEAMS[0] - BEAMS[1] - 0.12, 0.012, 0.11), 'paint')   # valance
        step(m, -2.35, side); step(m, 3.29, side, w=0.28)
        for x in AXLES: brake(m, x, side)
        m.tube(V((AXLES[0] - 0.63, side * 0.40, 0.42)), V((AXLES[2] - 0.63, side * 0.40, 0.42)), 0.02, 'iron', 8)   # pull rods
        m.box(V((0.70, side * 0.71, 1.14)), (0.24, 0.14, 0.18), 'paint')                                    # sandbox, its pipe to the rail
        m.sweep([V((0.70, side * 0.71, 1.05)), V((0.70, side * 0.73, 0.5)), V((0.68, side * 0.765, 0.12)), V((0.66, side * 0.765, 0.06))],
                0.02, 'iron', 8)
    for x in AXLES: m.tube(V((x - 0.63, -0.79, 0.42)), V((x - 0.63, 0.79, 0.42)), 0.025, 'iron', 8)      # brake beams

def buffer(m, c, sx):
    """Long-case buffer: square flange bolted to the beam, tapered case, plunger, slightly domed head."""
    m.box(c + X * sx * 0.015, (0.03, 0.30, 0.30), 'iron')
    for dy in (-0.11, 0.11):
        for dz in (-0.11, 0.11): m.disc(c + V((sx * 0.035, dy, dz)), X, 0.018, 0.02, 'iron', 6)
    m.sweep([c + X * sx * 0.03, c + X * sx * 0.06, c + X * sx * 0.25], [0.12, 0.11, 0.085], 'iron', 20)
    m.disc(c + X * sx * 0.25, X, 0.095, 0.02, 'iron', 20)
    m.tube(c + X * sx * 0.25, c + X * sx * 0.315, 0.058, 'steel', 16)
    m.disc(c + X * sx * 0.33, X, 0.19, 0.03, 'steel', 32); m.disc(c + X * sx * 0.35, X, 0.15, 0.012, 'steel', 32)

def coupling(m, c, sx):
    """Draw hook through the beam and a screw coupling hung on it: links, screw with its handle."""
    m.box(c + V((sx * 0.07, 0, 0)), (0.14, 0.05, 0.10), 'iron')
    m.sweep(smooth([c + V((sx * 0.12, 0, 0)), c + V((sx * 0.20, 0, -0.01)), c + V((sx * 0.25, 0, 0.05)), c + V((sx * 0.23, 0, 0.12))], 3),
            [0.034] * 6 + [0.026] * 4, 'iron', 10)
    pin = c + V((sx * 0.19, 0, 0.02))
    m.tube(pin + V((0, -0.06, 0)), pin + V((0, 0.06, 0)), 0.014, 'steel', 8)
    for dy in (-0.05, 0.05): rod(m, pin + V((0, dy, 0)), pin + V((sx * 0.03, dy, -0.24)), 0.035, 0.035, 0.012, 'iron')
    sc = pin + V((sx * 0.03, 0, -0.24))
    m.tube(sc + V((-0.09, 0, 0)), sc + V((0.09, 0, 0)), 0.016, 'steel', 8)                                   # the screw
    m.box(sc, (0.06, 0.11, 0.05), 'iron')
    m.sweep([sc, sc + V((0, 0.03, -0.12)), sc + V((0, 0.03, -0.20))], 0.012, 'iron', 6); m.disc(sc + V((0, 0.03, -0.22)), Z, 0.03, 0.04, 'iron', 10)

def step(m, x, side, w=0.34, rungs=(0.95, 0.62), top=1.27):
    """Open step hung under the footplate edge: two flat-bar hangers, two treads with non-slip ribs and an upturned lip."""
    y0, y1 = side * 1.16, side * 1.38; yc = (y0 + y1) / 2; h = top - rungs[-1] + 0.03
    for dx in (-w / 2, w / 2):
        m.box(V((x + dx, side * 1.35, top - h / 2)), (0.014, 0.06, h), 'paint')
        for z in rungs: m.box(V((x + dx, yc, z - 0.02)), (0.014, 0.22, 0.05), 'paint')                  # tread brackets
    for z in rungs:
        m.box(V((x, yc, z)), (w, 0.22, 0.014), 'iron'); m.box(V((x, y1 - side * 0.006, z + 0.018)), (w, 0.012, 0.05), 'iron')
        for k in range(4): m.box(V((x, y0 + side * (0.035 + k * 0.045), z + 0.011)), (w - 0.03, 0.012, 0.008), 'iron')

def brake(m, x, side):
    """Cast-iron block on the back of the tread, its hanger from a frame bracket."""
    c = V((x, side * 0.77, AZ))
    arc_block(m, c, 0.607, 0.66, pi - 0.30, pi + 0.30, 0.09, 'iron')
    m.box(c + V((-0.67, 0, 0)), (0.04, 0.05, 0.16), 'iron')
    m.tube(c + V((-0.68, 0, 0.02)), V((x - 0.70, side * 0.77, 1.06)), 0.018, 'iron', 8)
    m.box(V((x - 0.70, side * 0.69, 1.06)), (0.06, 0.18, 0.06), 'paint')
    m.tube(c + V((-0.62, 0, -0.19)), V((x - 0.63, side * 0.77, 0.42)), 0.02, 'iron', 8)

def boiler():
    m = part('firebox', explode=(-0.6, 0, 0.6))
    fb = V((-1.85, 0, 1.55))
    m.box(fb + V((0, 0, 0.25)), (1.2, 1.0, 0.04), 'copper')                                                # crown sheet
    for side in (1, -1): m.box(fb + V((0, side * 0.5, -0.1)), (1.2, 0.04, 0.70), 'copper')
    m.box(fb + V((-0.6, 0, -0.1)), (0.04, 1.0, 0.70), 'copper'); m.box(fb + V((0.6, 0, -0.1)), (0.04, 1.0, 0.70), 'copper')  # door plate, tube plate
    m.box(fb + V((0, 0, -0.44)), (1.15, 0.95, 0.03), 'iron')                                              # grate
    m.box(fb + V((0, 0, -0.38)), (1.0, 0.8, 0.08), 'glow')                                                # fire bed
    m.disc(fb + V((-0.62, 0, 0.0)), V((1, 0, 0)), 0.17, 0.03, 'iron', 16)                                 # fire door
    m = part('boiler_tubes', explode=(0, 0, 1.0))
    for k in range(-3, 4):
        for j in range(-2, 3):
            if k * k + j * j * 2.2 > 11: continue
            y, z = k * 0.085, BOILER_Z + j * 0.11 - 0.05
            m.tube(V((-1.23, y, z)), V((TUBE_X - 0.02, y, z)), 0.026, 'steel', 8, caps=False)
    for k in (-1, 1): m.tube(V((-1.23, k * 0.17, BOILER_Z + 0.27)), V((TUBE_X - 0.02, k * 0.17, BOILER_Z + 0.27)), 0.06, 'steel', 12, caps=False)   # superheater flues
    for x in (-1.25, TUBE_X): m.disc(V((x, 0, BOILER_Z)), V((1, 0, 0)), BOILER_R - 0.03, 0.025, 'copper' if x < 0 else 'iron', 32)   # tube plates
    m = part('steam_pipes', explode=(0.2, 0, 1.4))
    dome = V((0.75, 0, BOILER_Z + 0.55))
    m.tube(dome, dome + V((0, 0, -0.25)), 0.06, 'brass', 12)                                              # regulator head
    m.sweep([dome + V((0, 0, -0.25)), V((0.9, 0, BOILER_Z + 0.42)), V((SB_X - 0.2, 0, BOILER_Z + 0.42))], 0.05, 'steel', 12)   # main steam pipe
    hdr = V((SB_X - 0.1, 0, BOILER_Z + 0.2))
    m.sweep([V((SB_X - 0.2, 0, BOILER_Z + 0.42)), hdr], 0.05, 'steel', 12)
    for side in (1, -1):                                                                                   # outside steam pipes to the valve chests
        m.sweep([hdr, V((SB_X, side * 0.45, BOILER_Z - 0.2)), V((SB_X, side * 0.80, 1.25)), V((CYL0 + 0.375, side * CY, VZ + 0.16))], 0.055, 'steel', 12)
    m = part('blastpipe', explode=(0.6, 0, 1.6))
    bp = V((SB_X, 0, BOILER_Z - 0.45))
    m.sweep([bp, bp + V((0, 0, 0.55))], [0.10, 0.06], 'iron', 16)
    for side in (1, -1): m.sweep([V((CYL0 + 0.375, side * CY, VZ - 0.05)), V((SB_X, side * 0.55, 1.0)), bp], 0.06, 'iron', 10)   # exhaust from the cylinders
    m.sweep([bp + V((0, 0, 0.75)), bp + V((0, 0, 1.3))], [0.12, 0.17], 'iron', 20, caps=False)           # petticoat / chimney liner

def cab_controls():
    m = part('reverser', explode=(-0.6, 0.4, 0.4))
    lever = V((-2.35, 0.55, 1.15))
    m.sweep([lever, lever + V((0.08, 0, 0.75))], [0.025, 0.015], 'steel', 8)
    m.box(lever + V((0, 0.05, 0.3)), (0.35, 0.02, 0.05), 'steel')                                           # notched quadrant
    m.sweep([lever + V((0.04, 0.02, 0.4)), V((LINK.x + 0.25, GY, LINK.z + 0.55))], 0.015, 'steel', 6)      # reach rod to the lifting arm
    m.tube(V((LINK.x + 0.25, -GY, LINK.z + 0.55)), V((LINK.x + 0.25, GY, LINK.z + 0.55)), 0.025, 'steel', 10)   # weigh shaft
    m = part('regulator', explode=(-0.6, -0.3, 0.6))
    rg = V((-2.45, 0, BOILER_Z + 0.1))
    m.tube(rg, rg + V((0.2, 0, 0)), 0.03, 'brass', 10); m.box(rg + V((-0.02, 0.18, 0.05)), (0.03, 0.36, 0.05), 'brass')

def rails():
    m = part('track', explode=(0, 0, 0))
    half = [(0.07, -0.16), (0.07, -0.15), (0.012, -0.135), (0.009, -0.052), (0.035, -0.042), (0.035, -0.01), (0.027, 0)]   # flat-bottom rail
    prof = [(-y, z) for y, z in half[::-1]] + half
    for side in (1, -1):
        y = side * (0.7175 + 0.036)
        prism(m, [(y + dy, z) for dy, z in prof[::-1]], -4.5, 4.5, 'steel')
        for k in range(13):                                                                          # base plates and clips
            x = -4.2 + k * 0.7
            m.box(V((x, y, -0.168)), (0.18, 0.30, 0.016), 'iron')
            for e in (1, -1): m.box(V((x, y + e * 0.095, -0.148)), (0.06, 0.04, 0.03), 'iron')
    for k in range(13): m.box(V((-4.2 + k * 0.7, 0, -0.256)), (0.25, 2.6, 0.16), 'wood')

# ---------------------------------------------------------------- Tripo shell
TRIPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tripo', 'body.glb')
SHELL_TRIS, TEX = 22000, 2048
SHELL_Y = 0.88            # Tripo's loco is wider than its own wheel gauge: narrow it so the tanks sit over the CAD cylinders
CUT_Z, PLATE_Z = 1.24, 1.39                         # underside and top of the footplate
SHELL_BC = (2.10, 0.92)                             # boiler cladding axis height and radius before the y squeeze

def shell_material(img):
    img.scale(TEX, TEX); img.file_format = 'JPEG'
    m = bpy.data.materials.new('shell'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Metallic'].default_value = 0.15; b.inputs['Roughness'].default_value = 0.55       # satin loco paint
    return m

def panel(c, n):
    x, y, z = c; ay = abs(y) / SHELL_Y; s = 'l' if y > 0 else 'r'
    if z < PLATE_Z + 0.02: return 'footplate'
    if x < -0.98: return 'cab_roof' if z > 3.33 and abs(n.x) < 0.7 else 'cab' if not (x > -1.62 and ay > 1.40 and z < 2.45) else f'tank_{s}'
    if x > 2.38:
        if x > 3.2 and ay ** 2 + (z - 2.2) ** 2 < 0.62 ** 2 and n.x > 0.2: return 'smokebox_door'
        return 'smokebox' if ay < 0.95 else f'tank_{s}' if x < 2.46 else 'footplate'
    zc, rc = SHELL_BC; rr = (ay ** 2 + (z - zc) ** 2) ** 0.5
    radial = V((0, y / SHELL_Y, z - zc)).normalized().dot(V((0, n.y * SHELL_Y, n.z)).normalized())
    if z > 2.62 or ay < 0.78 or (abs(rr - rc) < 0.06 and radial > 0.9): return 'boiler_cladding'
    return f'tank_{s}'

def patch_cab(me, img, faces):
    """Tripo's cab back sheet carries black triangles, a dark door panel and half-black window panes: give those faces one flat
    texel each (back sheet: a mid red from the sheet itself, panes: the pane's own grey; elsewhere black specks: the nearest red)."""
    import numpy as np
    from mathutils.kdtree import KDTree
    w, h = img.size; px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    uv = me.uv_layers.active.data
    def col(f):
        u = sum((uv[l].uv for l in f.loop_indices), V((0, 0))) / f.loop_total
        return px[min(h - 1, int(u.y % 1 * h)), min(w - 1, int(u.x % 1 * w)), :3], u
    red, back, panes, specks = [], [], {}, []
    for i in faces:
        f = me.polygons[i]; (r, g, b), u = col(f); c = f.center
        if c.x < -2.55 and abs(f.normal.x) > 0.5:
            if 0.48 < abs(c.y) < 1.02 and 2.70 < c.z < 3.45:
                if abs(f.normal.x) > 0.9 and abs(c.x + 2.683) < 0.01: panes.setdefault(c.y > 0, []).append((f, max(r, g, b), u))
            else: back.append((f, r if r > 2.5 * g else 0, u))
        elif r > 2.5 * g and r > 0.08: red.append((c, u))
        elif max(r, g, b) < 0.012: specks.append(f)
    def flat(f, u):
        for l in f.loop_indices: uv[l].uv = u
    reds = sorted((r, tuple(u)) for f, r, u in back if r > 0)
    u_red = V(reds[len(reds) // 2][1])
    for f, _, _ in back: flat(f, u_red)
    for pane in panes.values():
        grey = [u for f, v, u in pane if 0.012 < v < 0.25]
        if grey:
            for f, _, _ in pane: flat(f, grey[0])
    kd = KDTree(len(red))
    for j, (c, _) in enumerate(red): kd.insert(c, j)
    kd.balance()
    for f in specks: flat(f, red[kd.find(f.center)[1]][1])
    print('cab texture patched:', len(back), 'back sheet,', sum(map(len, panes.values())), 'pane,', len(specks), 'speck faces')

HINGES = {   # id -> (pivot, axis, explode); the door and roof swing about their pivot, the rest only slides
    'footplate': (None, None, (0, 0, 0)), 'boiler_cladding': (None, None, (0, 0, 1.6)),
    'smokebox': (None, None, (1.0, 0, 1.1)), 'smokebox_door': (V((3.25, -0.62, 2.12)), V((0, 0, 1)), (1.9, -0.4, 1.1)),
    'tank_l': (None, None, (0, 1.4, 0.3)), 'tank_r': (None, None, (0, -1.4, 0.3)),
    'cab': (None, None, (-1.3, 0, 0.6)), 'cab_roof': (V((-1.0, 0, 3.45)), Y, (-1.4, 0, 1.8))}

def reused_shell(path):
    """Without the Tripo body (it stays out of git): take the shell parts as they are from a published model, decoded first
    with tools/decode-glb.mjs (the bpy wheel's glTF importer has no meshopt decoder). They were bevelled once already."""
    before, mats = set(bpy.data.objects), set(bpy.data.materials)
    bpy.ops.import_scene.gltf(filepath=path); bpy.context.view_layer.update()
    new = {o.name: o for o in bpy.data.objects if o not in before}
    for pid, (piv, ax, ex) in HINGES.items():
        o = new[pid]; me = o.data.copy(); me.transform(o.matrix_world)
        m = part(pid, pivot=piv, axis=ax, explode=ex); m.mats = ['shell']; m.bm.from_mesh(me)
        for f in m.bm.faces: f.material_index = 0; f.smooth = True
        bpy.data.meshes.remove(me)
    for o in new.values(): bpy.data.objects.remove(o)
    for mt in list(bpy.data.materials):
        if mt not in mats and mt.name != 'shell': bpy.data.materials.remove(mt)
    common.SHELLS.add('shell'); print('shell reused from', path)

def tripo_body():
    if not os.path.exists(TRIPO):
        if '--shell' in sys.argv: return reused_shell(sys.argv[sys.argv.index('--shell') + 1])
        print('no Tripo body, shell skipped:', TRIPO); return
    bpy.ops.import_scene.gltf(filepath=TRIPO)
    ob = next(o for o in bpy.context.selected_objects if o.type == 'MESH'); me = ob.data
    me.transform(Matrix.Rotation(pi / 2, 4, 'Z') @ ob.matrix_world)            # Tripo front is -y: turn it to +x
    for o in list(bpy.context.selected_objects):
        if o != ob: bpy.data.objects.remove(o)
    ob.parent = None; ob.matrix_world = Matrix.Identity(4)
    zs = [v.co.z for v in me.vertices]; z0 = min(zs); h = max(zs) - z0
    low = sorted(v.co.x for v in me.vertices if v.co.z < z0 + 0.01 * h)       # wheel treads: three clusters along x
    cl = [[low[0]]]
    for x in low[1:]: (cl[-1].append(x) if x - cl[-1][-1] < 0.03 else cl.append([x]))
    assert len(cl) == 3, f'expected 3 wheel clusters, got {len(cl)}'
    xf, xr = sum(cl[-1]) / len(cl[-1]), sum(cl[0]) / len(cl[0])
    k = (AXLES[0] - AXLES[2]) / (xf - xr); ym = sum(v.co.y for v in me.vertices) / len(me.vertices)
    me.transform(Matrix.Diagonal(V((k, k * SHELL_Y, k, 1))) @ Matrix.Translation(V((-(xf + xr) / 2, -ym, -z0))))
    xs = [v.co.x for v in me.vertices]
    print(f'Tripo body: scale {k:.3f}, length {max(xs) - min(xs):.2f} m')
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
    def below(f):      # wheels, motion, frames, cylinders and buffer beams: the CAD has its own
        c = f.calc_center_median()
        return c.z < CUT_Z or (c.z < PLATE_Z - 0.03 and (c.x > BEAMS[0] - 0.08 or c.x < BEAMS[1] + 0.08))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if below(f)], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    new = bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=8)['faces']    # Tripo's pin holes (cab back)
    uvl = bm.loops.layers.uv.active
    for f in new:      # a filled hole takes the texel its neighbour shows
        nb = next((g for e in f.edges for g in e.link_faces if g not in new), None)
        if nb is None: continue
        u = sum((l[uvl].uv for l in nb.loops), V((0, 0))) / len(nb.loops)
        for l in f.loops: l[uvl].uv = u
    print('holes filled', len(new))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)      # some Tripo triangles are wound backwards and shade black
    bm.to_mesh(me); bm.free()
    dec = ob.modifiers.new('d', 'DECIMATE'); dec.ratio = min(1, SHELL_TRIS / len(me.polygons)); dec.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='d')
    bm = bmesh.new(); bm.from_mesh(me); flipped = 0
    for f in bm.faces:   # a triangle wound against its neighbours shades black here and vanishes under back-face culling in the app
        around = sum((g.normal * g.calc_area() for v in f.verts for g in v.link_faces if g is not f), V((0, 0, 0)))
        if f.normal.dot(around) < 0: f.normal_flip(); flipped += 1
    def ghost(f):      # loose big triangles 6 cm behind the cab back sheet, in an X: they shade it in stripes
        c = f.calc_center_median()
        return c.x < -2.72 and abs(f.normal.x) > 0.9 and f.calc_area() > 0.01 and 1.45 < c.z < 3.5 and abs(c.y) < 1.0
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if ghost(f)], context='FACES')
    bm.to_mesh(me); bm.free(); print('flipped', flipped)
    img = next(n.image for n in me.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE')
    me.materials[0] = shell_material(img)
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    groups = {}
    for f in me.polygons: groups.setdefault(panel(f.center, f.normal), []).append(f.index)
    patch_cab(me, img, groups['cab'])
    for pid, faces in sorted(groups.items()):
        piv, ax, ex = HINGES[pid]
        m = part(pid, pivot=piv, axis=ax, explode=ex); m.mats = ['shell']
        keep = set(faces); b2 = bmesh.new(); b2.from_mesh(me)
        bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.index not in keep], context='FACES')
        m.bm.free(); m.bm = b2
        print(pid, len(faces), 'faces')
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

def grab_rails():
    """Handrails either side of the cab entrance, over the steps, stood off the cab side."""
    if 'cab' not in PARTS: return
    m = PARTS['cab']['m']
    for side in (1, -1):
        for x in (-2.18, -2.52):
            y = side * 1.166
            m.tube(V((x, y, 1.45)), V((x, y, 2.55)), 0.014, 'steel', 8); m.disc(V((x, y, 1.45)), Z, 0.02, 0.02, 'steel', 8)
            for z in (1.55, 2.45): m.tube(V((x, side * 1.09, z)), V((x, y, z)), 0.01, 'steel', 6)

def build():
    wheelsets(); frames(); boiler(); cab_controls(); rails(); tripo_body(); grab_rails()
    for side in (1, -1): motion(side)

VIEWS = {'left_34': ((5.4, 5.6, 2.6), (0.4, 0, 1.0), 35), 'right_side': ((0.4, -8.5, 1.3), (0.4, 0, 1.0), 35),
         'motion_r': ((1.3, -3.2, 1.0), (1.2, -1.0, 0.75), 35), 'front': ((7.5, 1.5, 2.0), (2.5, 0, 1.2), 40)}
if '--explode' in sys.argv:   # room for the shell parts flying off
    VIEWS = {'x_left_34': ((10.5, 10.0, 6.5), (0.2, 0, 2.0), 32), 'x_right_34': ((-7.5, -11.0, 6.0), (0.0, 0, 2.0), 32)}
if '--ortho' in sys.argv:   # fitting views: near-orthographic side, front, top and back
    VIEWS = {'o_side': ((0.3, -160, 1.8), (0.3, 0, 1.8), 600), 'o_front': ((160, 0, 1.8), (0, 0, 1.8), 600),
             'o_top': ((0.3, 0, 160), (0.3, 0.001, 0), 600), 'o_back': ((-160, 0, 1.8), (0, 0, 1.8), 600),
             'rear_34': ((-6.5, -4.0, 3.2), (-2.4, 0, 2.2), 45)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS.get('left_34'))
