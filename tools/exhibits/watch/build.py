# Dive-watch exhibit (generic 42 mm automatic, no brand), built from scratch for Mechanica.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/watch/build.py -- public/exhibits/watch [--preview]
# Run tools/exhibits/watch/cad.py first (case, bezel, case back, crown, plates, bridges, wheels, escapement and rotor come from its STLs).
# Modelled in millimetres (dial faces +z, 12 o'clock = +y, 3 o'clock = +x, z = 0 on the dial face), scaled to metres at the end.
# Glb: real size. glTF: dial faces +y, 12 o'clock = -z. Every wheel turns about the case axis; the sign of extras.axis is its turning
# sense, so the gear ratios in the hand-off are all positive. The pallet fork and the balance oscillate about their own axes.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths
import common
from layout import *
from math import asin

X, Z = V((1, 0, 0)), V((0, 0, 1))
CW = -Z                                        # clockwise seen from the dial
def at(x=0.0, y=0.0): return Matrix.Translation(V((x, y, 0)))
def hand_dir(deg): return V((sin(radians(deg)), cos(radians(deg)), 0))   # clockwise from 12
def along(deg): d = hand_dir(deg); return Matrix(((d.y, d.x, 0), (-d.x, d.y, 0), (0, 0, 1)))   # local y -> hand direction

common.MATS.update({   # base colour (linear), metallic, roughness
    'steel':   ((0.62, 0.63, 0.65), 1.0, 0.18),    # polished case
    'rhodium': ((0.72, 0.73, 0.75), 1.0, 0.30),    # bridges, rotor
    'plate':   ((0.55, 0.56, 0.58), 1.0, 0.40),
    'gilt':    ((0.80, 0.55, 0.25), 1.0, 0.28),    # wheels
    'blued':   ((0.04, 0.07, 0.30), 1.0, 0.25),    # screws, springs
    'ruby':    ((0.55, 0.02, 0.05), 0.0, 0.10),
    'dial':    ((0.008, 0.008, 0.010), 0.0, 0.12),
    'ceramic': ((0.005, 0.005, 0.008), 0.0, 0.08),
    'lume':    ((0.72, 0.80, 0.64), 0.0, 0.45),
    'white':   ((0.85, 0.85, 0.85), 0.0, 0.40),
    'red':     ((0.60, 0.03, 0.02), 0.0, 0.35),
    'rubber':  ((0.02, 0.02, 0.022), 0.0, 0.75),
    'glass':   ((0.80, 0.85, 0.90), 0.0, 0.02),
})

def band(m, pts, wdir, w, t, mat):
    """Flat strip along pts: width w along wdir (kept square to the path), thickness t (either can be a list, one per point)."""
    rings = []; n = len(pts)
    W = w if isinstance(w, list) else [w] * n; T = t if isinstance(t, list) else [t] * n
    for i, p in enumerate(pts):
        w, t = W[i], T[i]
        tg = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = (wdir - tg * wdir.dot(tg)).normalized(); b = tg.cross(a)
        rings.append([m.bm.verts.new(p + a * sa * w / 2 + b * sb * t / 2) for sa, sb in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    for r0, r1 in zip(rings, rings[1:]): m.bridge(r0, r1, mat)
    m.face(rings[0][::-1], mat); m.face(rings[-1], mat)

def spiral(c, r0, r1, turns, z, n=36): return [V((c[0], c[1], z)) + V((cos(t), sin(t), 0)) * (r0 + (r1 - r0) * t / (TAU * turns))
                                                for t in (TAU * turns * i / (n * turns) for i in range(int(n * turns) + 1))]

def prism(m, pts, c, z, t, mat, R=Matrix.Identity(3)):
    """Flat plate of outline pts (local x, y; convex), centred on c, top at z + t/2, rotated by R about c."""
    lo = [m.bm.verts.new(c + R @ V((x, y, 0)) + V((0, 0, z - t / 2))) for x, y in pts]
    hi = [m.bm.verts.new(c + R @ V((x, y, 0)) + V((0, 0, z + t / 2))) for x, y in pts]
    m.face(lo[::-1], mat); m.face(hi, mat); m.bridge(lo, hi, mat)

def glyphs(s, size, t):
    """One mesh per character of s (Blender's built-in font), each centred on its own origin, with its advance width."""
    out = []
    for ch in s:
        if ch == ' ': out.append((None, size * 0.35)); continue
        cu = bpy.data.curves.new('t', 'FONT'); cu.body = ch; cu.size = size; cu.extrude = t / 2; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
        ob = bpy.data.objects.new('t', cu); bpy.context.scene.collection.objects.link(ob)
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
        xs = [v.co.x for v in me.vertices]; out.append((me, (max(xs) - min(xs)) + size * 0.12))
    return out

def put(m, me, M, mat):
    me.transform(M); n = len(m.bm.faces); m.bm.from_mesh(me); m.bm.faces.ensure_lookup_table()
    for f in m.bm.faces[n:]: f.material_index = m.mi(mat); f.smooth = False
    bpy.data.meshes.remove(me)

def print_line(m, s, c, size, mat, t=0.03):
    """Straight printed line of text on the dial (reads from the front), centred on c."""
    gl = glyphs(s, size, t); x = -sum(w for _, w in gl) / 2
    for me, w in gl:
        if me: put(m, me, Matrix.Translation(c + V((x + w / 2, 0, 0))), mat)
        x += w

def print_arc(m, s, R, a_mid, z, size, mat, back=False, t=0.03):
    """Text round an arc of radius R centred on angle a_mid (degrees, from +x), letters upright (feet towards the centre).
    back=True: reads from the case back (seen from -z)."""
    gl = glyphs(s, size, t); a = radians(a_mid) + (-1 if back else 1) * sum(w for _, w in gl) / R / 2
    for me, w in gl:
        a -= (-1 if back else 1) * w / R / 2
        if me:
            r = V((cos(a), sin(a), 0)); x = V((-sin(a), cos(a), 0)) if back else V((sin(a), -cos(a), 0)); zz = x.cross(r)
            M = Matrix((x, r, zz)).transposed().to_4x4(); M.translation = r * R + V((0, 0, z))
            put(m, me, M, mat)
        a -= (-1 if back else 1) * w / R / 2

def jewel(m, x, y, z):
    """Ruby in its polished sink (the sink is cut into the bridge): domed top, the pivot hole showing in the middle."""
    m.disc(V((x, y, z)), Z, 0.42, 0.08, 'ruby', 20); m.disc(V((x, y, z - 0.05)), Z, 0.3, 0.04, 'ruby', 20)
    m.disc(V((x, y, z - 0.075)), Z, 0.07, 0.02, 'ceramic', 8)
def screw(m, x, y, z, r=0.6):
    """Blued screw: domed head standing proud of the bridge, a slot across it."""
    m.disc(V((x, y, z)), Z, r, 0.12, 'blued', 20); m.disc(V((x, y, z - 0.08)), Z, r * 0.8, 0.06, 'blued', 20)
    m.box(V((x, y, z - 0.1)), (r * 1.9, r * 0.22, 0.06), 'ceramic', Matrix.Rotation(radians(37 * x + 11 * y), 3, 'Z'))

# ---------------------------------------------------------------- outside
def case():
    m = part('case', explode=(0, 0, 0))
    m.stl('case', 'steel', at())
    part('crystal', explode=(0, 0, 0.060)).disc(V((0, 0, 3.6)), Z, 16.3, 2.2, 'glass', 96)
    m = part('bezel', pivot=V((0, 0, 3.5)), axis=Z, explode=(0, 0, 0.045))      # unidirectional: turns counter-clockwise only
    m.stl('bezel', 'steel', at())
    m.disc(V((0, 0, 4.56)), Z, 19.9, 0.12, 'ceramic', 96, r_in=16.8)
    for k in range(60):
        if k == 0: continue
        d = hand_dir(6 * k); big = k % 5 == 0 or k < 15
        if big: m.box(d * 18.4 + V((0, 0, 4.64)), (0.5 if k % 5 else 0.9, 2.2 if k % 5 == 0 else 1.0, 0.06), 'white', along(6 * k))
    m.box(V((0, 18.3, 4.64)), (1.9, 1.9, 0.06), 'white', Matrix.Rotation(radians(45), 3, 'Z')); m.disc(V((0, 18.3, 4.68)), Z, 0.55, 0.06, 'lume', 16)
    m = part('case_back', explode=(0, 0, -0.085))
    m.stl('case_back', 'steel', at()); m.disc(V((0, 0, -8.15)), Z, 12.9, 1.5, 'glass', 64)
    print_arc(m, 'STAINLESS STEEL  WATER RESISTANT 200m', 15.4, 90, -9.01, 1.0, 'plate', back=True)
    print_arc(m, 'SAPPHIRE CRYSTAL  AUTOMATIC', 15.4, 270, -9.01, 1.0, 'plate', back=True)
    m = part('crown', pivot=V((20, 0, -1.9)), axis=X, explode=(0.03, 0, 0))
    m.stl('crown', 'steel', at())

def dial():
    m = part('dial', explode=(0, 0, 0.018))
    m.stl('dial', 'dial', at())
    for h in range(12):
        d = hand_dir(30 * h); c = d * 11.6 + V((0, 0, 0.2))
        # applied indices: a polished steel surround, the lume filled in a touch proud of it
        if h == 0:
            tri = [(-1.7, 1.2), (0, -1.6), (1.7, 1.2)]
            prism(m, [(x * 1.18, y * 1.18) for x, y in tri], c + V((0, 0.4, 0)), 0.0, 0.42, 'steel'); prism(m, tri, c + V((0, 0.4, 0)), 0.04, 0.42, 'lume')
        elif h % 3 == 0: m.box(c, (2.2, 4.6, 0.36), 'steel', along(30 * h)); m.box(c + V((0, 0, 0.04)), (1.7, 4.1, 0.36), 'lume', along(30 * h))
        else: m.disc(c, Z, 1.45, 0.36, 'steel', 28); m.disc(c + V((0, 0, 0.04)), Z, 1.18, 0.36, 'lume', 28)
    for k in range(60): m.box(hand_dir(6 * k) * 14.3 + V((0, 0, 0.02)), (0.15, 0.9 if k % 5 else 1.3, 0.04), 'white', along(6 * k))
    print_line(m, 'AUTOMATIC', V((0, 5.4, 0.02)), 1.05, 'white')
    print_line(m, '200m = 660ft', V((0, -5.2, 0.02)), 0.95, 'white')
    print_line(m, '25 JEWELS', V((0, -6.9, 0.02)), 0.8, 'white')

def hands():
    for pid, deg, L, w, z, ex in (('hour_hand', 305, 8.6, 1.9, 0.55, 0.025), ('minute_hand', 60, 13.4, 1.3, 0.85, 0.030)):
        m = part(pid, pivot=V((0, 0, z)), axis=CW, explode=(0, 0, ex))
        R = along(deg); d = hand_dir(deg)
        m.disc(V((0, 0, z)), Z, 1.3 if pid == 'hour_hand' else 1.0, 0.14, 'steel', 24)               # boss
        m.disc(V((0, 0, z + 0.06)), Z, 0.45, 0.1, 'steel', 16)
        sword = [(-w * 0.28, -2.2), (w * 0.28, -2.2), (w * 0.3, 0.6), (w / 2, L * 0.66), (0, L + 0.6), (-w / 2, L * 0.66), (-w * 0.3, 0.6)]
        prism(m, sword, V((0, 0, 0)), z, 0.12, 'steel', R)                                              # polished sword blade, short tail
        prism(m, [(-w * 0.16, 2.0), (w * 0.16, 2.0), (w * 0.34, L * 0.66), (0, L - 0.2), (-w * 0.34, L * 0.66)], V((0, 0, 0)), z + 0.07, 0.06, 'lume', R)
        if pid == 'hour_hand': m.stl('hour_wheel', 'gilt', at())
    m = part('seconds_hand', pivot=V((0, 0, 1.2)), axis=CW, explode=(0, 0, 0.035))
    R = along(222); d = hand_dir(222)
    m.disc(V((0, 0, 1.2)), Z, 0.7, 0.1, 'steel', 20); m.disc(V((0, 0, 1.27)), Z, 0.3, 0.08, 'steel', 12)
    prism(m, [(-0.09, 0), (0.09, 0), (0.05, 14.4), (-0.05, 14.4)], V((0, 0, 0)), 1.2, 0.08, 'steel', R)                # needle, tapering
    prism(m, [(-0.22, -0.4), (0.22, -0.4), (0.13, -3.4), (-0.13, -3.4)], V((0, 0, 0)), 1.2, 0.08, 'steel', R)          # tail
    m.disc(-d * 3.8 + V((0, 0, 1.2)), Z, 0.75, 0.08, 'steel', 20)                                                     # counterweight
    m.box(d * 13.6 + V((0, 0, 1.25)), (0.14, 1.6, 0.04), 'red', R)
    m.disc(d * 10.0 + V((0, 0, 1.2)), Z, 0.8, 0.1, 'steel', 20); m.disc(d * 10.0 + V((0, 0, 1.27)), Z, 0.6, 0.05, 'lume', 20)

# ---------------------------------------------------------------- movement
def train():
    part('mainplate', explode=(0, 0, -0.015)).stl('mainplate', 'plate', at())
    m = part('barrel', pivot=V((*BARREL, -3.4)), axis=Z, explode=(0, 0, -0.030))
    m.stl('barrel', 'gilt', at(*BARREL))
    band(m, spiral(BARREL, 1.0, 4.85, 7, -3.35), Z, 1.0, 0.12, 'blued')                               # mainspring
    m = part('center_wheel', pivot=V((0, 0, -3.5)), axis=CW, explode=(0, 0, -0.030))
    m.stl('center_wheel', 'gilt', at()); m.stl('cannon_pinion', 'steel', at())
    part('third_wheel', pivot=V((*THIRD, -4.5)), axis=Z, explode=(0, 0, -0.030)).stl('third_wheel', 'gilt', at(*THIRD))
    part('fourth_wheel', pivot=V((0, 0, -4.9)), axis=CW, explode=(0, 0, -0.036)).stl('fourth_wheel', 'gilt', at())
    part('escape_wheel', pivot=V((*ESCAPE, -3.6)), axis=Z, explode=(0, 0, -0.030)).stl('escape_wheel', 'steel', at(*ESCAPE))
    m = part('pallet_fork', pivot=V((*PALLET, -3.6)), axis=Z, explode=(0, 0, -0.033))
    m.stl('pallet_fork', 'steel', at(*PALLET))
    ex, ey = ESCAPE[0] - PALLET[0], ESCAPE[1] - PALLET[1]
    for s in (1, -1):                                                                                 # entry and exit stones
        m.box(V((PALLET[0] + ex * 0.6 + s * ey * 0.42, PALLET[1] + ey * 0.6 - s * ex * 0.42, -3.62)), (0.35, 0.7, 0.24), 'ruby',
              Matrix.Rotation(atan2(ey, ex), 3, 'Z'))
    m = part('balance', pivot=V((*BALANCE, -3.9)), axis=Z, explode=(0, 0, -0.045))
    m.stl('balance', 'gilt', at(*BALANCE))
    hs = spiral(BALANCE, 0.75, 2.7, 9, -4.35); end = hs[-1]; tg = (hs[-1] - hs[-2]).normalized()
    m.sweep(hs + [end + tg * 0.4 + (end - V((*BALANCE, -4.35))).normalized() * 0.25], 0.035, 'blued', 4)   # hairspring, end curve to the stud
    m.box(V((BALANCE[0] + 0.6, BALANCE[1], -3.5)), (0.15, 0.15, 0.4), 'ruby')                        # impulse jewel
    part('minute_wheel', pivot=V((*MINUTE_WHEEL, -0.8)), axis=Z, explode=(0, 0, 0.012)).stl('minute_wheel', 'steel', at(*MINUTE_WHEEL))

def bridges():
    m = part('barrel_bridge', explode=(0, 0, -0.050))
    m.stl('barrel_bridge', 'rhodium', at()); m.stl('ratchet', 'steel', at(*BARREL)); m.stl('crown_wheel', 'steel', at(*CROWN_WHEEL))
    for x, y in ((-6.0, 9.2), (6.8, 8.6)): screw(m, x, y, -6.45)
    screw(m, *BARREL, -6.67, 1.1); screw(m, *CROWN_WHEEL, -6.67, 0.7)                                # ratchet and crown-wheel screws
    click = [V((BARREL[0] - 3.9 * cos(t), BARREL[1] + 3.9 * sin(t), -6.5)) for t in (radians(a) for a in range(20, 75, 5))]
    m.sweep(click, 0.12, 'steel', 6)                                                                 # click spring
    m = part('train_bridge', explode=(0, 0, -0.050))
    m.stl('train_bridge', 'rhodium', at())
    for x, y in ((0, 0), THIRD, ESCAPE, PALLET): jewel(m, x, y, -6.29)
    for x, y in ((8.0, -7.5), (-0.8, -10.6), (-4.6, -9.6)): screw(m, x, y, -6.45)
    m = part('balance_cock', explode=(0, 0, -0.060))
    m.stl('balance_cock', 'rhodium', at()); jewel(m, *BALANCE, -6.49); screw(m, -8.9, -7.4, -6.65, 0.75)
    bx, by = BALANCE                                                                                  # regulator: index arm with its +/- scale, stud carrier
    m.disc(V((bx, by, -6.68)), Z, 0.95, 0.08, 'steel', 28, r_in=0.5)
    IDX = 176                                                                                          # the index lies along the cock arm
    prism(m, [(-0.18, 0.6), (0.18, 0.6), (0.08, 4.6), (-0.08, 4.6)], V((bx, by, 0)), -6.7, 0.07, 'steel', Matrix.Rotation(radians(IDX), 3, 'Z'))
    prism(m, [(-0.25, 0.6), (0.25, 0.6), (0.25, 1.9), (-0.25, 1.9)], V((bx, by, 0)), -6.7, 0.07, 'steel', Matrix.Rotation(radians(-80), 3, 'Z'))
    for k in range(-3, 4):
        Rk = Matrix.Rotation(radians(180 + k * 4), 3, 'Z'); m.box(V((bx, by, -6.64)) + Rk @ V((0, 4.25, 0)), (0.05, 0.35 if k else 0.6, 0.03), 'ceramic', Rk)
    m = part('rotor', pivot=V((0, 0, -6.9)), axis=Z, explode=(0, 0, -0.070))                       # self-winding weight, turns either way
    m.stl('rotor', 'rhodium', at())
    m.disc(V((0, 0, -6.95)), Z, 2.3, 0.5, 'steel', 40, r_in=1.55)                                    # ball bearing: outer race
    for k in range(14): m.disc(V((1.92 * cos(TAU * k / 14), 1.92 * sin(TAU * k / 14), -7.1)), Z, 0.16, 0.3, 'steel', 8)   # balls
    m.disc(V((0, 0, -6.95)), Z, 1.55, 0.6, 'plate', 32, r_in=0.5); m.disc(V((0, 0, -7.0)), Z, 1.2, 0.6, 'steel', 32)  # inner race, cap
    for k in range(3): screw(m, 0.75 * cos(TAU * k / 3 + 0.5), 0.75 * sin(TAU * k / 3 + 0.5), -7.32, 0.22)
    print_arc(m, 'AUTOMATIC', 11.0, 125, -7.27, 1.1, 'gilt', back=True)
    print_arc(m, '25 JEWELS', 11.0, 55, -7.27, 1.1, 'gilt', back=True)

def strap():
    zc = -30.0; R = (22.0 ** 2 + (zc + 2.5) ** 2) ** 0.5; f0 = asin(22.0 / R)
    def arc(s, f1): return [V((0, s * R * sin(f), zc + R * cos(f))) for f in (f0 + (f1 - f0) * i / 30 for i in range(31))]
    def rrect(cx, cy, hw, hh, r, n=4):   # rounded rectangle, closed
        out = []
        for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
            for i in range(n + 1):
                a = radians(a0 + 90 * i / n); out.append((cx + sx * (hw - r) + r * cos(a), cy + sy * (hh - r) + r * sin(a)))
        return out + out[:1]
    for pid, s, f1 in (('strap_top', 1, radians(178)), ('strap_bottom', -1, radians(165))):
        m = part(pid, explode=(0, s * 0.035, 0))
        pts = arc(s, f1); n = len(pts)
        band(m, pts, X, [21.6 - 2.6 * max(0, i - 4) / (n - 5) for i in range(n)], [4.0 - 1.2 * min(1, i / 8) for i in range(n)], 'rubber')
        for x in (-6.5, -2.2, 2.2, 6.5):                                                              # moulded ribs at the lug end
            m.box(pts[2] + (pts[2] - V((0, 0, zc))).normalized() * 1.6 + V((x, 0, 0)), (2.6, 3.4, 0.4), 'rubber',
                  Matrix((X, (pts[3] - pts[1]).normalized(), (pts[3] - pts[1]).normalized().cross(X))).transposed())
        m.tube(V((-11.2, s * 22.0, -2.5)), V((11.2, s * 22.0, -2.5)), 0.4, 'steel', 8)              # spring bar
        for x in (-11.75, 11.75): m.tube(V((x, s * 22.0, -2.5)), V((x * 1.06, s * 22.0, -2.5)), 0.3, 'steel', 8)
        if s > 0:                                                                                     # adjustment holes through the long strap
            for i in range(17, n - 2, 2):
                nm = (pts[i] - V((0, 0, zc))).normalized(); m.disc(pts[i], nm, 0.95, 2.84, 'ceramic', 20)
        else:                                                                                         # keepers, rounded tang buckle at the end
            e = pts[-1]; tg = (pts[-1] - pts[-2]).normalized(); nm = tg.cross(X)
            rot = Matrix((X, tg, nm)).transposed()
            for i in (n - 6, n - 10):
                t2 = (pts[i + 1] - pts[i - 1]).normalized(); n2 = t2.cross(X)
                m.sweep([pts[i] + X * a + n2 * b for a, b in rrect(0, 0, 10.6, 2.0, 0.8)], 0.55, 'rubber', 6, caps=False)
            m.sweep([e + rot @ V((x, y, 0)) for x, y in rrect(0, 3.3, 12.4, 3.6, 1.6)], 0.75, 'steel', 8, caps=False)
            m.tube(e + rot @ V((-12.0, 0.0, 0)), e + rot @ V((12.0, 0.0, 0)), 0.5, 'steel', 8)        # bar the strap wraps round
            m.sweep([e + rot @ V((0, y, z)) for y, z in ((0.0, 0.0), (0.2, 0.8), (3.0, 1.2), (6.6, 1.0), (7.4, 0.2))], 0.4, 'steel', 8)  # tang

def build():
    g = common.material('glass'); b = g.node_tree.nodes['Principled BSDF']
    b.inputs['Alpha'].default_value = 0.15; g.surface_render_method = 'BLENDED'
    case(); dial(); hands(); train(); bridges(); strap()
    for p in PARTS.values():                                                                          # mm -> m
        bmesh.ops.scale(p['m'].bm, vec=V((0.001, 0.001, 0.001)), verts=p['m'].bm.verts)
        if p['pivot'] is not None: p['pivot'] = p['pivot'] * 0.001

_lights_camera = common.lights_camera
def lights_camera(*a):                         # the default 0.1 m near clip would cut a watch in half
    sc = _lights_camera(*a); sc.camera.data.clip_start = 0.001; return sc
common.lights_camera = lights_camera

VIEWS = {'front_34': ((0.05, -0.09, 0.10), (0, -0.004, -0.006), 50), 'back': ((0.035, -0.06, -0.11), (0, 0, -0.008), 50),
         'movement': ((0.018, -0.03, -0.07), (0, 0, -0.004), 60), 'side': ((0.12, 0.0, 0.01), (0, 0, -0.01), 50),
         'dial_close': ((0.012, -0.02, 0.045), (0.002, 0.0, 0.0), 70), 'crown_close': ((0.04, -0.018, 0.012), (0.021, 0, -0.002), 70),
         'balance_close': ((-0.004, -0.008, -0.024), (-0.007, -0.003, -0.005), 90), 'train_close': ((0.004, -0.012, -0.03), (0.0, -0.001, -0.005), 70),
         'bare_movement': ((0.0, -0.012, -0.05), (0, 0, -0.005), 55),
         'strap_close': ((0.03, 0.05, 0.02), (0, 0.03, -0.005), 60)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['front_34'])
