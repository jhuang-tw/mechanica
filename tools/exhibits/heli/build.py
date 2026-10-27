# Helicopter exhibit (generic light single-turbine, two-blade teetering rotor), built from scratch for Mechanica.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/heli/build.py -- public/exhibits/heli [--preview]
# Run tools/exhibits/heli/cad.py first (gearbox gears, swashplate, rotor hub and tail gears come from its STLs).
# Model frame (Blender): metres, skids on z = 0, nose = +x, left = +y. glTF: nose +x, up +y, right = +z.
# Main rotor turns counter-clockwise seen from above: mast, hub, blades, upper swashplate and pitch links spin about glTF +y.
# The rotating parts hang on the mast; blades hang on the hub and feather about their own span axis (extras.axis).
# The fuselage, cabin doors, tail boom and engine cowling come from Tripo (tools/tripo-ref) and are added when that GLB exists.
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
    m = part('cyclic', pivot=V((1.30, -0.32, 0.60)), explode=(0.3, -0.4, 0.3))
    m.sweep([V((1.30, -0.32, 0.60)), V((1.32, -0.32, 0.95)), V((1.28, -0.32, 1.12))], [0.018, 0.016, 0.02], 'black', 10)
    m.disc(V((1.30, -0.32, 0.60)), V((0, 0, 1)), 0.06, 0.04, 'rubber' if 'rubber' in common.MATS else 'black', 12)
    m = part('collective', pivot=V((0.95, -0.05, 0.62)), axis=Y, explode=(0.2, 0.4, 0.3))
    m.sweep([V((0.95, -0.05, 0.62)), V((1.35, -0.07, 0.78)), V((1.52, -0.08, 0.80))], [0.02, 0.018, 0.024], 'black', 10)
    m = part('pedals', explode=(0.5, 0, 0))
    for y in (-0.42, -0.22): m.box(V((1.95, y, 0.52)), (0.04, 0.09, 0.16), 'alu', Matrix.Rotation(radians(-20), 3, 'Y'))
    m.tube(V((1.98, -0.48, 0.45)), V((1.98, -0.16, 0.45)), 0.012, 'steel', 8)
    m = part('control_rods', explode=(0, -0.5, 0.4))                                                  # mixing linkage up to the servos
    for k, a in enumerate((0, 120, 240)):
        d = V((cos(radians(a)), sin(radians(a)), 0)); top = V((0, 0, PLAN_Z - 0.05)) + d * 0.32
        m.sweep([V((1.0, -0.2 + 0.05 * k, 0.55)), V((0.6, -0.2 + 0.05 * k, 1.55)), top + V((0, 0, -0.05))], 0.008, 'steel', 6)

def airframe():
    m = part('skids', explode=(0, 0, -0.5))
    for s in (1, -1):
        m.sweep([V((-1.45, s * 1.0, 0.05)), V((1.55, s * 1.0, 0.05)), V((1.80, s * 1.0, 0.18))], 0.035, 'alu', 12)
    for x in (0.95, -0.75):
        m.sweep([V((x, 1.0, 0.07)), V((x, 0.85, 0.42)), V((x, 0.45, 0.58)), V((x, -0.45, 0.58)), V((x, -0.85, 0.42)), V((x, -1.0, 0.07))], 0.04, 'alu', 12)
    m = part('fuel_tank', explode=(0, 0, -0.7))
    m.box(V((0.05, 0, 0.62)), (0.65, 0.95, 0.40), 'black')

def build():
    gearbox(); rotor(); engine(); tail(); controls(); airframe()

VIEWS = {'left_34': ((7.0, 8.5, 5.0), (-1.2, 0, 1.8), 30), 'rotor_head': ((1.6, 1.4, 3.3), (0, 0, 2.45), 40),
         'drive': ((0.6, -2.4, 2.4), (-0.6, 0, 2.05), 40), 'tail': ((-5.0, -1.6, 2.6), (-6.3, -0.2, 2.25), 40)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['left_34'])
