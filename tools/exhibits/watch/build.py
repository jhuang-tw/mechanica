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
    """Flat strip along pts: width w along wdir (kept square to the path), thickness t."""
    rings = []
    for i, p in enumerate(pts):
        tg = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = (wdir - tg * wdir.dot(tg)).normalized(); b = tg.cross(a)
        rings.append([m.bm.verts.new(p + a * sa * w / 2 + b * sb * t / 2) for sa, sb in ((1, 1), (-1, 1), (-1, -1), (1, -1))])
    for r0, r1 in zip(rings, rings[1:]): m.bridge(r0, r1, mat)
    m.face(rings[0][::-1], mat); m.face(rings[-1], mat)

def spiral(c, r0, r1, turns, z, n=36): return [V((c[0], c[1], z)) + V((cos(t), sin(t), 0)) * (r0 + (r1 - r0) * t / (TAU * turns))
                                                for t in (TAU * turns * i / (n * turns) for i in range(int(n * turns) + 1))]

def jewel(m, x, y, z): m.disc(V((x, y, z)), Z, 0.55, 0.1, 'ruby', 16)
def screw(m, x, y, z):
    m.disc(V((x, y, z)), Z, 0.75, 0.16, 'blued', 16); m.box(V((x, y, z - 0.09)), (1.3, 0.2, 0.05), 'ceramic')

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
    m = part('crown', pivot=V((20, 0, -1.9)), axis=X, explode=(0.03, 0, 0))
    m.stl('crown', 'steel', at())

def dial():
    m = part('dial', explode=(0, 0, 0.018))
    m.stl('dial', 'dial', at())
    for h in range(12):
        d = hand_dir(30 * h); c = d * 11.6 + V((0, 0, 0.2))
        if h == 0: m.box(c + V((0, 0.4, 0)), (2.6, 2.6, 0.4), 'lume', Matrix.Rotation(radians(45), 3, 'Z'))
        elif h % 3 == 0: m.box(c, (1.8, 4.2, 0.4), 'lume', along(30 * h))
        else: m.disc(c, Z, 1.2, 0.4, 'lume', 20)
    for k in range(60): m.box(hand_dir(6 * k) * 14.3 + V((0, 0, 0.02)), (0.15, 0.9 if k % 5 else 1.3, 0.04), 'white', along(6 * k))

def hands():
    for pid, deg, L, w, z, ex in (('hour_hand', 305, 8.6, 1.9, 0.55, 0.025), ('minute_hand', 60, 13.4, 1.3, 0.85, 0.030)):
        m = part(pid, pivot=V((0, 0, z)), axis=CW, explode=(0, 0, ex))
        R = along(deg); d = hand_dir(deg)
        m.disc(V((0, 0, z)), Z, 1.3 if pid == 'hour_hand' else 1.0, 0.12, 'steel', 20)
        m.box(d * L / 2 + V((0, 0, z)), (w, L, 0.12), 'steel', R)
        m.box(d * (L / 2 + 0.8) + V((0, 0, z + 0.07)), (w * 0.6, L - 3.2, 0.06), 'lume', R)
        m.box(d * (L + 0.3) + V((0, 0, z)), (w * 0.72, w * 0.72, 0.12), 'steel', R @ Matrix.Rotation(radians(45), 3, 'Z'))
        if pid == 'hour_hand': m.stl('hour_wheel', 'gilt', at())
    m = part('seconds_hand', pivot=V((0, 0, 1.2)), axis=CW, explode=(0, 0, 0.035))
    R = along(222); d = hand_dir(222)
    m.disc(V((0, 0, 1.2)), Z, 0.7, 0.1, 'steel', 16)
    m.box(d * 5.3 + V((0, 0, 1.2)), (0.28, 18.6, 0.08), 'steel', R)
    m.box(d * 13.6 + V((0, 0, 1.25)), (0.3, 2.0, 0.06), 'red', R)
    m.disc(d * 10.0 + V((0, 0, 1.2)), Z, 0.8, 0.1, 'steel', 16); m.disc(d * 10.0 + V((0, 0, 1.27)), Z, 0.6, 0.05, 'lume', 16)

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
    m.sweep(spiral(BALANCE, 0.75, 2.7, 9, -4.35), 0.035, 'blued', 4)                                # hairspring
    m.box(V((BALANCE[0] + 0.6, BALANCE[1], -3.5)), (0.15, 0.15, 0.4), 'ruby')                        # impulse jewel
    part('minute_wheel', pivot=V((*MINUTE_WHEEL, -0.8)), axis=Z, explode=(0, 0, 0.012)).stl('minute_wheel', 'steel', at(*MINUTE_WHEEL))

def bridges():
    m = part('barrel_bridge', explode=(0, 0, -0.050))
    m.stl('barrel_bridge', 'rhodium', at()); m.stl('ratchet', 'steel', at(*BARREL))
    for x, y in ((-6.0, 9.2), (6.8, 8.6)): screw(m, x, y, -6.45)
    m = part('train_bridge', explode=(0, 0, -0.050))
    m.stl('train_bridge', 'rhodium', at())
    for x, y in ((0, 0), THIRD, ESCAPE, PALLET): jewel(m, x, y, -6.43)
    screw(m, 8.0, -7.5, -6.45)
    m = part('balance_cock', explode=(0, 0, -0.060))
    m.stl('balance_cock', 'rhodium', at()); jewel(m, *BALANCE, -6.63); screw(m, -8.8, -6.9, -6.65)
    m = part('rotor', pivot=V((0, 0, -6.9)), axis=Z, explode=(0, 0, -0.070))                       # self-winding weight, turns either way
    m.stl('rotor', 'rhodium', at()); m.disc(V((0, 0, -6.95)), Z, 1.4, 0.2, 'steel', 20)

def strap():
    zc = -30.0; R = (22.0 ** 2 + (zc + 2.5) ** 2) ** 0.5; f0 = asin(22.0 / R)
    def arc(s, f1): return [V((0, s * R * sin(f), zc + R * cos(f))) for f in (f0 + (f1 - f0) * i / 30 for i in range(31))]
    for pid, s, f1 in (('strap_top', 1, radians(178)), ('strap_bottom', -1, radians(165))):
        m = part(pid, explode=(0, s * 0.035, 0))
        pts = arc(s, f1); band(m, pts, X, 21.6, 3.4, 'rubber')
        m.tube(V((-11.2, s * 22.0, -2.5)), V((11.2, s * 22.0, -2.5)), 0.6, 'steel', 8)              # spring bar
        if s < 0:                                                                                     # tang buckle at the end
            e = pts[-1]; tg = (pts[-1] - pts[-2]).normalized(); nm = tg.cross(X)
            rot = Matrix((X, tg, nm)).transposed()
            for c, size in ((V((12.2, 3, 0)), (1.4, 8, 1.6)), (V((-12.2, 3, 0)), (1.4, 8, 1.6)), (V((0, 6.6, 0)), (25.8, 1.4, 1.6)),
                            (V((0, 0, 0)), (25.8, 1.4, 1.6)), (V((0, 3.6, -1.0)), (1.0, 7.0, 0.8))):
                m.box(e + rot @ c, size, 'steel', rot)

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
         'movement': ((0.018, -0.03, -0.07), (0, 0, -0.004), 60), 'side': ((0.12, 0.0, 0.01), (0, 0, -0.01), 50)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['front_34'])
