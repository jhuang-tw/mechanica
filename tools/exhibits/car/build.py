# Car exhibit (generic compact front-wheel-drive sedan), built from scratch for Mechanica: one GLB node per semantic part.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/car/build.py -- public/exhibits/car [--preview]
# then node tools/optimize-glb.mjs tools/exhibits/car/model.raw.glb public/exhibits/car/model.glb 0.002
# Run tools/exhibits/car/cad.py first (engine, gearbox, differential, wheels and discs come from its STLs).
# Model frame (Blender): metres, ground z = 0, front = +x, car's left = +y. glTF export: front +x, up +y, car's right = +z.
# Node origins are rotation centres; spin axes are written as extras.axis (glTF axes); shafts across the car spin about
# glTF -z (Blender +y), so a positive turn rolls the wheels forward. Front wheels hang on their steering
# knuckle (knuckle turns about the kingpin, the wheel spins inside it); brake discs hang on their wheel.
# The body shell is a Tripo3D mesh (tools/exhibits/car/tripo/body.glb, kept out of git): aligned to the CAD axles, wheels cut away,
# decimated and split along its panel lines into hood, doors, trunk and body. Seats, dashboard, pedals, floor pan and brake booster are modelled here.
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
    'seat':   ((0.035, 0.035, 0.04), 0.0, 0.80),
    'trim':   ((0.06, 0.06, 0.065), 0.0, 0.60),
    'screen': ((0.005, 0.006, 0.01), 0.3, 0.08),
    'carpet': ((0.025, 0.025, 0.028), 0.0, 0.95),
    'fluid':  ((0.55, 0.50, 0.38), 0.0, 0.45),      # translucent-looking reservoir plastic
    'white':  ((0.80, 0.80, 0.78), 0.0, 0.50),
    'filter': ((0.04, 0.10, 0.30), 0.3, 0.40),
})

def helix(m, a, b, r, turns, wire, mat):
    """Coil spring from a to b (any direction)."""
    ax = (b - a); L = ax.length; ax.normalize()
    u = ax.cross(V((0, 0, 1)) if abs(ax.z) < 0.9 else V((1, 0, 0))).normalized(); w = ax.cross(u)
    n = int(turns * 16)
    m.sweep([a + ax * (L * i / n) + (u * cos(TAU * turns * i / n) + w * sin(TAU * turns * i / n)) * r for i in range(n + 1)], wire, mat, 6)

def revolve(m, c, axis, prof, mat, seg=96, bump=None):
    """Closed surface of revolution about axis through c; prof = [(radius, axial offset)] as a closed loop.
    bump(i, j) -> radius change for ring i, profile point j (tread blocks)."""
    ax = axis.normalized(); a = ax.cross(V((0, 0, 1)) if abs(ax.z) < 0.9 else V((1, 0, 0))).normalized(); b = ax.cross(a)
    rings = []
    for i in range(seg):
        t = TAU * i / seg; rd = a * cos(t) + b * sin(t)
        rings.append([m.bm.verts.new(c + rd * (r + (bump(i, j) if bump else 0)) + ax * h) for j, (r, h) in enumerate(prof)])
    n = len(prof)
    for i in range(seg):
        r0, r1 = rings[i], rings[(i + 1) % seg]
        for j in range(n): m.face([r0[j], r1[j], r1[(j + 1) % n], r0[(j + 1) % n]], mat)

def sector(m, c, axis, r0, r1, a0, a1, h0, h1, mat, steps=8):
    """Annular sector (radii r0..r1, angles a0..a1 in the plane normal to axis, axial h0..h1) about c: caliper bodies."""
    ax = axis.normalized(); u = V((1, 0, 0)) if abs(ax.x) < 0.9 else V((0, 0, 1)); w = ax.cross(u).normalized(); u = w.cross(ax)
    if h0 > h1: h0, h1 = h1, h0
    rings = []
    for k in range(steps + 1):
        t = a0 + (a1 - a0) * k / steps; d = u * cos(t) + w * sin(t)
        rings.append([m.bm.verts.new(c + d * r + ax * h) for r, h in ((r0, h0), (r1, h0), (r1, h1), (r0, h1))])
    if (u.cross(w)).dot(ax) * (a1 - a0) < 0: rings = [r[::-1] for r in rings]
    for r0_, r1_ in zip(rings, rings[1:]):
        for j in range(4): m.face([r0_[j], r0_[(j + 1) % 4], r1_[(j + 1) % 4], r1_[j]], mat)
    m.face(rings[0], mat); m.face(rings[-1][::-1], mat)

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
    m = PARTS['block']['m']; X = V((1, 0, 0))                                 # spin-on oil filter on the boss at the back
    m.disc(CRANK + V((-0.165, -0.11, 0.01)), X, 0.038, 0.085, 'filter', 32); m.disc(CRANK + V((-0.21, -0.11, 0.01)), X, 0.03, 0.008, 'filter', 24)
    m = part('crankshaft', pivot=CRANK, axis=Y, explode=(0, 0, -0.55))
    m.stl('crankshaft', 'steel', at(CRANK, NY, pi / 2))                       # throw 0 (cylinders 1, 4) points up
    fw = part('flywheel', pivot=CRANK + V((0, -0.218, 0)), axis=Y, explode=(0, -0.3, 0))
    fw.stl('flywheel', 'steel', at(CRANK + V((0, -0.218, 0)), NY))
    for i, (y, up) in enumerate(zip(CYL_Y, TDC), 1):
        pin_z = CRANK.z + (STROKE / 2 if up else -STROKE / 2)
        pin = V((CRANK.x, y, pin_z)); wrist = pin + V((0, 0, ROD))
        p = part(f'piston_{i}', pivot=wrist, explode=(0, 0, 0.9))
        p.stl('piston', 'alu', at(wrist, S, pi / 2))
        r = part(f'conrod_{i}', pivot=pin, axis=Y, explode=(0, 0, 0.6))
        r.stl('conrod', 'steel', at(pin, NY))
    for pid, dx, ex in (('camshaft_intake', -0.035, (-0.1, 0, 0.75)), ('camshaft_exhaust', 0.035, (0.1, 0, 0.75))):
        c = V((CRANK.x + dx, CRANK.y, CAM_Z))
        m = part(pid, pivot=c, axis=Y, explode=ex)
        m.stl('cam_in' if dx < 0 else 'cam_ex', 'steel', at(c, NY))
        m.tube(c + V((0, 0.19, 0)), V((c.x, PULLEY_Y, c.z)), 0.012, 'steel', 10)
        m.stl('pulley_cam', 'black', at(V((c.x, PULLEY_Y, c.z)), NY))
    m = part('crank_pulley', pivot=V((CRANK.x, PULLEY_Y, CRANK.z)), parent='crankshaft', axis=Y, explode=(0, 0.25, 0))
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
    fc = rc - V((0.055, 0.0, 0.0)); X = V((1, 0, 0))                          # electric cooling fan in its shroud
    m.box(rc - V((0.022, 0, 0)), (0.012, 0.60, 0.38), 'black')
    m.disc(fc, X, 0.16, 0.05, 'black', 40, r_in=0.150)
    m.disc(fc - X * 0.01, X, 0.04, 0.05, 'black', 24)                         # motor
    for k in range(7):
        t = TAU * k / 7
        m.box(fc + V((0, cos(t) * 0.095, sin(t) * 0.095)), (0.006, 0.042, 0.11), 'black', Matrix.Rotation(t - pi / 2, 3, 'X') @ Matrix.Rotation(radians(28), 3, 'Z'))
    for t in (0.6, 0.6 + TAU / 3, 0.6 + 2 * TAU / 3): m.tube(fc - X * 0.02 + V((0, cos(t) * 0.04, sin(t) * 0.04)), fc - X * 0.02 + V((0, cos(t) * 0.15, sin(t) * 0.15)), 0.005, 'black', 6)
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
    inp = part('input_shaft', pivot=I + V((0, fy, 0)), axis=Y, explode=(0.15, -0.6, 0.3))
    inp.tube(I + V((0, fy, 0)), I + V((0, GEAR_Y[-1] - 0.03, 0)), 0.012, 'steel', 12)
    out = part('output_shaft', pivot=OUT_AX + V((0, GEAR_Y[0] + 0.03, 0)), axis=Y, explode=(-0.05, -0.6, -0.15))
    out.tube(OUT_AX + V((0, GEAR_Y[0] + 0.03, 0)), OUT_AX + V((0, DIFF.y - 0.03, 0)), 0.014, 'steel', 12)
    out.stl('pinion', 'steel', at(OUT_AX + V((0, DIFF.y, 0)), NY))
    for k, y in enumerate(GEAR_Y, 1):
        inp.stl(f'gear_in_{k}', 'steel', at(I + V((0, y, 0)), NY))
        g = part(f'gear_{k}', pivot=OUT_AX + V((0, y, 0)), axis=Y, explode=(-0.1, -0.6 - 0.05 * k, -0.25))
        g.stl(f'gear_out_{k}', 'brass' if k == 3 else 'steel', at(OUT_AX + V((0, y, 0)), NY))   # 3rd is engaged at rest
    d = part('differential', pivot=DIFF, axis=Y, explode=(-0.2, -0.5, -0.2))
    d.stl('diff', 'steel', at(DIFF, NY))
    for pid, y0, y1 in (('driveshaft_l', DIFF.y + 0.06, 0.62), ('driveshaft_r', DIFF.y - 0.06, -0.62)):
        s = part(pid, pivot=V((FA, y0, WR)), axis=Y, explode=(0, 0.3 if y1 > 0 else -0.3, -0.3))
        a, b = V((FA, y0, WR)), V((FA, y1, WR)); dy = 1 if y1 > y0 else -1
        s.tube(a + V((0, dy * 0.04, 0)), b - V((0, dy * 0.04, 0)), 0.013, 'steel', 12)
        for e in (a + V((0, dy * 0.035, 0)), b - V((0, dy * 0.035, 0))):
            s.disc(e, Y, 0.042, 0.07, 'black', 20)
            s.sweep([e + V((0, dy * 0.03, 0)), e + V((0, dy * 0.09, 0))] if e.y * dy < b.y * dy - 0.1 else [e - V((0, dy * 0.03, 0)), e - V((0, dy * 0.09, 0))], [0.035, 0.016], 'rubber', 14)

# ---------------------------------------------------------------- wheels, brakes, suspension, steering
# 205/55 R16 tyre section (radius, offset across the tread): bead, sidewall bulge with a rim protector, rounded shoulder,
# tread with four circumferential grooves; closed under the bead (hidden by the rim)
_T = [(0.204, -0.084), (0.226, -0.101), (0.252, -0.105), (0.262, -0.108), (0.272, -0.104), (0.290, -0.100),
      (0.306, -0.093), (0.313, -0.084), (0.316, -0.074)]
for g in (-0.048, -0.017):
    _T += [(0.316, g - 0.006), (0.307, g - 0.005), (0.307, g + 0.005), (0.316, g + 0.006)]
TYRE = _T + [(r, -h) for r, h in reversed(_T)] + [(0.200, 0.084), (0.200, -0.084)]
SHOULDER = {j for j, (r, h) in enumerate(TYRE) if r > 0.300 and abs(h) > 0.066}

def wheel(pid, c, side, parent, ex):
    """Rim with its hub outboard (positive offset, like a real FWD wheel), lug nuts and centre cap, a treaded tyre; the
    brake disc's hat bolts against the rim's mounting face; a floating caliper straddles the disc at the rear-top."""
    out = Y * side
    w = part(pid, pivot=c, parent=parent, axis=Y, explode=ex)
    w.stl('rim', 'alu', at(c, PY if side > 0 else NY))                         # rim z (outboard) -> away from the car
    revolve(w, c, Y, TYRE, 'rubber', 108, lambda i, j: -0.0045 if j in SHOULDER and i % 3 == 0 else 0)   # shoulder blocks
    for k in range(5):                                                         # lug nuts in the rim's five holes (PCD 114)
        t = TAU * k / 5 + pi / 2; p = c + out * 0.059 + V((cos(t) * 0.057, 0, sin(t) * 0.057))
        w.disc(p, Y, 0.0105, 0.016, 'steel', 6); w.disc(p + out * 0.009, Y, 0.007, 0.004, 'steel', 12)
    w.disc(c + out * 0.058, Y, 0.031, 0.008, 'black', 24)                      # centre cap
    dc = c - out * 0.009                                                       # disc centre: braking faces at -0.021..+0.003
    d = part(pid.replace('wheel', 'disc'), pivot=c, parent=pid, axis=Y, explode=(0, -side * 0.2, 0))
    d.stl('disc', 'cast', at(dc, PY if side > 0 else NY))
    cal = part(pid.replace('wheel', 'caliper'), parent=parent and parent, explode=(0, -side * 0.15, 0.25))
    a = radians(140); da = radians(24)                                         # caliper centre angle (rear-top) and half span
    io, oo = -side, side                                                       # inboard / outboard along y
    sector(cal, dc, Y, 0.086, 0.150, a - da, a + da, io * 0.022, io * 0.058, 'red')          # piston housing (inboard)
    sector(cal, dc, Y, 0.100, 0.150, a - da * 0.8, a + da * 0.8, oo * 0.022, oo * 0.034, 'red')   # outer fingers
    sector(cal, dc, Y, 0.142, 0.162, a - da * 0.85, a + da * 0.85, io * 0.058, oo * 0.034, 'red')  # bridge over the disc rim
    sector(cal, dc, Y, 0.100, 0.138, a - da * 0.75, a + da * 0.75, io * 0.012, io * 0.022, 'black')   # pads
    sector(cal, dc, Y, 0.100, 0.138, a - da * 0.75, a + da * 0.75, oo * 0.012, oo * 0.022, 'black')
    ctr = dc + V((cos(a), 0, sin(a))) * 0.118
    cal.disc(ctr + Y * io * 0.064, Y, 0.030, 0.014, 'red', 24)                 # piston bore boss
    for s in (-1, 1):                                                          # guide pins on the bracket
        t = a + s * (da + 0.10); p = dc + V((cos(t), 0, sin(t))) * 0.112
        cal.disc(p + Y * io * 0.037, Y, 0.011, 0.044, 'steel', 12); cal.disc(p + Y * io * 0.063, Y, 0.008, 0.008, 'black', 12)
    t = a - da * 0.55; p = dc + V((cos(t), 0, sin(t))) * 0.150 + Y * io * 0.045
    cal.tube(p, p + V((cos(t), 0, sin(t))) * 0.014, 0.004, 'steel', 8)        # bleed nipple
    t = a + da * 0.4; p = dc + V((cos(t), 0, sin(t))) * 0.12 + Y * io * 0.058
    cal.sweep([p, p + Y * io * 0.03, p + Y * io * 0.06 + V((0, 0, 0.05))], 0.0055, 'rubber', 8)   # brake hose

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
    sw.torus(SW, col_dir, 0.185, 0.0175, 'black', 64, 12, squash=1.2)          # leather rim, slightly oval grip
    sw.disc(SW + col_dir * 0.025, col_dir, 0.072, 0.05, 'black', 32)          # hub
    sw.disc(SW - col_dir * 0.002, col_dir, 0.064, 0.008, 'trim', 32)           # airbag cover
    up = (V((0, 0, 1)) - col_dir * col_dir.z).normalized(); side = col_dir.cross(up)
    for r in (-up, (side - up * 0.25).normalized(), (-side - up * 0.25).normalized()):   # spokes at 3, 6 and 9 o'clock, each two tubes wide
        t = r.cross(col_dir).normalized()
        for o in (-0.006, 0.006): sw.sweep([SW + col_dir * 0.02 + r * 0.06 + t * o, SW + col_dir * 0.005 + r * 0.172 + t * o * 0.7], 0.0095, 'black', 8)
    col = part('steering_column', pivot=SW + col_dir * 0.06, axis=-col_dir, explode=(-0.25, 0, 0.1))
    mid = SW.lerp(PINION, 0.6) + V((0, 0, 0.05))
    col.tube(SW + col_dir * 0.05, mid, 0.016, 'steel', 10); col.tube(mid, PINION, 0.012, 'steel', 10)
    col.sweep([SW + col_dir * 0.065, SW + col_dir * 0.25], [0.048, 0.055], 'trim', 16)   # shroud
    u = col_dir.cross(Y).normalized()
    for s in (-1, 1): col.sweep([SW + col_dir * 0.09 + u * s * 0.045, SW + col_dir * 0.08 + u * s * 0.15 + V((0, 0, 0.01))], [0.009, 0.007], 'black', 8)   # stalks
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

# ---------------------------------------------------------------- Tripo body shell
TRIPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tripo', 'body.glb')
SHELL_TRIS = 18000

# panel lines in the aligned frame, read off the Tripo side view (x forward from mid-wheelbase, z up from the ground)
B_PILLAR = -0.205
def panel(c, n):
    x, y, z = c
    if abs(y) > 0.50 and abs(n.y) > 0.3 and 0.30 < z < 1.36:
        front = 0.90 if z < 0.98 else 0.634 - (z - 0.98) / 0.39 * 0.69      # front door follows the window arc above the belt
        rear = -0.88 if z < 0.70 else (-1.19 if z < 0.98 else -1.0)
        s = 'l' if y > 0 else 'r'
        if B_PILLAR < x < front: return f'door_f{s}'
        if rear < x < B_PILLAR: return f'door_r{s}'
    if x > 1.08 and z > 0.72 and n.z > 0.75 and abs(y) < 0.64: return 'hood'
    if x < -1.80 and z > 0.80 and abs(y) < 0.55 and (n.z > 0.45 or n.x < -0.5): return 'trunk'
    return 'body'

def tripo_body():
    hubs = [V((x, s * TW, WR)) for x in (FA, RA) for s in (1, -1)]
    def cut(ps):   # Tripo's own wheels and tyres
        return all(any(((p.x - c.x) ** 2 + (p.z - c.z) ** 2) ** 0.5 < WR + 0.03 and abs(p.y - c.y) < 0.20 for c in hubs) for p in ps)
    nodes = {'hood': (V((1.06, 0, 0.98)), Y, (0.25, 0, 0.75), None), 'trunk': (V((-1.80, 0, 1.12)), Y, (-0.3, 0, 0.7), None),
             'body': (None, None, (0, 0, 1.3), None)}
    for s, side in (('l', 1), ('r', -1)):
        nodes[f'door_f{s}'] = (V((0.90, side * 0.80, 0.70)), V((0, 0, 1)), (0.1, side * 0.9, 0), None)
        nodes[f'door_r{s}'] = (V((B_PILLAR, side * 0.80, 0.70)), V((0, 0, 1)), (-0.1, side * 0.9, 0), None)
    tripo_shell(TRIPO, (FA, RA), cut, SHELL_TRIS, panel, nodes)

# ---------------------------------------------------------------- cabin
RY = lambda deg: Matrix.Rotation(radians(deg), 3, 'Y')
RX = lambda deg: Matrix.Rotation(radians(deg), 3, 'X')
RZ = lambda deg: Matrix.Rotation(radians(deg), 3, 'Z')

def seat(m, x, y, places, bench=False):
    """Upholstered seat: pleated cushion and backrest inserts between side bolsters, front roll, headrests on posts, rails.
    places = [(y offset, width)] of the sitting places (one for a bucket seat, three for the rear bench)."""
    w = places[-1][0] - places[0][0] + places[0][1]                           # overall width
    H = V((x - 0.25, y, 0.49)); lean = RY(-16)                                 # backrest hinge, leaning back 16 degrees
    L = lambda p: H + lean @ V(p)
    rbox(m, V((x, y, 0.435)), (0.50, w - 0.02, 0.07), 0.03, 'seat')                          # cushion base
    rbox(m, V((x + 0.23, y, 0.475)), (0.07, w - 0.06, 0.09), 0.035, 'seat')                   # front roll
    rbox(m, L((-0.065, 0, 0.32)), (0.06, w - 0.01, 0.60), 0.025, 'seat', lean)                # backrest shell
    rbox(m, L((-0.01, 0, 0.60)), (0.13, w - 0.04, 0.07), 0.033, 'seat', lean)                 # top roll
    for k, (dy, pw) in enumerate(places):
        c = V((x - 0.01, y + dy, 0.485))
        for i in range(4): rbox(m, c + V((-0.165 + 0.11 * i, 0, 0)), (0.10, pw - 0.15, 0.045), 0.02, 'seat')   # pleats
        for i in range(5): rbox(m, L((0.0, dy, 0.08 + 0.10 * i)), (0.06, pw - 0.17, 0.09), 0.025, 'seat', lean)
        outer = [s for s in (-1, 1) if not bench or (k == 0 and s < 0) or (k == len(places) - 1 and s > 0)]
        for s in outer:                                                        # side bolsters, tipped inwards
            rbox(m, c + V((-0.01, s * (pw / 2 - 0.05), 0.015)), (0.44, 0.10, 0.10), 0.04, 'seat', RX(s * 14))
            rbox(m, L((0.01, dy + s * (pw / 2 - 0.055), 0.28)), (0.14, 0.11, 0.52), 0.045, 'seat', lean @ RZ(-s * 12))
        hc = L((-0.03, dy, 0.76))                                              # headrest on two chrome posts
        rbox(m, hc, (0.10, 0.25 if not bench else 0.22, 0.17), 0.045, 'seat', lean @ RX(0))
        for s in (-1, 1): m.tube(L((-0.035, dy + s * 0.065, 0.60)), L((-0.035, dy + s * 0.065, 0.69)), 0.0055, 'steel', 8)
    if not bench:
        for s in (-1, 1):                                                      # seat tracks on the floor
            m.box(V((x, y + s * 0.17, 0.33)), (0.46, 0.035, 0.03), 'black')
            m.box(V((x, y + s * 0.17, 0.37)), (0.36, 0.025, 0.06), 'steel')
        so = 1 if y > 0 else -1                                                # outer side: plastic trim, recline knob, slide bar
        rbox(m, V((x - 0.02, y + so * (w / 2 + 0.005), 0.43)), (0.42, 0.02, 0.09), 0.008, 'trim')
        m.disc(L((-0.02, so * (w / 2 + 0.02), 0.0)), Y, 0.028, 0.02, 'trim', 18)
        m.sweep([V((x + 0.20, y - 0.09, 0.355)), V((x + 0.27, y - 0.09, 0.36)), V((x + 0.27, y + 0.09, 0.36)), V((x + 0.20, y + 0.09, 0.355))], 0.006, 'black', 8)
        m.box(V((x - 0.18, y - so * (w / 2 + 0.02), 0.50)), (0.035, 0.025, 0.08), 'black')       # seat-belt buckle
    else:
        m.box(L((0.035, -w / 2 + 0.6 * w, 0.30)), (0.10, 0.006, 0.60), 'black', lean)   # 60/40 split seam

def floor_pan():
    """Cabin floor, toe board and firewall in carpet, with the transmission tunnel and the step up under the rear seat."""
    m = part('floor_pan', explode=(0, 0, -0.75))
    m.box(V((0.20, 0, 0.30)), (1.40, 1.36, 0.02), 'carpet')                                  # front floor
    m.box(V((0.99, 0, 0.43)), (0.316, 1.36, 0.02), 'carpet', RY(-55.3))                      # toe board up to the firewall
    m.box(V((1.08, 0, 0.76)), (0.02, 1.36, 0.40), 'carpet')                                  # firewall
    rbox(m, V((0.22, 0, 0.36)), (1.36, 0.22, 0.12), 0.04, 'carpet')                          # transmission tunnel
    m.box(V((-0.50, 0, 0.345)), (0.02, 1.36, 0.09), 'carpet')                                # step under the rear seat
    m.box(V((-0.875, 0, 0.38)), (0.75, 1.36, 0.02), 'carpet')                                # rear floor
    for s in (-1, 1): rbox(m, V((0.20, s * 0.70, 0.36)), (1.40, 0.06, 0.10), 0.03, 'carpet')   # sills
    rbox(m, V((0.88, 0.63, 0.40)), (0.22, 0.08, 0.025), 0.01, 'trim', RY(-40))               # dead pedal (footrest)
    rbox(m, V((0.55, DRIVER_Y, 0.312)), (0.38, 0.36, 0.008), 0.004, 'rubber')                 # driver's mat

def pedals():
    """Pendant clutch, brake and accelerator hanging from a pedal box under the dash (left-hand drive, clutch leftmost)."""
    m = part('pedals', explode=(-0.35, 0, -0.1))
    box = V((1.00, DRIVER_Y, 0.72))
    rbox(m, box, (0.08, 0.36, 0.08), 0.015, 'black')                                          # pedal box
    m.box(box + V((0.07, 0, 0)), (0.06, 0.30, 0.10), 'black')                                # mounting plate to the firewall
    m.tube(V((0.97, DRIVER_Y - 0.17, 0.69)), V((0.97, DRIVER_Y + 0.17, 0.69)), 0.008, 'steel', 10)   # pivot shaft
    for dy, pw, ph in ((0.15, 0.075, 0.06), (0.01, 0.10, 0.065)):                            # clutch, brake
        y = DRIVER_Y + dy; pad = V((0.83, y, 0.415))
        m.sweep(smooth([V((0.97, y, 0.69)), V((0.95, y, 0.60)), V((0.89, y, 0.50)), pad + V((0.02, 0, 0.01))], 3), 0.009, 'black', 6)
        m.disc(V((0.97, y, 0.69)), Y, 0.016, 0.03, 'black', 14)                              # pivot boss
        rbox(m, pad, (0.022, pw, ph), 0.008, 'rubber', RY(30))
        for k in range(4): m.box(pad + RY(30) @ V((-0.012, 0, -0.022 + 0.0147 * k)), (0.004, pw - 0.012, 0.005), 'rubber', RY(30))   # ribs
    m.tube(V((0.955, DRIVER_Y + 0.01, 0.62)), V((1.13, DRIVER_Y + 0.01, 0.72)), 0.005, 'steel', 8)   # brake push rod through the firewall
    m.tube(V((0.955, DRIVER_Y + 0.15, 0.62)), V((1.10, DRIVER_Y + 0.15, 0.70)), 0.005, 'steel', 8)   # clutch push rod
    y = DRIVER_Y - 0.13; pad = V((0.845, y, 0.40))                                              # accelerator, tall narrow pad
    m.sweep(smooth([V((0.97, y, 0.66)), V((0.93, y, 0.58)), V((0.875, y, 0.47)), pad + V((0.015, 0, 0.04))], 3), 0.006, 'black', 6)
    m.disc(V((0.97, y, 0.66)), Y, 0.014, 0.04, 'black', 14)
    rbox(m, pad, (0.016, 0.052, 0.12), 0.008, 'rubber', RY(30))
    for k in range(5): m.box(pad + RY(30) @ V((-0.009, 0, -0.044 + 0.022 * k)), (0.003, 0.042, 0.006), 'rubber', RY(30))

def brake_booster():
    """Vacuum brake booster on the engine side of the firewall with the master cylinder, fluid reservoir and the clutch master."""
    m = part('brake_booster', explode=(0.25, 0.25, 0.35))
    b = V((1.16, DRIVER_Y + 0.01, 0.72)); X = V((1, 0, 0))
    m.disc(b, X, 0.105, 0.075, 'black', 40); m.torus(b, X, 0.104, 0.006, 'steel', 40, 8)      # two-shell drum, crimped seam
    m.disc(b + X * 0.04, X, 0.04, 0.01, 'black', 24)
    m.tube(b + X * 0.04, b + X * 0.16, 0.021, 'alu', 16)                                     # master cylinder
    m.disc(b + X * 0.16, X, 0.023, 0.008, 'alu', 16)
    rbox(m, b + V((0.10, 0, 0.055)), (0.10, 0.07, 0.05), 0.012, 'fluid')                      # reservoir
    m.disc(b + V((0.10, 0, 0.085)), V((0, 0, 1)), 0.016, 0.014, 'black', 16)                  # filler cap
    for dx in (0.07, 0.13): m.sweep([b + V((dx, 0, -0.02)), b + V((dx, -0.06, -0.06)), b + V((dx + 0.05, -0.12, -0.10))], 0.004, 'steel', 6)   # brake lines
    c = V((1.10, DRIVER_Y + 0.15, 0.70)); m.tube(c, c + X * 0.08, 0.012, 'alu', 12)            # clutch master cylinder
    m.disc(c + V((0.04, 0, 0.03)), V((0, 0, 1)), 0.014, 0.025, 'fluid', 14)

def cabin():
    for s, y in (('l', DRIVER_Y), ('r', -DRIVER_Y)): seat(part(f'seat_f{s}', explode=(0, 0, 1.0)), -0.10, y, [(0, 0.52)])
    seat(part('seat_rear', explode=(-0.3, 0, 1.0)), -0.95, 0, [(-0.43, 0.44), (0, 0.42), (0.43, 0.44)], bench=True)
    d = part('dashboard', explode=(0.35, 0, 0.9))
    rbox(d, V((0.90, 0, 0.975)), (0.32, 1.46, 0.07), 0.03, 'trim', RY(-4))                    # soft top pad up to the windscreen
    rbox(d, V((0.83, 0, 0.865)), (0.15, 1.44, 0.18), 0.04, 'trim')                            # face
    rbox(d, V((0.87, 0, 0.72)), (0.16, 1.30, 0.12), 0.04, 'trim', RY(25))                     # knee panel, tucked under
    rbox(d, V((0.752, -0.36, 0.82)), (0.02, 0.42, 0.11), 0.012, 'trim')                        # glove box lid
    d.box(V((0.742, -0.36, 0.855)), (0.012, 0.09, 0.018), 'black')                            # glove box handle
    # instrument cluster: hood, two round dials (speed, rpm) with chrome bezels, white ticks and red needles
    rbox(d, V((0.73, DRIVER_Y, 1.005)), (0.15, 0.40, 0.065), 0.03, 'trim')
    d.box(V((0.762, DRIVER_Y, 0.935)), (0.01, 0.36, 0.10), 'black')
    X = V((1, 0, 0))
    for k, dy in enumerate((0.085, -0.085)):
        g = V((0.755, DRIVER_Y + dy, 0.935))
        d.disc(g, X, 0.046, 0.004, 'screen', 32); d.torus(g + X * -0.002, X, 0.047, 0.004, 'alu', 32, 6)
        for i in range(11):
            t = radians(225 - 27 * i); d.box(g + V((-0.003, cos(t) * 0.038, sin(t) * 0.038)), (0.002, 0.003, 0.009), 'white', RX(135 - 27 * i))
        t = radians(200 - 40 * k); d.box(g + V((-0.004, cos(t) * 0.018, sin(t) * 0.018)), (0.002, 0.003, 0.036), 'red', RX(110 - 40 * k))
        d.disc(g + X * -0.005, X, 0.006, 0.004, 'black', 12)
    # centre stack: floating screen, vents with slats, climate knobs, hazard button
    rbox(d, V((0.735, 0, 1.03)), (0.025, 0.25, 0.15), 0.008, 'black', RY(-10))
    d.box(V((0.722, 0, 1.03)), (0.004, 0.23, 0.13), 'screen', RY(-10))
    for y, z in ((0.62, 0.89), (0.12, 0.88), (-0.12, 0.88), (-0.62, 0.89)):
        rbox(d, V((0.752, y, z)), (0.012, 0.13, 0.055), 0.006, 'black')
        for i in range(4): d.box(V((0.746, y, z - 0.018 + 0.012 * i)), (0.006, 0.12, 0.004), 'trim', RY(-15))
    for y in (-0.08, 0, 0.08):
        d.disc(V((0.752, y, 0.80)), X, 0.022, 0.025, 'black', 20); d.torus(V((0.742, y, 0.80)), X, 0.022, 0.003, 'alu', 20, 6)
    d.box(V((0.755, 0, 0.845)), (0.012, 0.035, 0.018), 'red')
    # console: tunnel cover, cup holders, gear lever with boot and knob, handbrake, armrest box
    rbox(d, V((0.25, 0, 0.44)), (0.75, 0.22, 0.10), 0.035, 'trim')
    rbox(d, V((0.68, 0, 0.62)), (0.10, 0.20, 0.26), 0.045, 'trim', RY(28))                      # stack down to the console
    for x in (0.50, 0.42): d.disc(V((x, 0, 0.49)), V((0, 0, 1)), 0.036, 0.006, 'black', 20)
    d.sweep([V((0.30, 0, 0.495)), V((0.295, 0, 0.53)), V((0.285, 0, 0.565))], [0.05, 0.03, 0.013], 'rubber', 16)   # shift boot
    d.tube(V((0.285, 0, 0.56)), V((0.27, 0, 0.62)), 0.007, 'steel', 8)
    rbox(d, V((0.268, 0, 0.635)), (0.045, 0.042, 0.045), 0.019, 'black')                      # knob
    d.box(V((0.268, 0, 0.659)), (0.024, 0.024, 0.002), 'white')                               # shift pattern
    rbox(d, V((0.08, 0, 0.53)), (0.22, 0.035, 0.035), 0.014, 'black', RY(14))                # handbrake lever
    d.disc(V((-0.03, 0, 0.555)), X, 0.009, 0.012, 'steel', 12)
    d.sweep([V((0.17, 0, 0.495)), V((0.17, 0, 0.51))], [0.03, 0.025], 'rubber', 12)
    rbox(d, V((-0.22, 0, 0.47)), (0.28, 0.20, 0.16), 0.03, 'trim')                            # storage box
    rbox(d, V((-0.22, 0, 0.565)), (0.28, 0.19, 0.04), 0.018, 'seat')                          # armrest lid

def build():
    engine(); transmission(); steering(); rear_axle(); chassis_misc()
    for side in (1, -1): front_corner(side); rear_corner(side)
    cabin(); floor_pan(); pedals(); brake_booster()
    for pid, p in PARTS.items():   # the hand-built parts are closed shells: make every face point outwards
        if pid.startswith(('wheel', 'caliper', 'seat', 'dashboard', 'floor', 'pedals', 'brake', 'radiator', 'steering_')):
            bmesh.ops.recalc_face_normals(p['m'].bm, faces=p['m'].bm.faces[:])
    tripo_body()

VIEWS = {'left_34': ((3.4, 3.0, 1.9), (0.3, 0, 0.45), 35), 'right_side': ((0.2, -5.2, 0.9), (0.2, 0, 0.45), 35),
         'engine': ((2.6, 1.5, 1.55), (1.55, 0, 0.45), 40), 'gearbox': ((1.55, -1.6, 0.7), (1.45, -0.25, 0.4), 40),
         'under': ((0.4, -2.2, -1.2), (0.3, 0, 0.3), 30), 'engine_front': ((2.5, 0.25, 0.75), (1.56, 0.12, 0.55), 45)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['left_34'])
