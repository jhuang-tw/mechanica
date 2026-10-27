# Car exhibit (generic compact front-wheel-drive sedan), built from scratch for Mechanica: one GLB node per semantic part.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/car/build.py -- public/exhibits/car [--preview]
# Run tools/exhibits/car/cad.py first (engine, gearbox, differential, wheels and discs come from its STLs).
# Model frame (Blender): metres, ground z = 0, front = +x, car's left = +y. glTF export: front +x, up +y, car's right = +z.
# Node origins are rotation centres; spin axes are written as extras.axis (glTF axes). Front wheels hang on their steering
# knuckle (knuckle turns about the kingpin, the wheel spins inside it); brake discs hang on their wheel.
# The body shell, seats and dashboard come from Tripo (tools/tripo-ref) and are added when those GLBs exist.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths
import common

S = Matrix.Scale(0.001, 4)
NY = Matrix.Rotation(pi / 2, 4, 'X') @ S      # CAD z -> Blender -y, CAD y -> +z (shafts across the car)
PY = Matrix.Rotation(-pi / 2, 4, 'X') @ S     # CAD z -> Blender +y
def at(p, M=S, rz=0): return Matrix.Translation(p) @ M @ Matrix.Rotation(rz, 4, 'Z')

# ---------------------------------------------------------------- layout (metres)
WR = 0.316                                     # 205/55 R16
FA, RA, TW = 1.35, -1.35, 0.765                # axle x, half track
CRANK = V((1.56, 0.12, 0.40))                  # crank centre, crank along y, cylinder 1 at +y
STROKE, ROD = 0.088, 0.140
CYL_Y = [CRANK.y + (1.5 - i) * 0.088 for i in range(4)]
TDC = [True, False, False, True]               # cylinders 1 and 4 up at rest
DECK = CRANK.z + STROKE / 2 + ROD + 0.032
CAM_Z = DECK + 0.095
DIFF = V((FA, -0.33, WR))
GEARS = [(24, 74), (33, 65), (41, 57), (47, 51), (53, 45)]
GEAR_Y = [-0.135 - 0.034 * k for k in range(5)]
def output_shaft_xz():   # circle intersection: 122.5 mm from the input (crank) axis, 118.5 mm from the diff axis
    a, b = V((CRANK.x, CRANK.z)), V((DIFF.x, DIFF.z)); r0, r1 = 0.1225, 0.1185
    d = (b - a).length; l = (r0 * r0 - r1 * r1 + d * d) / (2 * d); h = (r0 * r0 - l * l) ** 0.5
    m = a + (b - a) * (l / d); n = V((-(b - a).y, (b - a).x)) / d
    p = m + n * h if (m + n * h).y < (m - n * h).y else m - n * h    # the lower solution, under the crank
    return p
OS2 = output_shaft_xz(); OUT_AX = V((OS2.x, 0, OS2.y))
PULLEY_Y = CRANK.y + 0.226
DRIVER_Y = 0.37                                 # left-hand drive
SW = V((0.55, DRIVER_Y, 0.95))                  # steering wheel centre
RACK = V((1.20, 0, 0.36))
PINION = V((RACK.x, DRIVER_Y - 0.05, RACK.z + 0.03))

common.MATS.update({   # base colour (linear), metallic, roughness
    'alu':    ((0.62, 0.63, 0.65), 1.0, 0.38),
    'cast':   ((0.12, 0.12, 0.13), 0.8, 0.55),
    'steel':  ((0.50, 0.51, 0.53), 1.0, 0.30),
    'black':  ((0.015, 0.015, 0.017), 0.0, 0.55),
    'rubber': ((0.02, 0.02, 0.02), 0.0, 0.85),
    'red':    ((0.55, 0.04, 0.03), 0.2, 0.35),
    'brass':  ((0.60, 0.42, 0.15), 1.0, 0.35),
    'spring': ((0.70, 0.55, 0.05), 0.3, 0.40),
    'belt':   ((0.03, 0.03, 0.035), 0.0, 0.70),
})

def helix(m, a, b, r, turns, wire, mat):
    """Coil spring from a to b (any direction)."""
    ax = (b - a); L = ax.length; ax.normalize()
    u = ax.cross(V((0, 0, 1)) if abs(ax.z) < 0.9 else V((1, 0, 0))).normalized(); w = ax.cross(u)
    n = int(turns * 16)
    m.sweep([a + ax * (L * i / n) + (u * cos(TAU * turns * i / n) + w * sin(TAU * turns * i / n)) * r for i in range(n + 1)], wire, mat, 6)

def band(m, centres, y, width, mat):
    """Closed flat belt around pulleys given as (x, z, r) in the xz plane at y, wound the convex way (outer tangents)."""
    pts = []
    n = len(centres)
    for i in range(n):
        (x0, z0, r0), (x1, z1, r1) = centres[i], centres[(i + 1) % n]
        d = V((x1 - x0, z1 - z0)); L = d.length; d /= L
        k = (r0 - r1) / L; nrm = V((d.x * k - d.y * (1 - k * k) ** 0.5, d.y * k + d.x * (1 - k * k) ** 0.5))   # outer tangent normal
        pts.append((V((x0, z0)) + nrm * r0, V((x1, z1)) + nrm * r1, nrm))
    path = []
    for i in range(n):   # tangent line, then the arc on the next pulley
        a, b, nrm = pts[i]; path += [a, b]
        x, z, r = centres[(i + 1) % n]; c = V((x, z)); a0 = atan2(nrm.y, nrm.x); a1 = atan2(pts[(i + 1) % n][2].y, pts[(i + 1) % n][2].x)
        while a1 > a0: a1 -= TAU
        steps = max(2, int((a0 - a1) / 0.2))
        path += [c + V((cos(a0 + (a1 - a0) * j / steps), sin(a0 + (a1 - a0) * j / steps))) * r for j in range(1, steps)]
    rings = []
    for i, p in enumerate(path):
        q = path[(i + 1) % len(path)]; o = path[i - 1]; t = (q - o).normalized(); nn = V((t.y, -t.x)) * -1
        rings.append([m.bm.verts.new(V((p.x + nn.x * dn, y + dy, p.y + nn.y * dn))) for dn, dy in ((0, -width / 2), (0.004, -width / 2), (0.004, width / 2), (0, width / 2))])
    for i in range(len(rings)): m.bridge(rings[i], rings[(i + 1) % len(rings)], mat)

# ---------------------------------------------------------------- engine
def engine():
    for pid, mat, ex in (('block', 'alu', (0, 0, 0)), ('head', 'alu', (0, 0, 0.35)), ('valve_cover', 'black', (0, 0, 0.6)), ('oil_pan', 'cast', (0, 0, -0.35))):
        part(pid, explode=ex).stl(pid, mat, at(CRANK))
    m = part('crankshaft', pivot=CRANK, axis=V((0, -1, 0)), explode=(0, 0, -0.55))
    m.stl('crankshaft', 'steel', at(CRANK, NY, pi / 2))                       # throw 0 (cylinders 1, 4) points up
    fw = part('flywheel', pivot=CRANK + V((0, -0.218, 0)), axis=V((0, -1, 0)), explode=(0, -0.3, 0))
    fw.stl('flywheel', 'steel', at(CRANK + V((0, -0.218, 0)), NY))
    for i, (y, up) in enumerate(zip(CYL_Y, TDC), 1):
        pin_z = CRANK.z + (STROKE / 2 if up else -STROKE / 2)
        pin = V((CRANK.x, y, pin_z)); wrist = pin + V((0, 0, ROD))
        p = part(f'piston_{i}', pivot=wrist, explode=(0, 0, 0.9))
        p.stl('piston', 'alu', at(wrist, S, pi / 2))
        r = part(f'conrod_{i}', pivot=pin, axis=V((0, -1, 0)), explode=(0, 0, 0.6))
        r.stl('conrod', 'steel', at(pin, NY))
    for pid, dx, ex in (('camshaft_intake', -0.035, (-0.1, 0, 0.75)), ('camshaft_exhaust', 0.035, (0.1, 0, 0.75))):
        c = V((CRANK.x + dx, CRANK.y, CAM_Z))
        m = part(pid, pivot=c, axis=V((0, -1, 0)), explode=ex)
        m.stl('cam_in' if dx < 0 else 'cam_ex', 'steel', at(c, NY))
        m.tube(c + V((0, 0.19, 0)), V((c.x, PULLEY_Y, c.z)), 0.012, 'steel', 10)
        m.stl('pulley_cam', 'black', at(V((c.x, PULLEY_Y, c.z)), NY))
    m = part('crank_pulley', pivot=V((CRANK.x, PULLEY_Y, CRANK.z)), parent='crankshaft', axis=V((0, -1, 0)), explode=(0, 0.25, 0))
    m.stl('pulley_crank', 'black', at(V((CRANK.x, PULLEY_Y, CRANK.z)), NY))
    m = part('timing_belt', explode=(0, 0.45, 0.1))
    idler = (CRANK.x + 0.075, (CRANK.z + CAM_Z) / 2 - 0.02, 0.028)
    band(m, [(CRANK.x - 0.035, CAM_Z, 0.06), (CRANK.x + 0.035, CAM_Z, 0.06), idler, (CRANK.x, CRANK.z, 0.03)], PULLEY_Y, 0.024, 'belt')
    m.disc(V((idler[0], PULLEY_Y, idler[1])), Y, idler[2] - 0.004, 0.028, 'steel', 24)

    m = part('intake_manifold', explode=(-0.45, 0, 0.1))                      # plenum behind the engine, runners into the head
    plen = V((CRANK.x - 0.24, CRANK.y, DECK + 0.02))
    m.tube(plen + V((0, -0.22, 0)), plen + V((0, 0.22, 0)), 0.045, 'black', 16)
    m.tube(plen + V((0, -0.24, 0.02)), plen + V((0, -0.33, 0.05)), 0.035, 'black', 14)        # throttle body
    for y in CYL_Y: m.sweep([plen + V((0, y - CRANK.y, 0)), plen + V((0.07, y - CRANK.y, 0.10)), V((CRANK.x - 0.118, y, DECK + 0.06))], 0.019, 'black', 10)
    m = part('exhaust_manifold', explode=(0.45, 0, 0))
    col = V((CRANK.x + 0.20, CRANK.y - 0.02, CRANK.z - 0.05))
    for y in CYL_Y: m.sweep([V((CRANK.x + 0.118, y, DECK + 0.05)), V((CRANK.x + 0.17, y, DECK)), col + V((0, (y - CRANK.y) * 0.25, 0.06))], 0.017, 'cast', 10)
    m.tube(col + V((0, 0, 0.08)), col + V((0, 0, -0.08)), 0.03, 'cast', 12)
    m = part('exhaust', explode=(0, 0, -0.4))
    path = [col + V((0, 0, -0.08)), V((col.x - 0.15, col.y, 0.20)), V((0.6, -0.05, 0.16)), V((-0.3, -0.05, 0.16)), V((-0.8, -0.05, 0.17)), V((-1.5, -0.30, 0.22))]
    m.sweep(path, 0.025, 'steel', 10)
    m.tube(V((0.25, -0.05, 0.16)), V((-0.05, -0.05, 0.16)), 0.06, 'steel', 16)                  # catalytic converter
    mf = V((-1.75, -0.40, 0.25)); m.disc(mf, V((1, 0, 0)), 0.11, 0.42, 'steel', 20)            # muffler
    m.tube(mf + V((-0.21, 0, 0)), mf + V((-0.33, 0, -0.02)), 0.025, 'steel', 10)
    m = part('radiator', explode=(0.5, 0, 0))
    rc = V((2.02, 0.0, 0.48))
    m.box(rc, (0.03, 0.62, 0.40), 'black'); m.box(rc + V((0, 0.33, 0)), (0.05, 0.05, 0.42), 'black'); m.box(rc + V((0, -0.33, 0)), (0.05, 0.05, 0.42), 'black')
    for k in range(14): m.box(rc + V((0.016, -0.29 + k * 0.045, 0)), (0.004, 0.02, 0.38), 'alu')
    m.sweep([rc + V((-0.02, 0.30, 0.14)), V((1.85, 0.28, 0.66)), V((CRANK.x + 0.12, 0.25, DECK + 0.08))], 0.016, 'rubber', 8)   # top hose
    m = part('battery', explode=(0, -0.3, 0.2))
    m.box(V((1.80, -0.45, 0.66)), (0.24, 0.17, 0.19), 'black'); [m.disc(V((1.80 + dx, -0.45, 0.76)), V((0, 0, 1)), 0.01, 0.02, 'red' if dx > 0 else 'steel', 10) for dx in (-0.08, 0.08)]

# ---------------------------------------------------------------- gearbox and final drive
def transmission():
    m = part('gearbox', explode=(0, -0.45, 0.2))
    I = V((CRANK.x, 0, CRANK.z)); fy = CRANK.y - 0.218
    m.sweep([I + V((0, fy - 0.02, 0)), I + V((0, fy - 0.07, 0))], [0.16, 0.165], 'alu', 32, caps=False)   # bellhousing
    m.disc(I + V((0, fy - 0.075, 0)), Y, 0.165, 0.01, 'alu', 32)
    c = (I + OUT_AX + DIFF) / 3
    m.box(V((c.x, -0.235, c.z)), (0.30, 0.17, 0.30), 'alu')
    m.disc(V((DIFF.x, -0.33, DIFF.z)), Y, 0.11, 0.10, 'alu', 32)
    inp = part('input_shaft', pivot=I + V((0, fy, 0)), axis=V((0, -1, 0)), explode=(0.15, -0.6, 0.3))
    inp.tube(I + V((0, fy, 0)), I + V((0, GEAR_Y[-1] - 0.03, 0)), 0.012, 'steel', 12)
    out = part('output_shaft', pivot=OUT_AX + V((0, GEAR_Y[0] + 0.03, 0)), axis=V((0, -1, 0)), explode=(-0.05, -0.6, -0.15))
    out.tube(OUT_AX + V((0, GEAR_Y[0] + 0.03, 0)), OUT_AX + V((0, DIFF.y - 0.03, 0)), 0.014, 'steel', 12)
    out.stl('pinion', 'steel', at(OUT_AX + V((0, DIFF.y, 0)), NY))
    for k, y in enumerate(GEAR_Y, 1):
        inp.stl(f'gear_in_{k}', 'steel', at(I + V((0, y, 0)), NY))
        g = part(f'gear_{k}', pivot=OUT_AX + V((0, y, 0)), axis=V((0, -1, 0)), explode=(-0.1, -0.6 - 0.05 * k, -0.25))
        g.stl(f'gear_out_{k}', 'brass' if k == 3 else 'steel', at(OUT_AX + V((0, y, 0)), NY))   # 3rd is engaged at rest
    d = part('differential', pivot=DIFF, axis=V((0, -1, 0)), explode=(-0.2, -0.5, -0.2))
    d.stl('diff', 'steel', at(DIFF, NY))
    for pid, y0, y1 in (('driveshaft_l', DIFF.y + 0.06, 0.62), ('driveshaft_r', DIFF.y - 0.06, -0.62)):
        s = part(pid, pivot=V((FA, y0, WR)), axis=V((0, -1, 0)), explode=(0, 0.3 if y1 > 0 else -0.3, -0.3))
        a, b = V((FA, y0, WR)), V((FA, y1, WR)); dy = 1 if y1 > y0 else -1
        s.tube(a + V((0, dy * 0.04, 0)), b - V((0, dy * 0.04, 0)), 0.013, 'steel', 12)
        for e in (a + V((0, dy * 0.035, 0)), b - V((0, dy * 0.035, 0))):
            s.disc(e, Y, 0.042, 0.07, 'black', 20)
            s.sweep([e + V((0, dy * 0.03, 0)), e + V((0, dy * 0.09, 0))] if e.y * dy < b.y * dy - 0.1 else [e - V((0, dy * 0.03, 0)), e - V((0, dy * 0.09, 0))], [0.035, 0.016], 'rubber', 14)

# ---------------------------------------------------------------- wheels, brakes, suspension, steering
def wheel(pid, c, side, parent, ex):
    w = part(pid, pivot=c, parent=parent, axis=V((0, -1, 0)), explode=ex)
    w.stl('rim', 'alu', at(c, NY if side > 0 else PY))                        # mounting face towards the car's centre
    w.torus(c, Y, WR - 0.056, 0.055, 'rubber', 64, 12, squash=1.45)
    d = part(pid.replace('wheel', 'disc'), pivot=c, parent=pid, axis=V((0, -1, 0)), explode=(0, -side * 0.2, 0))
    hub = c - V((0, side * 0.05, 0))
    d.stl('disc', 'cast', at(hub, NY if side > 0 else PY))
    cal = part(pid.replace('wheel', 'caliper'), parent=parent and parent, explode=(0, -side * 0.15, 0.25))
    cp = hub + V((-0.10, 0, 0.09))
    cal.box(cp, (0.10, 0.07, 0.05), 'red', Matrix.Rotation(radians(-42), 3, 'Y'))
    cal.box(cp + V((0, -side * 0.025, 0)), (0.07, 0.02, 0.07), 'red', Matrix.Rotation(radians(-42), 3, 'Y'))

def front_corner(side):
    s = 'l' if side > 0 else 'r'; c = V((FA, side * TW, WR)); k = c - V((0, side * 0.09, 0))
    kingpin = k + V((0, 0, 0))
    n = part(f'knuckle_f{s}', pivot=kingpin, axis=V((0, -side * 0.12, 1)), explode=(0, side * 0.25, 0))
    n.box(k, (0.05, 0.04, 0.22), 'cast'); n.disc(c - V((0, side * 0.075, 0)), Y, 0.045, 0.035, 'cast', 16)
    n.sweep([k + V((0, 0, -0.02)), k + V((-0.13, side * 0.01, -0.03))], 0.012, 'cast', 8)       # steering arm
    wheel(f'wheel_f{s}', c, side, f'knuckle_f{s}', (0.15, side * 0.6, 0))
    st = part(f'strut_f{s}', explode=(0, side * 0.2, 0.45))
    top = V((FA - 0.03, side * 0.56, 0.88)); bot = k + V((0, 0, 0.11))
    st.tube(bot, bot.lerp(top, 0.55), 0.025, 'black', 14); st.tube(bot.lerp(top, 0.5), top, 0.011, 'steel', 10)
    helix(st, bot.lerp(top, 0.45), top - (top - bot).normalized() * 0.06, 0.06, 6, 0.0065, 'spring')
    st.disc(top, (top - bot).normalized(), 0.075, 0.025, 'black', 20)
    arm = part(f'control_arm_f{s}', explode=(0, side * 0.15, -0.3))
    bj = k + V((0, side * 0.01, -0.13))
    for x in (FA + 0.13, FA - 0.22): arm.sweep([V((x, side * 0.33, 0.26)), bj], 0.016, 'black', 10)
    arm.disc(bj, V((0, 0, 1)), 0.022, 0.03, 'steel', 12)

def rear_corner(side):
    s = 'l' if side > 0 else 'r'; c = V((RA, side * TW, WR))
    wheel(f'wheel_r{s}', c, side, None, (-0.15, side * 0.6, 0))
    sp = part(f'spring_r{s}', explode=(0, side * 0.1, 0.4))
    helix(sp, V((RA + 0.12, side * 0.55, 0.30)), V((RA + 0.12, side * 0.55, 0.52)), 0.06, 5, 0.007, 'spring')
    sh = part(f'shock_r{s}', explode=(-0.2, side * 0.15, 0.35))
    a, b = V((RA - 0.08, side * 0.60, 0.26)), V((RA - 0.12, side * 0.58, 0.66))
    sh.tube(a, a.lerp(b, 0.6), 0.022, 'black', 12); sh.tube(a.lerp(b, 0.55), b, 0.008, 'steel', 8)

def rear_axle():
    m = part('rear_axle', explode=(0, 0, -0.35))
    m.tube(V((RA + 0.12, -0.60, 0.30)), V((RA + 0.12, 0.60, 0.30)), 0.04, 'cast', 16)        # torsion beam
    for side in (-1, 1):
        m.sweep([V((RA + 0.48, side * 0.60, 0.33)), V((RA + 0.12, side * 0.62, 0.30)), V((RA, side * 0.66, WR))], [0.03, 0.035, 0.03], 'cast', 12)
        m.disc(V((RA, side * 0.66, WR)), Y, 0.05, 0.05, 'cast', 16)

def steering():
    col_dir = (PINION - SW).normalized()
    sw = part('steering_wheel', pivot=SW, axis=-col_dir, explode=(-0.45, 0, 0.25))
    sw.torus(SW, col_dir, 0.185, 0.016, 'black', 48, 10)
    sw.disc(SW + col_dir * 0.02, col_dir, 0.07, 0.05, 'black', 20)
    u = col_dir.cross(Y).normalized(); w = col_dir.cross(u)
    for a in (pi / 2, pi + 0.35, -0.35):
        sw.sweep([SW + col_dir * 0.02 + (u * cos(a) + w * sin(a)) * 0.06, SW + (u * cos(a) + w * sin(a)) * 0.175], 0.012, 'black', 8)
    col = part('steering_column', pivot=SW + col_dir * 0.06, axis=-col_dir, explode=(-0.25, 0, 0.1))
    mid = SW.lerp(PINION, 0.6) + V((0, 0, 0.05))
    col.tube(SW + col_dir * 0.05, mid, 0.016, 'steel', 10); col.tube(mid, PINION, 0.012, 'steel', 10)
    col.disc(mid, (PINION - mid).normalized(), 0.022, 0.04, 'black', 12)                    # universal joint
    r = part('steering_rack', explode=(0, 0, -0.25))
    r.tube(RACK + V((0, -0.42, 0)), RACK + V((0, 0.42, 0)), 0.025, 'alu', 14)
    r.disc(PINION, V((0, 0, 1)), 0.035, 0.07, 'alu', 16)
    for side in (-1, 1):
        r.sweep([RACK + V((0, side * 0.42, 0)), RACK + V((0, side * 0.48, 0))], [0.03, 0.014], 'rubber', 12)   # boots
        end = V((FA - 0.13, side * (TW - 0.08), WR - 0.03))
        r.tube(RACK + V((0, side * 0.48, 0)), end, 0.011, 'steel', 8); r.disc(end, V((0, 0, 1)), 0.018, 0.03, 'steel', 10)   # tie rods

def chassis_misc():
    m = part('fuel_tank', explode=(0, 0, -0.45))
    m.box(V((-0.80, 0, 0.27)), (0.55, 0.85, 0.20), 'black')
    m.tube(V((-0.80, 0.40, 0.32)), V((-1.55, 0.72, 0.85)), 0.02, 'black', 10)                 # filler neck
    m = part('subframe', explode=(0, 0, -0.3))
    for side in (-1, 1): m.tube(V((FA + 0.30, side * 0.36, 0.25)), V((FA - 0.40, side * 0.36, 0.25)), 0.03, 'cast', 12)
    for x in (FA + 0.28, FA - 0.38): m.tube(V((x, -0.38, 0.25)), V((x, 0.38, 0.25)), 0.028, 'cast', 12)

def build():
    engine(); transmission(); steering(); rear_axle(); chassis_misc()
    for side in (1, -1): front_corner(side); rear_corner(side)

VIEWS = {'left_34': ((3.4, 3.0, 1.9), (0.3, 0, 0.45), 35), 'right_side': ((0.2, -5.2, 0.9), (0.2, 0, 0.45), 35),
         'engine': ((2.6, 1.5, 1.55), (1.55, 0, 0.45), 40), 'gearbox': ((1.55, -1.6, 0.7), (1.45, -0.25, 0.4), 40),
         'under': ((0.4, -2.2, -1.2), (0.3, 0, 0.3), 30), 'engine_front': ((2.5, 0.25, 0.75), (1.56, 0.12, 0.55), 45)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['left_34'])
