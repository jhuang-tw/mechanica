# Mixed-reality headset exhibit (generic standalone headset of the Quest 3 generation, no logos), built from scratch for Mechanica.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/quest/build.py -- public/exhibits/quest [--preview]
# A teaching reconstruction of the published teardown layout: white front cover with three dark sensor windows, colour and tracking
# cameras plus a depth sensor behind it, mainboard with SoC under a finned heatsink and a blower fan, battery between the board and
# the optics, two LCDs behind pancake lenses on an IPD rail adjusted by a wheel underneath, speakers in the side arms, soft strap.
# Modelled in millimetres in the headset frame (x = front, away from the face; y = wearer's left; z = up), scaled to metres at the end.
# Glb: real size (184 mm wide). The eye carriages slide along glTF z (wearer's right = +z); the fan rotor and IPD wheel spin.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths
import common
from math import exp

X, Zv = V((1, 0, 0)), V((0, 0, 1))
IPD, EYE_Z = 64.0, 2.0
def EYE(s): return V((0, s * IPD / 2, EYE_Z))

common.MATS.update({   # base colour (linear), metallic, roughness
    'shell':  ((0.80, 0.80, 0.80), 0.0, 0.45),
    'gloss':  ((0.01, 0.01, 0.012), 0.2, 0.08),
    'dark':   ((0.03, 0.03, 0.035), 0.0, 0.55),
    'grey':   ((0.25, 0.26, 0.28), 0.1, 0.5),
    'metal':  ((0.55, 0.56, 0.58), 1.0, 0.32),
    'alu':    ((0.70, 0.71, 0.73), 1.0, 0.30),
    'copper': ((0.80, 0.38, 0.22), 1.0, 0.30),
    'pcb':    ((0.03, 0.12, 0.06), 0.0, 0.45),
    'chip':   ((0.02, 0.02, 0.025), 0.3, 0.35),
    'gold':   ((0.85, 0.62, 0.25), 1.0, 0.25),
    'batt':   ((0.05, 0.10, 0.25), 0.0, 0.40),
    'lens':   ((0.16, 0.19, 0.22), 0.1, 0.04),
    'lcd':    ((0.02, 0.03, 0.05), 0.5, 0.10),
    'glass':  ((0.02, 0.02, 0.05), 0.8, 0.05),
    'foam':   ((0.20, 0.20, 0.21), 0.0, 0.90),
    'fabric': ((0.10, 0.10, 0.11), 0.0, 0.95),
    'flex':   ((0.55, 0.30, 0.05), 0.0, 0.40),
})

# ---------------------------------------------------------------- shapes (y, z) in mm
def outline(a, b, n=72, notch=0.0, nw=22.0, e=0.55):
    """Squircle face outline, half-width a, half-height b, with a nose notch pushed up at the bottom middle."""
    pts = []
    for i in range(n):
        t = TAU * i / n; c, s = cos(t), sin(t)
        y = a * (abs(c) ** e) * (1 if c >= 0 else -1); z = b * (abs(s) ** e) * (1 if s >= 0 else -1)
        if s < 0: z += notch * exp(-(y / nw) ** 2) * (-s)
        pts.append((y, z))
    return pts

def rrect(w, h, r, n=6):
    pts = []
    for cy, cz, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        pts += [(cy + r * cos(radians(a0 + 90 * k / n)), cz + r * sin(radians(a0 + 90 * k / n))) for k in range(n + 1)]
    return pts

def prism(m, pts, x0, x1, mat, off=(0, 0)):
    """Extrude a (y, z) outline along x; x0 / x1 may be numbers or functions of (y, z)."""
    f0 = x0 if callable(x0) else (lambda y, z: x0); f1 = x1 if callable(x1) else (lambda y, z: x1)
    P = [(y + off[0], z + off[1]) for y, z in pts]
    a = [m.bm.verts.new(V((f0(y, z), y, z))) for y, z in P]; b = [m.bm.verts.new(V((f1(y, z), y, z))) for y, z in P]
    m.face(a, mat); m.face(b[::-1], mat); m.bridge(b, a, mat)

def loft(m, stations, mat, base, cap=None):
    """Rings of `base` outline, each (x or f(y,z), scale); bridged in order; cap = material for a centre fan on the last ring."""
    rings = []
    for x, s in stations:
        rings.append([m.bm.verts.new(V((x(y * s, z * s) if callable(x) else x, y * s, z * s))) for y, z in base])
    for a, b in zip(rings, rings[1:]): m.bridge(a, b, mat)
    if cap:
        c = rings[-1]; ctr = m.bm.verts.new(V((stations[-1][0](0, 0) + 0.3 if callable(stations[-1][0]) else stations[-1][0], 0, 0)))
        for i in range(len(c)): m.face([c[i], c[(i + 1) % len(c)], ctr], cap)
    return rings

def smooth(pts, n=6, closed=False):
    """Catmull-Rom resample of a control polyline."""
    P = pts + pts[:3] if closed else [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(len(P) - 3):
        p0, p1, p2, p3 = P[i:i + 4]
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    return out if closed else out + [pts[-1]]

def holed_plate(m, outer, holes, x0, x1, mat):
    """Flat plate between x0 and x1 with an outer (y, z) outline and through-holes (each a (y, z) outline)."""
    def loop(pts, x): return [m.bm.verts.new(V((x, y, z))) for y, z in pts]
    rings = [(loop(outer, x0), loop(outer, x1))] + [(loop(h, x0), loop(h, x1)) for h in holes]
    for x, k, up in ((x0, 0, False), (x1, 1, True)):
        es = []
        for r in rings:
            vs = r[k]; es += [m.bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
        fs = bmesh.ops.triangle_fill(m.bm, use_beauty=True, use_dissolve=True, edges=es, normal=X if up else -X)['geom']
        for f in fs:
            if isinstance(f, bmesh.types.BMFace):
                f.material_index = m.mi(mat); f.smooth = True
                if (f.normal.x > 0) != up: f.normal_flip()
    m.bridge(rings[0][1], rings[0][0], mat)
    for a, b in rings[1:]: m.bridge(a, b, mat)

def band(m, pts, wdir, w, t, mat):
    """Flat strap along pts: width w along wdir (kept square to the path), thickness t."""
    rings = []
    for i, p in enumerate(pts):
        tg = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = (wdir - tg * wdir.dot(tg)).normalized(); b = tg.cross(a)
        rings.append([m.bm.verts.new(p + a * sa * w / 2 + b * sb * t / 2) for sa, sb in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    for r0, r1 in zip(rings, rings[1:]): m.bridge(r0, r1, mat)
    m.face(rings[0][::-1], mat); m.face(rings[-1], mat)

FRONT = lambda y, z: 33 - 9 * (y / 92) ** 2 - 3 * (z / 49) ** 2      # the front cover curves back towards the sides
OUT = outline(92, 49, notch=20)
INN = outline(89.8, 46.8, notch=19)

# ---------------------------------------------------------------- parts
def shell():
    v = part('front_cover', explode=(0.09, 0, 0))
    o = loft(v, [(12, 1), (lambda y, z: FRONT(y, z) - 6, 1), (lambda y, z: FRONT(y, z) - 1.6, 0.965), (FRONT, 0.88), (FRONT, 0.62), (FRONT, 0.32)], 'shell', OUT, cap='shell')
    i = loft(v, [(12, 1), (lambda y, z: FRONT(y * 1.02, z * 1.04) - 8.2, 1), (lambda y, z: FRONT(y * 1.02, z * 1.04) - 3.6, 0.95), (lambda y, z: FRONT(y, z) - 2.4, 0.6)], 'grey', INN)
    v.bridge(i[0], o[0], 'shell')
    for y, w, h, z in ((52, 21, 54, 0), (-52, 21, 54, 0), (0, 13, 30, -6)):                     # dark glossy sensor windows
        prism(v, rrect(w, h, w / 2 - 0.01, 8), lambda Y, Z: FRONT(Y, Z) - 1.0, lambda Y, Z: FRONT(Y, Z) + 1.6, 'gloss', off=(y, z))
    for s in (1, -1):                                                                                # camera glass seen through each window
        for z, r0 in ((-11, 4.6), (13, 4.0)):
            c = V((FRONT(s * 52, z) + 1.7, s * 52, z))
            v.disc(c, X, r0 + 1.1, 0.25, 'grey', 32, r_in=r0); v.disc(c, X, r0, 0.2, 'glass', 32)
        for y, z in ((s * 76, -40.3),):                                                            # downward tracking camera windows
            v.disc(V((16, y, z)), V((0, s * 0.45, -1)), 4.2, 1.2, 'gloss', 24)
    for z, r0 in ((-1, 2.9), (-11, 2.9)):                                                            # depth sensor and its IR projector
        c = V((FRONT(0, z) + 1.7, 0, z)); v.disc(c, X, r0 + 0.9, 0.25, 'grey', 24, r_in=r0); v.disc(c, X, r0, 0.2, 'glass', 24)
    v.disc(V((FRONT(0, 7) + 1.7, 0, 7)), X, 1.1, 0.2, 'glass', 12)                                   # flood illuminator
    h = part('housing', explode=(-0.02, 0, 0))
    loft(h, [(-22, 0.985), (-20.5, 1), (12, 1)], 'shell', OUT)
    loft(h, [(12, 1), (-20, 1)], 'grey', INN)
    hole = [(y, z + EYE_Z) for y, z in rrect(50, 45, 22.4, 10)]                                       # oval: the lenses slide with the IPD
    holed_plate(h, outline(90, 47.5, notch=20, n=72), [[(y + s * IPD / 2, z) for y, z in hole] for s in (1, -1)], -24, -21.6, 'dark')
    for k in range(4): h.disc(V((-14, -30 + 20 * k, -46.6)), Zv, 0.7, 1.4, 'dark', 10)               # microphone holes underneath
    for k in range(17): h.box(V((4, -40 + 5 * k, 48.6 - 4 * ((-40 + 5 * k) / 92) ** 2)), (12, 1.4, 1.6), 'dark')   # top intake vents
    for k in range(11): h.box(V((6, 48 + 3 * k, -46)), (9, 1.2, 1.6), 'dark')                        # exhaust vents underneath

def electronics():
    mf = part('midframe', explode=(0.05, 0, 0.0))
    prism(mf, outline(80, 38, notch=14, n=64), 7, 8.2, 'metal')
    for z in (-6, 24): mf.box(V((8.9, 0, z)), (1.4, 120, 1.6), 'metal')
    T = 10.4
    bd = part('mainboard', explode=(0.06, 0, 0.0))
    prism(bd, outline(66, 30, n=64, notch=12, nw=16, e=0.3), 9.2, T, 'pcb')
    for y, z in ((-55, -8), (-48, 18), (40, 20), (56, -6), (-20, -18), (12, -20)):                   # board-to-board connectors
        bd.box(V((T + 0.65, y, z)), (1.3, 6.5, 3.2), 'dark'); bd.box(V((T + 1.35, y, z)), (0.2, 5.5, 2.2), 'gold')
    for k in range(8): bd.box(V((T + 0.4, -30 + 9 * k, -22 + 4 * (k % 2))), (0.8, 2.6, 2.6), 'chip')
    for y, z, w, hh in ((-44, 4, 14, 16), (28, -12, 16, 9), (54, 14, 10, 9)):                         # RF / power shield cans
        bd.box(V((T + 0.75, y, z)), (1.5, w, hh), 'metal')
    import random; rnd = random.Random(3)
    for k in range(70):                                                                               # capacitors and resistors
        y, z = rnd.uniform(-60, 60), rnd.uniform(-24, 26)
        if abs(y) < 32 and -6 < z < 16 or abs(y + 44) < 8 and abs(z - 4) < 9: continue
        bd.box(V((T + 0.3, y, z)), (0.6, rnd.choice((1.0, 1.6)), 0.8), 'chip')
    for y, z in ((-62, 12), (62, 8), (-30, 26), (30, 26), (0, -24)): bd.disc(V((T + 0.4, y, z)), X, 2.2, 0.8, 'gold', 16, r_in=1.1)
    soc = part('soc', explode=(0.075, 0, 0.0))
    soc.box(V((T + 0.5, 0, 4)), (1.0, 15, 15), 'pcb'); soc.box(V((T + 1.3, 0, 4)), (0.6, 11.5, 11.5), 'chip')
    part('memory', explode=(0.075, 0.02, 0)).box(V((T + 0.5, 18, 6)), (1.0, 12.4, 12.4), 'chip')
    part('storage', explode=(0.075, -0.02, 0)).box(V((T + 0.5, -22, 10)), (1.0, 11.5, 13), 'chip')
    wf = part('wifi', explode=(0.075, 0.035, 0)); wf.box(V((T + 0.9, 42, 4)), (1.8, 18, 13), 'metal')
    hk = part('heatsink', explode=(0.1, 0, 0.0)); HX = T + 2.1
    hk.box(V((HX + 1.0, -2, 4)), (2.0, 46, 34), 'alu')
    for k in range(21): hk.box(V((HX + 5.6, -23.5 + 43 * k / 20, 4)), (7.5, 0.6, 31), 'alu')
    hk.sweep([V((HX + 0.6, 6, -6)), V((HX + 1.2, 24, -9)), V((HX + 2.8, 42, -6)), V((HX + 3.4, 54, 2))], 1.6, 'copper', 10)    # heat pipe to the fan
    FAN = V((16.0, 56, 6))
    fn = part('fan', explode=(0.1, 0.03, 0.0))
    fn.disc(FAN, X, 17.5, 6.8, 'dark', 48, r_in=16.0); fn.disc(FAN + V((3.1, 0, 0)), X, 17.5, 0.5, 'dark', 48, r_in=8.5)
    fn.box(FAN + V((0, -14, -12)), (6.8, 11, 8), 'dark')
    r = part('fan_rotor', pivot=FAN, axis=X, explode=(0.12, 0.03, 0.0))
    r.disc(FAN, X, 5.4, 5.2, 'grey', 24)
    for k in range(27):
        a = TAU * k / 27
        r.box(FAN + V((0, cos(a) * 10.4, sin(a) * 10.4)), (4.6, 9.6, 0.3), 'grey', Matrix.Rotation(a + 0.35, 3, 'X'))
    cams = part('cameras', explode=(0.11, 0, 0))
    for s in (1, -1):
        for z, r0 in ((-11, 3.6), (13, 3.2)):                                                        # colour camera, tracking camera
            c = V((24.0, s * 52, z)); cams.box(c - V((7.4, 0, 0)), (3.2, 10, 10), 'dark')          # sensor board
            cams.disc(c - V((3.2, 0, 0)), X, r0 + 1.8, 5.2, 'dark', 24); cams.disc(c - V((0.3, 0, 0)), X, r0 + 1.2, 0.8, 'metal', 24, r_in=r0)
            cams.disc(c + V((0.2, 0, 0)), X, r0, 0.6, 'glass', 20)
        d = V((0, s * 0.45, -1)).normalized(); c = V((15, s * 76, -36))                              # lower corner tracking cameras, looking down
        cams.box(c - d * 4, (7, 8, 8), 'dark'); cams.disc(c, d, 3.8, 3.4, 'dark', 20); cams.disc(c + d * 1.8, d, 3.0, 0.4, 'glass', 16)
        cams.box(V((22.1, s * 52, 1)), (1.0, 13, 36), 'metal')
    dp = part('depth_sensor', explode=(0.11, 0, -0.01))
    dp.box(V((22.6, 0, -6)), (4, 10, 20), 'dark')
    for z in (-1, -11): dp.disc(V((24.6, 0, z)), X, 2.4, 1.2, 'glass', 16)
    bt = part('battery', explode=(0.03, 0, 0.06))
    bt.box(V((3.4, 0, 10)), (6.0, 112, 40), 'batt'); bt.box(V((6.5, 14, 10)), (0.2, 64, 24), 'grey')
    fx = part('flex_cables', explode=(0.05, 0, -0.03))
    for s in (1, -1):
        band(fx, smooth([V((21.8, s * 52, -17)), V((19, s * 46, -16)), V((14, s * 40, -14)), V((T + 1.4, s * 30, -12))], 5), Zv, 6, 0.3, 'flex')
        band(fx, smooth([V((T, s * 40, -24)), V((4, s * 45, -27)), V((-2, s * 44, -28)), V((-5.5, s * 40, -27))], 5), V((0, 1, 0)), 7, 0.3, 'flex')
        fx.box(V((T + 1.6, s * 30, -12)), (1.2, 7, 3), 'dark')

def optics():
    rail = part('ipd_rail', explode=(-0.02, 0, -0.05))
    for x in (-12.7, -6.3): rail.tube(V((x, -64, -29)), V((x, 64, -29)), 1.6, 'alu', 12)
    for y in (-64, 64): rail.box(V((-9.5, y, -29)), (12, 4, 8), 'dark')
    for s, tag in ((1, 'l'), (-1, 'r')):
        E = EYE(s)
        c = part(f'eye_carriage_{tag}', pivot=E, explode=(-0.04, s * 0.06, 0))                      # slides along y with the IPD wheel
        c.box(E + V((-9.5, 0, -27 - EYE_Z)), (7, 16, 6), 'metal')
        for x in (-12.7, -6.3): c.tube(E + V((x, -8.2, -29 - EYE_Z)), E + V((x, 8.2, -29 - EYE_Z)), 2.6, 'metal', 12)
        p = part(f'lens_{tag}', pivot=E, parent=f'eye_carriage_{tag}', explode=(-0.06, 0, 0))       # two-element pancake stack in a ribbed barrel
        p.disc(E + V((-15.3, 0, 0)), X, 24.4, 12.4, 'dark', 48, r_in=21)
        for x in (-17, -13, -9): p.disc(E + V((x, 0, 0)), X, 24.6, 0.8, 'dark', 48, r_in=23.6)
        p.disc(E + V((-18.6, 0, 0)), X, 20.4, 4.4, 'lens', 40); p.disc(E + V((-11.5, 0, 0)), X, 20.2, 3.4, 'lens', 40)
        d = part(f'display_{tag}', pivot=E, parent=f'eye_carriage_{tag}', explode=(0.03, 0, 0))
        d.box(E + V((-4.4, 0, 0)), (2.2, 50, 52), 'dark'); d.box(E + V((-5.55, 0, 1)), (0.2, 45, 47), 'lcd')
    W = V((-10, -62, -46))
    w = part('ipd_wheel', pivot=W, axis=X, explode=(0, -0.03, -0.04))
    w.disc(W, X, 6.5, 6, 'grey', 30); w.disc(W, X, 2, 7.2, 'metal', 12)
    for k in range(30): a = TAU * k / 30; w.box(W + V((0, cos(a) * 6.6, sin(a) * 6.6)), (6, 0.6, 0.6), 'grey', Matrix.Rotation(a, 3, 'X'))

def wearables():
    f = part('face_cushion', explode=(-0.08, 0, 0))
    loop = [V((-35 - 7 * (y / 77) ** 2, y, z)) for y, z in outline(77, 38, n=96, notch=15, nw=20)]
    f.sweep(loop + loop[:2], 9.5, 'foam', 14, caps=False)
    a = part('side_arms', explode=(-0.03, 0, 0.03))
    for s in (1, -1):
        band(a, smooth([V((2, s * 90.5, 1)), V((-30, s * 92.5, 0)), V((-80, s * 89, -2)), V((-112, s * 84, -3))], 6), Zv, 15, 5.5, 'shell')
        a.disc(V((2, s * 87, 1)), Y, 8.5, 7, 'grey', 32); a.disc(V((2, s * 91, 1)), Y, 3, 1.4, 'metal', 16)   # hinge and its pin
        for z in (-14.5, 8.5): a.box(V((-118, s * 83.4, z - 3)), (14, 5, 3), 'shell')                    # strap loop the head strap threads through
        a.box(V((-124, s * 82.8, -3)), (3, 5, 26), 'shell')
    sp = part('speakers', explode=(-0.03, 0, -0.03))
    for s in (1, -1):                                                                                # speaker in the arm, grille slots facing the ear
        for k in range(9):
            x = -72 - 2.6 * k; y = s * (89 + (x + 80) * 0.11)
            sp.box(V((x, y - s * 2.9, -2.2)), (1.1, 0.5, 9), 'dark')
        sp.box(V((-82.4, s * (89 + 2.4 * 0.11) - s * 1.0, -2.2)), (26, 3.4, 11), 'grey')
    b = part('buttons', explode=(0, 0.03, 0))
    rbox(b, V((4, 93.2, -6)), (11, 2.4, 4.2), 1.0, 'grey')                                          # power
    rbox(b, V((6, -62, -48.2)), (5, 16, 2.2), 0.9, 'grey')                                           # volume rocker
    for y in (-67, -57): b.disc(V((6, y, -49.4)), Zv, 1.3, 0.6, 'grey', 12)
    b.disc(V((4, 92.9, 3)), Y, 0.9, 1.2, 'glass', 10)                                               # status light
    b.box(V((-26, 96.2, -4)), (10, 2.4, 3.8), 'metal')                                              # USB-C port
    st = part('strap', explode=(-0.12, 0, 0))
    back = [V((-110, 83, -3)), V((-165, 86, -2)), V((-225, 66, -1)), V((-248, 0, 0)), V((-225, -66, -1)), V((-165, -86, -2)), V((-110, -83, -3))]
    band(st, smooth(back, 8), Zv, 26, 2.4, 'fabric')
    band(st, smooth([V((-148, 84, 8)), V((-156, 70, 78)), V((-165, 0, 116)), V((-156, -70, 78)), V((-148, -84, 8))], 8), X, 22, 2.2, 'fabric')

def build():
    shell(); electronics(); optics(); wearables()
    for p in PARTS.values():                                                                          # mm -> m
        bmesh.ops.scale(p['m'].bm, vec=V((0.001, 0.001, 0.001)), verts=p['m'].bm.verts)
        if p['pivot'] is not None: p['pivot'] = p['pivot'] * 0.001

VIEWS = {'front_34': ((0.42, 0.30, 0.16), (-0.05, 0, 0), 40), 'back_34': ((-0.55, -0.30, 0.20), (-0.04, 0, 0), 40),
         'inside': ((0.20, -0.32, 0.18), (0.0, 0, 0), 40),
         'detail_front': ((0.24, 0.15, 0.10), (0.01, 0, 0), 60), 'detail_back': ((-0.22, -0.13, 0.07), (-0.01, 0, 0), 60),
         'front': ((0.45, 0, 0.02), (0, 0, 0), 50), 'top': ((0.02, 0, 0.45), (-0.04, 0, 0), 40), 'below': ((0.15, 0.10, -0.30), (-0.01, 0, -0.03), 50),
         'side': ((-0.02, 0.40, 0.03), (-0.04, 0, 0), 40), 'face': ((-0.33, 0.0, 0.02), (-0.03, 0, 0), 50)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, ((0.42, 0.30, 0.16), (-0.085, 0, 0.012), 68))
