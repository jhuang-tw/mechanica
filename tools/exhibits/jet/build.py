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

def foil(chord, th, camber=0.0, n=6):
    """Cambered blade section (NACA-like thickness, rounded leading edge at -chord/2, thin trailing edge) as a (u, v) loop.
    th is the absolute maximum thickness, camber the mean-line rise as a share of the chord."""
    pts = []
    for i in range(n + 1):
        s = 0.5 * (1 - cos(pi * i / n))                                     # cosine spacing: more points round the nose
        yt = 5 * th * (0.2969 * s ** 0.5 - 0.126 * s - 0.3516 * s * s + 0.2843 * s ** 3 - 0.1036 * s ** 4)
        pts.append((chord * (s - 0.5), camber * chord * 4 * s * (1 - s), yt))
    up = [(u, c + t) for u, c, t in pts]
    lo = [(u, c - t) for u, c, t in pts[-2:0:-1]]
    return up + lo

def cut(a):
    """True inside the cutaway quadrant (Blender upper left): stationary parts leave it open."""
    a %= 360; return 0 < a < 90

def row(m, x, n, r0, r1, chord, st0, st1, mat, th=0.004, secs=3, sweep=0.0, phase=0.0, fn=4, camber=(0.06, 0.04), open_=False,
        shroud=0.0, platform=0.0):
    """Ring of n blades between radii r0 and r1 at axial station x; stagger st0 -> st1 degrees from the axis.
    chord: number, (hub, tip) or a function of the span share f; sweep: axial lean of the stacking line at the tip, or a function of f.
    open_: leave the cutaway quadrant empty (stators); shroud / platform: axial width of a ring at the tip / hub (0 = none)."""
    ch_f = chord if callable(chord) else (lambda f, c=chord: lerp(*c, f) if isinstance(c, tuple) else c)
    sw_f = sweep if callable(sweep) else (lambda f, s=sweep: s * f)
    cb0, cb1 = camber if isinstance(camber, tuple) else (camber, camber)
    for k in range(n):
        ad = 360 * (k + phase) / n
        if open_ and cut(ad): continue
        a = radians(ad); d = V((0, cos(a), sin(a))); t = V((0, -sin(a), cos(a)))
        rings = []
        for i in range(secs):
            f = i / (secs - 1); r = r0 + (r1 - r0) * f; st = st0 + (st1 - st0) * f; ch = ch_f(f)
            sg = 1 if st >= 0 else -1; st = radians(st)
            cd = X * cos(st) + t * sin(st); nd = t * cos(st) - X * sin(st); c = C + X * (x - sw_f(f)) + d * r
            rings.append([m.bm.verts.new(c - cd * u + nd * v * sg) for u, v in foil(ch, th * (1 - 0.45 * f), lerp(cb0, cb1, f), fn)])
        for a_, b_ in zip(rings, rings[1:]): m.bridge(a_, b_, mat)
        m.cap(rings[0], mat, True); m.cap(rings[-1], mat)
    if shroud: band(m, x - sw_f(1), r1 - 0.002, r1 + 0.006, shroud, mat, 0, 360, max(48, n))
    if platform: band(m, x, r0 - 0.008, r0 + 0.002, platform, mat, 0, 360, max(48, n))

def band(m, x, r0, r1, w, mat, a0=90, a1=360, seg=None, x1=None):
    """Ring of rectangular section (r0..r1 radially, w axially) from angle a0 to a1 (degrees, the P() convention); x1 tapers it."""
    seg = seg or max(8, int((a1 - a0) / 4))
    full = (a1 - a0) % 360 == 0; x1 = x if x1 is None else x1
    loops = []
    for i in range(seg if full else seg + 1):
        a = a0 + (a1 - a0) * i / seg
        loops.append([m.bm.verts.new(P(xx, r, a)) for xx, r in ((x + w / 2, r0), (x + w / 2, r1), (x1 - w / 2, r1), (x1 - w / 2, r0))])
    pairs = list(zip(loops, loops[1:])) + ([(loops[-1], loops[0])] if full else [])
    for l0, l1 in pairs: m.bridge(l0, l1, mat)
    if not full: m.cap(loops[0], mat); m.cap(loops[-1], mat, True)

def bolts(m, x, r, n, mat, a0=90, a1=360, size=0.007, axis=None):
    """Bolt heads on a flange face: small hex prisms around the axis."""
    for k in range(n):
        a = a0 + (a1 - a0) * (k + 0.5) / n
        m.disc(P(x, r, a), axis or X, size, size * 0.8, mat, 6)

def flange(m, x, r, mat, h=0.014, w=0.010, n=0, a0=90, a1=360, bolt='steel'):
    """Bolted casing joint: a raised ring plus n bolt heads on its front face (open quadrant left out by default)."""
    band(m, x, r - 0.004, r + h, w, mat, a0, a1)
    if n: bolts(m, x + w / 2 + 0.002, r + h * 0.55, n, bolt, a0, a1, size=0.005)

def arc_pts(x, r, a0, a1, step=6): return [P(x, r, a0 + (a1 - a0) * i / max(1, int(abs(a1 - a0) / step))) for i in range(int(abs(a1 - a0) / step) + 1)]

def pipe(m, pts, rad, mat, clamps=0, seg=8):
    """Smoothed tube through control points with optional clamp collars."""
    path = smooth(pts, 5); m.sweep(path, rad, mat, seg)
    for k in range(clamps):
        i = int((k + 1) * (len(path) - 1) / (clamps + 1)); tgt = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        m.disc(path[i], tgt, rad * 1.7, rad * 2.2, 'steel', 8)

def lerp(a, b, f): return a + (b - a) * f

def rc(x):
    """Outer radius of the core case (cad.py core_case profile) at axial station x."""
    zs = [-0.560, -1.150, -1.190, -1.450, -1.490, -1.580, -1.960, -2.060]; rs = [0.368, 0.328, 0.418, 0.418, 0.368, 0.380, 0.450, 0.436]
    if x >= zs[0]: return rs[0]
    for z0, z1, r0, r1 in zip(zs, zs[1:], rs, rs[1:]):
        if z1 <= x <= z0: return lerp(r0, r1, (z0 - x) / (z0 - z1))
    return rs[-1]

def rot_x(a): return Matrix.Rotation(radians(a), 3, 'X')   # box axes: (axial, radial, tangential) at angle a

# ---------------------------------------------------------------- nacelle and fan case (fixed, cut away)
def nacelle():
    part('nacelle_inlet', explode=(1.1, 0, 0)).stl('inlet', 'paint', at())
    for pid, s in (('fan_cowl_left', 1), ('fan_cowl_right', -1)):           # hinged at the top, open like doors
        m = part(pid, pivot=P(-0.32, 0.975, 90), axis=X, explode=(0, s * 0.9, 0.35))
        m.stl('fan_cowl_' + 'lr'[s < 0], 'paint', at())
        if s < 0:                                                            # hook latches along the bottom split line
            for x in (-0.05, -0.32, -0.58):
                ro = lerp(0.990, 0.955, (0.05 - x) / 0.75)
                rbox(m, P(x, ro - 0.002, -88.5), (0.11, 0.008, 0.035), 0.002, 'dark', rot_x(-88.5))
    m = part('thrust_reverser', explode=(-1.3, 0, 0))
    m.stl('reverser', 'paint', at())                                         # hollow sleeve: outer and inner skins
    for a0, a1 in ((100, 233), (307, 358)):                                  # cascade boxes under the sleeve; beams top and bottom
        for i in range(9): band(m, -0.725 - 0.025 * i, 0.832, 0.888, 0.004, 'dark', a0, a1)
        for k in range(int((a1 - a0) / 7) + 1): band(m, -0.825, 0.830, 0.890, 0.21, 'dark', a0 + 7 * k - 0.4, a0 + 7 * k + 0.4, 1)
    for a in (150, 210, 330):                                                # sleeve actuators
        m.tube(P(-0.705, 0.902, a), P(-0.90, 0.902, a), 0.009, 'steel', 10); m.tube(P(-0.705, 0.902, a), P(-0.80, 0.902, a), 0.013, 'dark', 10)

    m = part('fan_case', explode=(0, 0, 2.0))
    m.stl('fan_case', 'alu', at())
    row(m, -0.50, 44, 0.49, 0.81, 0.13, -12, -18, 'alu', th=0.008, camber=0.10, open_=True)   # outlet guide vanes take the swirl out
    m.box(P(-0.535, 0.65), (0.16, 0.05, 0.32), 'alu')                        # bottom strut: the radial drive shaft runs inside
    flange(m, 0.045, 0.862, 'alu', n=60); flange(m, -0.685, 0.852, 'alu', n=60)
    for x in (-0.18, -0.42): band(m, x, 0.858, 0.868, 0.012, 'alu')         # containment stiffeners
    pipe(m, arc_pts(-0.12, 0.880, 93, 357), 0.008, 'black', clamps=10)        # engine harness
    pipe(m, arc_pts(-0.60, 0.872, 93, 357), 0.006, 'steel', clamps=10)        # fuel / oil line
    ecu = P(-0.33, 0.888, 200)                                               # engine control unit on shock mounts
    rbox(m, ecu, (0.22, 0.042, 0.15), 0.008, 'dark', rot_x(200))
    for dx in (-0.08, 0.08):
        for da in (-4, 4): m.disc(P(-0.33 + dx, 0.866, 200 + da), V(P(0, 1, 200 + da) - P(0, 0, 200 + da)), 0.008, 0.012, 'black', 8)
    for dx in (-0.05, 0.0, 0.05): m.disc(P(-0.215 + 0.0, 0.888, 200 + dx * 60), X, 0.008, 0.02, 'brass', 10)   # connectors
    pipe(m, [P(-0.12, 0.880, 205), P(-0.16, 0.888, 203), P(-0.205, 0.888, 200)], 0.007, 'black')
    tank = [P(-0.20 - 0.03 * i, 0.892, 330) for i in range(9)]               # oil tank with sight glass
    m.sweep(tank, [0.012, 0.026, 0.032, 0.034, 0.034, 0.034, 0.032, 0.026, 0.012], 'alu', 16)
    m.disc(P(-0.32, 0.926, 330), V(P(0, 1, 330) - P(0, 0, 330)), 0.009, 0.006, 'brass', 12)
    pipe(m, [P(-0.44, 0.892, 330), P(-0.52, 0.890, 318), P(-0.50, 0.892, 300)], 0.006, 'steel', clamps=1)

def fan():
    m = part('fan', pivot=C, axis=X, explode=(2.0, 0, 0))
    m.stl('spinner', 'black', at()); m.stl('fan_disk', 'ti', at())
    # wide-chord fan: 24 blades, strong twist root -> tip, chord widest out at three quarters span, tip swept back
    row(m, 0.085, 24, 0.258, 0.795, lambda f: 0.20 + 0.30 * f - 0.15 * f * f, 18, 62, 'ti', th=0.024, secs=10, fn=7,
        sweep=lambda f: 0.07 * f * f - 0.02 * f, camber=(0.11, 0.025))
    # painted spiral on the spinner (shows the ground crew it turns); spinner profile r = R (1 - u)^0.8 from cad.py
    R, z0, L = 0.262, 0.200, 0.420; w = 0.012
    def sp(u, a, dz=0.0):
        uu = min(max(u + dz / L, 0), 1); r = R * (1 - uu) ** 0.8 + 0.0015
        return C + X * (z0 + L * uu) + V((0, r * cos(radians(a)), r * sin(radians(a))))
    prev = None
    for i in range(61):
        u = 0.04 + 0.80 * i / 60; a = 300 * i / 60
        cur = [m.bm.verts.new(sp(u, a, -w)), m.bm.verts.new(sp(u, a, w))]
        if prev: m.face([prev[0], cur[0], cur[1], prev[1]], 'paint')
        prev = cur

def lp_spool():
    m = part('booster', pivot=C, axis=X, explode=(0.7, 0, 0))
    m.stl('booster', 'ti', at())
    for x, tip in ((-0.30, 0.420), (-0.39, 0.436), (-0.48, 0.452)): row(m, x, 56, 0.282, tip, 0.045, 30, 50, 'ti', camber=(0.09, 0.05))
    part('lp_shaft', pivot=C, axis=X, explode=(0, 0, -0.35)).stl('lp_shaft', 'steel', at())
    m = part('lp_turbine', pivot=C, axis=X, explode=(-0.7, 0, 0))
    m.stl('lpt_drum', 'nickel', at())
    for i in range(4):                                                       # shrouded blades: the tip shrouds lock into a ring
        x = -1.62 - 0.10 * i; f = (-1.58 - x) / 0.39
        row(m, x, 64, lerp(0.228, 0.282, f), lerp(0.356, 0.426, f), 0.05, -30, -52, 'nickel', th=0.007, camber=(0.16, 0.12),
            shroud=0.026, platform=0.05)
        m.disc(C + X * x, X, lerp(0.228, 0.282, f) - 0.005, 0.03, 'nickel', 32, r_in=0.05)

def hp_spool():
    m = part('hp_compressor', pivot=C, axis=X, explode=(0, 0, -0.95))
    m.stl('hpc_drum', 'ti', at())
    for i in range(9):                                                       # blades get smaller and more numerous aft
        x = -0.62 - 0.06 * i; f = (-0.59 - x) / 0.57
        row(m, x, int(lerp(36, 72, i / 8)), lerp(0.222, 0.270, f), lerp(0.343, 0.305, f), lerp(0.040, 0.024, i / 8), 30, 52, 'ti',
            th=0.0032, camber=(0.08, 0.05), sweep=0.004)
    m = part('hp_shaft', pivot=C, axis=X, explode=(0, 0, -0.6))
    m.stl('hp_shaft', 'steel', at())
    m.stl('bevel_hp', 'brass', at(-0.635))                                   # drives the radial shaft
    m = part('hp_turbine', pivot=C, axis=X, explode=(0, 0, -0.95))
    m.stl('hpt_disk', 'nickel', at())
    row(m, -1.50, 60, 0.252, 0.345, 0.045, -38, -50, 'nickel', th=0.012, camber=(0.20, 0.16), platform=0.05, fn=5)   # thick, hot, cooled

def core():
    m = part('core_cowl', explode=(0, 0, 1.25))                              # inner bypass wall; its front lip is the booster case
    m.stl('core_cowl', 'alu', at())
    for x, tip in ((-0.345, 0.428), (-0.435, 0.444), (-0.525, 0.458)):
        row(m, x, 64, 0.29, tip, 0.04, -25, -25, 'alu', th=0.003, camber=0.08, open_=True)
    m = part('core_case', explode=(0, 0, 0.7))
    m.stl('core_case', 'hot', at())
    for i in range(9):                                                       # compressor stator rows
        x = -0.65 - 0.06 * i; f = (-0.59 - x) / 0.57
        row(m, x, int(lerp(44, 80, i / 8)), lerp(0.226, 0.274, f), lerp(0.350, 0.312, f), lerp(0.034, 0.022, i / 8), -20, -24, 'alu',
            th=0.003, camber=0.08, open_=True)
    row(m, -1.465, 40, 0.25, 0.352, 0.035, 50, 50, 'nickel', th=0.012, camber=0.18, open_=True, fn=5)   # HP nozzle guide vanes
    for i in range(4):                                                       # LP turbine stators
        x = -1.67 - 0.10 * i; f = (-1.58 - x) / 0.39
        row(m, x, 56, lerp(0.232, 0.286, f), lerp(0.364, 0.432, f), 0.04, 40, 40, 'hot', th=0.007, camber=0.15, open_=True)
    for x in (-0.566, -0.86, -1.186, -1.454, -1.584, -1.954): flange(m, x, rc(x), 'hot', n=40)   # bolted case joints
    for i in range(4):                                                       # variable stator vanes: unison ring + one lever per vane
        x = -0.65 - 0.06 * i; r = rc(x)
        band(m, x + 0.016, r + 0.026, r + 0.034, 0.010, 'steel', 92, 358)
        for k in range(28):
            a = 92 + 266 * (k + 0.5) / 28
            m.disc(P(x, r + 0.004, a), V(P(0, 1, a) - P(0, 0, a)), 0.006, 0.008, 'steel', 6)
            m.tube(P(x, r + 0.008, a), P(x + 0.016, r + 0.030, a), 0.0025, 'steel', 4)
    act = [P(-0.60, rc(-0.6) + 0.055, 205), P(-0.84, rc(-0.84) + 0.055, 205)]   # VSV actuator and its bell-crank links
    m.tube(*act, 0.013, 'steel', 12); m.tube(act[0], lerp(act[0], act[1], 0.45), 0.018, 'dark', 12)
    for i in range(4):
        x = -0.65 - 0.06 * i; m.tube(P(x + 0.016, rc(x) + 0.032, 203), P(x + 0.016, rc(-0.6) + 0.055, 205), 0.004, 'steel', 6)
    for i in range(0, 9, 2): m.disc(P(-0.65 - 0.06 * i + 0.03, rc(-0.68 - 0.06 * i) + 0.006, 235), V(P(0, 1, 235) - P(0, 0, 235)), 0.010, 0.014, 'steel', 8)   # borescope ports
    pipe(m, [P(-0.92, rc(-0.92), 230), P(-0.95, 0.40, 228), P(-1.05, 0.44, 222), P(-1.12, 0.455, 215)], 0.022, 'steel', clamps=1)   # bleed duct
    for a, mat, rad in ((250, 'steel', 0.006), (258, 'steel', 0.005), (196, 'black', 0.008)):          # oil supply / scavenge, harness
        pipe(m, [P(-0.62, rc(-0.62) + 0.012, a), P(-0.90, rc(-0.90) + 0.020, a), P(-1.12, 0.432, a), P(-1.44, 0.434, a),
                 P(-1.56, 0.425, a), P(-1.64, rc(-1.64) + 0.006, a)], rad, mat, clamps=5)
    m = part('combustor', explode=(0, 0, -1.4))                              # annular liner, 20 fuel nozzles off a ring manifold
    m.stl('liner', 'hot', at())
    m.torus(C + X * -1.16, X, 0.455, 0.012, 'brass', 64, 6)
    for k in range(20):
        a = 360 * k / 20
        m.sweep([P(-1.16, 0.455, a), P(-1.16, 0.395, a), P(-1.175, 0.32, a), P(-1.19, 0.30, a)], 0.008, 'steel', 6)
        m.disc(P(-1.16, 0.43, a), V(P(0, 1, a) - P(0, 0, a)), 0.016, 0.008, 'steel', 8)              # nozzle mounting flange
        m.disc(P(-1.187, 0.295, a), X, 0.016, 0.012, 'steel', 12, r_in=0.008)                         # swirler cup in the dome
    for a in (200, 340):                                                     # igniter plugs
        m.tube(P(-1.22, 0.47, a), P(-1.22, 0.345, a), 0.007, 'steel', 8); m.tube(P(-1.22, 0.47, a), P(-1.22, 0.50, a), 0.012, 'black', 10)
    m.tube(P(-1.12, 0.455, 270), P(-0.95, 0.43, 272), 0.007, 'steel', 8)    # fuel feed into the manifold
    m = part('exhaust', explode=(-1.4, 0, 0))
    m.stl('plug', 'hot', at())

def accessories():
    tower = P(-0.57, 0)
    m = part('radial_driveshaft', pivot=tower, axis=-Z, explode=(0, 0, -0.7))   # taken off the HP spool by the bevel pair
    m.stl('bevel_tower', 'brass', at(p=P(-0.57, 0.135), M=S))
    m.tube(P(-0.57, 0.14), P(-0.57, 0.84), 0.016, 'steel', 12)
    m.stl('bevel_agb', 'brass', at(p=P(-0.57, 0.835), M=Matrix.Rotation(pi, 4, 'X') @ S))
    m = part('accessory_gearbox', explode=(0, 0, -1.1))
    band(m, -0.57, 0.866, 0.918, 0.13, 'alu', 232, 308, 26)                  # curved casting hugging the fan case
    for x in (-0.50, -0.64): band(m, x, 0.864, 0.921, 0.010, 'alu', 231, 309, 26)   # mating flanges
    def acc(a, front, r, l, mat, pad=0.006):
        x0 = -0.505 if front else -0.635; s = 1 if front else -1
        m.disc(P(x0 + s * 0.006, 0.892, a), X, r + 0.006, 0.012, 'alu', 20)                        # mounting pad + V-band clamp
        m.disc(P(x0 + s * (0.012 + l / 2), 0.892, a), X, r, l, mat, 20)
        m.disc(P(x0 + s * (0.012 + l), 0.892, a), X, r * 0.6, 0.012, mat, 16)
        return P(x0 + s * (0.012 + l), 0.892, a)
    acc(244, True, 0.026, 0.10, 'dark')                                      # air starter
    acc(296, True, 0.022, 0.07, 'red'); rbox(m, P(-0.43, 0.892, 296), (0.06, 0.05, 0.07), 0.006, 'red', rot_x(296))   # fuel pump + metering unit
    acc(268, True, 0.015, 0.04, 'black')                                     # control alternator
    acc(248, False, 0.025, 0.11, 'dark')                                     # integrated drive generator
    acc(272, False, 0.018, 0.07, 'steel')                                    # hydraulic pump
    acc(294, False, 0.020, 0.08, 'alu')                                      # lube and scavenge pump
    pipe(m, [P(-0.43, 0.892, 296), P(-0.45, 0.915, 300), P(-0.60, 0.918, 285), P(-0.70, 0.905, 278)], 0.006, 'steel', clamps=1)
    pipe(m, [P(-0.72, 0.892, 294), P(-0.70, 0.905, 305), P(-0.52, 0.895, 315)], 0.006, 'steel')

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
         'core': ((-0.8, 2.2, 2.2), (-1.0, 0, CZ), 35), 'agb': ((0.6, -1.6, 0.9), (-0.55, 0, 0.6), 35),
         'fan_close': ((1.3, 0.5, 1.6), (0.05, 0, 1.25), 40), 'hpc_close': ((-0.55, 0.9, 1.75), (-0.85, 0.1, 1.35), 40),
         'turb_close': ((-1.35, 0.95, 1.75), (-1.65, 0.1, 1.35), 40), 'rear': ((-3.6, 1.4, 1.6), (-1.6, 0, CZ), 35),
         'under': ((-0.4, -1.4, 0.25), (-0.6, 0, 0.6), 35),
         'right': ((-0.4, -3.2, 1.3), (-0.7, 0, 0.9), 35), 'agb_close': ((-0.1, -1.0, 0.05), (-0.57, 0, 0.3), 40)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['left_34'])
