# Turbofan exhibit (generic two-spool high-bypass engine, CFM56 class, no brand), built from scratch for Mechanica.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/jet/build.py -- public/exhibits/jet [--preview]
# Run tools/exhibits/jet/cad.py first (nacelle, casings, drums, spinner, exhaust plug and the tower-shaft bevels come from its STLs).
# Model frame (Blender): metres, stand on z = 0, intake = +x, left = +y. glTF: intake +x, up +y, right = +z.
# The casings are cut away over the upper-left quadrant so the spools show. Two spools turn about the engine axis (extras.axis = +x):
# low pressure (fan, booster, LP shaft, LP turbine) and high pressure (HP compressor, HP shaft, HP turbine); the radial drive shaft
# takes power off the HP spool through a bevel pair down to the accessory gearbox. The fan-cowl doors hinge about +x at the top.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths
import common

S = Matrix.Scale(0.001, 4)
X, Z = V((1, 0, 0)), V((0, 0, 1))
CZ = 1.15                                      # engine centreline height
C = V((0, 0, CZ))
TO_X = Matrix.Rotation(pi / 2, 4, 'Y') @ S     # CAD z (engine front) -> Blender +x, CAD x -> Blender -z
def at(x=0.0, M=TO_X, p=None): return Matrix.Translation(p if p is not None else C + X * x) @ M
def P(x, r=0.0, a=-90.0): return C + V((x, r * cos(radians(a)), r * sin(radians(a))))   # a = -90: straight down

common.MATS.update({   # base colour (linear), metallic, roughness
    'paint':  ((0.78, 0.79, 0.80), 0.0, 0.35),     # nacelle
    'alu':    ((0.62, 0.63, 0.65), 1.0, 0.35),
    'steel':  ((0.50, 0.51, 0.53), 1.0, 0.28),
    'ti':     ((0.42, 0.43, 0.46), 1.0, 0.30),     # fan and compressor blades
    'dark':   ((0.06, 0.06, 0.07), 0.8, 0.45),
    'black':  ((0.015, 0.015, 0.017), 0.0, 0.55),
    'hot':    ((0.30, 0.18, 0.10), 1.0, 0.45),     # combustor and turbine case
    'nickel': ((0.55, 0.45, 0.30), 1.0, 0.35),     # turbine blades
    'brass':  ((0.60, 0.42, 0.15), 1.0, 0.35),
    'red':    ((0.50, 0.04, 0.03), 0.2, 0.40),
})

def foil(chord, th, n=6):
    """Thin symmetric section, leading edge at -chord/2, as a (u, v) loop."""
    up = [(chord * (i / n - 0.5), th / 2 * 4 * (i / n) * (1 - i / n) ** 0.8) for i in range(n + 1)]
    return up + [(u, -v) for u, v in up[-2:0:-1]]

def row(m, x, n, r0, r1, chord, st0, st1, mat, th=0.004, secs=2, sweep=0.0, phase=0.0, fn=2):
    """Ring of n blades between radii r0 and r1 at axial station x; stagger st0 -> st1 degrees from the axis; chord may be (hub, tip)."""
    c0, c1 = chord if isinstance(chord, tuple) else (chord, chord)
    for k in range(n):
        a = TAU * (k + phase) / n; d = V((0, cos(a), sin(a))); t = V((0, -sin(a), cos(a)))
        rings = []
        for i in range(secs):
            f = i / (secs - 1); r = r0 + (r1 - r0) * f; st = radians(st0 + (st1 - st0) * f); ch = c0 + (c1 - c0) * f
            cd = X * cos(st) + t * sin(st); nd = t * cos(st) - X * sin(st); c = C + X * (x - sweep * f) + d * r
            rings.append([m.bm.verts.new(c - cd * u + nd * v) for u, v in foil(ch, th * (1 - 0.5 * f), fn)])
        for a_, b_ in zip(rings, rings[1:]): m.bridge(a_, b_, mat)
        m.cap(rings[0], mat, True); m.cap(rings[-1], mat)

def lerp(a, b, f): return a + (b - a) * f

# ---------------------------------------------------------------- nacelle and fan case (fixed, cut away)
def nacelle():
    part('nacelle_inlet', explode=(1.1, 0, 0)).stl('inlet', 'paint', at())
    for pid, s in (('fan_cowl_left', 1), ('fan_cowl_right', -1)):           # hinged at the top, open like doors
        part(pid, pivot=P(-0.32, 0.975, 90), axis=X, explode=(0, s * 0.9, 0.35)).stl('fan_cowl_' + 'lr'[s < 0], 'paint', at())
    part('thrust_reverser', explode=(-1.3, 0, 0)).stl('reverser', 'paint', at())
    m = part('fan_case', explode=(0, 0, 2.0))
    m.stl('fan_case', 'alu', at())
    row(m, -0.50, 44, 0.49, 0.81, 0.13, -12, -18, 'alu', th=0.008)          # outlet guide vanes take the swirl out of the bypass air
    m.box(P(-0.535, 0.65), (0.16, 0.05, 0.32), 'alu')                        # bottom strut: the radial drive shaft runs inside

def fan():
    m = part('fan', pivot=C, axis=X, explode=(2.0, 0, 0))
    m.stl('spinner', 'black', at()); m.stl('fan_disk', 'ti', at())
    row(m, 0.085, 24, 0.255, 0.79, (0.20, 0.36), 22, 60, 'ti', th=0.03, secs=5, sweep=0.05, fn=5)   # wide-chord, twisted

def lp_spool():
    m = part('booster', pivot=C, axis=X, explode=(0.7, 0, 0))
    m.stl('booster', 'ti', at())
    for x, tip in ((-0.30, 0.420), (-0.39, 0.436), (-0.48, 0.452)): row(m, x, 56, 0.282, tip, 0.045, 30, 48, 'ti')
    part('lp_shaft', pivot=C, axis=X, explode=(0, 0, -0.35)).stl('lp_shaft', 'steel', at())
    m = part('lp_turbine', pivot=C, axis=X, explode=(-0.7, 0, 0))
    m.stl('lpt_drum', 'nickel', at())
    for i in range(4):
        x = -1.62 - 0.10 * i; f = (-1.58 - x) / 0.39
        row(m, x, 64, lerp(0.228, 0.282, f), lerp(0.356, 0.426, f), 0.05, -35, -50, 'nickel', th=0.006)
        m.disc(C + X * x, X, lerp(0.228, 0.282, f) - 0.005, 0.03, 'nickel', 32, r_in=0.05)

def hp_spool():
    m = part('hp_compressor', pivot=C, axis=X, explode=(0, 0, -0.95))
    m.stl('hpc_drum', 'ti', at())
    for i in range(9):
        x = -0.62 - 0.06 * i; f = (-0.59 - x) / 0.57
        row(m, x, 38, lerp(0.222, 0.270, f), lerp(0.343, 0.305, f), 0.032, 35, 50, 'ti', th=0.003)
    m = part('hp_shaft', pivot=C, axis=X, explode=(0, 0, -0.6))
    m.stl('hp_shaft', 'steel', at())
    m.stl('bevel_hp', 'brass', at(-0.635))                                   # drives the radial shaft
    m = part('hp_turbine', pivot=C, axis=X, explode=(0, 0, -0.95))
    m.stl('hpt_disk', 'nickel', at())
    row(m, -1.50, 60, 0.25, 0.345, 0.045, -40, -48, 'nickel', th=0.008)

def core():
    m = part('core_cowl', explode=(0, 0, 1.25))                              # inner bypass wall; its front lip is the booster case
    m.stl('core_cowl', 'alu', at())
    for x, tip in ((-0.345, 0.428), (-0.435, 0.444), (-0.525, 0.458)): row(m, x, 64, 0.29, tip, 0.04, -25, -25, 'alu', th=0.003)
    m = part('core_case', explode=(0, 0, 0.7))
    m.stl('core_case', 'hot', at())
    for i in range(9):                                                       # compressor stator rows
        x = -0.65 - 0.06 * i; f = (-0.59 - x) / 0.57
        row(m, x, 48, lerp(0.226, 0.274, f), lerp(0.350, 0.312, f), 0.028, -20, -20, 'alu', th=0.003)
    row(m, -1.465, 40, 0.25, 0.352, 0.035, 50, 50, 'nickel', th=0.010)       # HP nozzle guide vanes
    for i in range(4):                                                       # LP turbine stators
        x = -1.67 - 0.10 * i; f = (-1.58 - x) / 0.39
        row(m, x, 56, lerp(0.232, 0.286, f), lerp(0.364, 0.432, f), 0.04, 40, 40, 'hot', th=0.006)
    m = part('combustor', explode=(0, 0, -1.4))                              # annular liner, 20 fuel nozzles off a ring manifold
    m.stl('liner', 'hot', at())
    m.torus(C + X * -1.16, X, 0.455, 0.012, 'brass', 64, 6)
    for k in range(20):
        a = 360 * k / 20
        m.sweep([P(-1.16, 0.455, a), P(-1.16, 0.395, a), P(-1.175, 0.32, a), P(-1.19, 0.30, a)], 0.008, 'steel', 6)
    m = part('exhaust', explode=(-1.4, 0, 0))
    m.stl('plug', 'hot', at())

def accessories():
    tower = P(-0.57, 0)
    m = part('radial_driveshaft', pivot=tower, axis=-Z, explode=(0, 0, -0.7))   # taken off the HP spool by the bevel pair
    m.stl('bevel_tower', 'brass', at(p=P(-0.57, 0.135), M=S))
    m.tube(P(-0.57, 0.14), P(-0.57, 0.84), 0.016, 'steel', 12)
    m.stl('bevel_agb', 'brass', at(p=P(-0.57, 0.835), M=Matrix.Rotation(pi, 4, 'X') @ S))
    m = part('accessory_gearbox', explode=(0, 0, -1.1))
    m.box(P(-0.50, 0.895), (0.52, 0.30, 0.065), 'alu')
    for x, y, r, l, mat in ((-0.20, 0.08, 0.030, 0.10, 'dark'), (-0.20, -0.08, 0.026, 0.09, 'red'),      # starter, fuel pump
                            (-0.80, 0.08, 0.032, 0.11, 'dark'), (-0.80, -0.08, 0.024, 0.09, 'alu')):     # generator, oil pump
        c = P(x, 0.895) + V((0, y, 0.005)); m.disc(c, X, r, l, mat, 20)

def stand():
    m = part('stand', explode=(0, -1.6, 0))
    m.box(V((-0.90, 0, 0.02)), (2.0, 1.2, 0.04), 'dark')
    for x, R in ((-0.20, 1.0), (-1.62, 0.49)):
        arc = [P(x, R, a) for a in range(-150, -29, 15)]
        m.sweep(arc, 0.025, 'dark', 10)
        for a in (-125, -55): m.tube(V((P(x, R, a).x, P(x, R, a).y, 0.04)), P(x, R, a), 0.03, 'dark', 10)

def build():
    nacelle(); fan(); lp_spool(); hp_spool(); core(); accessories(); stand()

VIEWS = {'left_34': ((2.6, 5.0, 3.4), (-0.85, 0, 0.95), 45), 'front': ((3.6, 1.2, 1.5), (0, 0, CZ), 35),
         'core': ((-0.8, 2.2, 2.2), (-1.0, 0, CZ), 35), 'agb': ((0.6, -1.6, 0.9), (-0.55, 0, 0.6), 35)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['left_34'])
