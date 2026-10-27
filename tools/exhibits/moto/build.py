# Motorcycle exhibit (generic 700 cc naked parallel twin), built from scratch for Mechanica: one GLB node per semantic part.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -t 4 -P tools/exhibits/moto/build.py -- public/exhibits/moto [--preview]
# Run tools/exhibits/moto/cad.py first (engine, clutch, gearbox, sprockets, rims and discs come from its STLs).
# Model frame (Blender): metres, ground z = 0, front = +x, rider's left = +y, origin mid-wheelbase. glTF: front +x, up +y, right +z.
# Node origins are rotation centres; spin axes are written as extras.axis (glTF axes). Shafts spin about Blender +y, so a
# positive turn rolls the wheels forward. Pistons slide along the cylinder axis CYL_AXIS (15 degrees forward of vertical).
# The bodywork, frame, fork and swingarm are a Tripo3D mesh (tools/exhibits/moto/tripo/body.glb, kept out of git), aligned
# to the CAD axles, its wheels cut away and split into tank, seat, side covers, headlight cowl, fork, swingarm and frame.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import *   # Mesh, part, run, V, Matrix, Y, TAU, maths, rbox, tripo_shell
import common
from math import asin, acos, sqrt

S = Matrix.Scale(0.001, 4)
NY = Matrix.Rotation(pi / 2, 4, 'X') @ S      # CAD z -> Blender -y (outboard right)
PY = Matrix.Rotation(-pi / 2, 4, 'X') @ S     # CAD z -> Blender +y (outboard left)
def at(p, M=S, rz=0): return Matrix.Translation(p) @ M @ Matrix.Rotation(rz, 4, 'Z')
def frame_m(p, cx, cy, cz):                   # CAD x, y, z -> the given Blender directions, mm -> m
    return Matrix.Translation(p) @ Matrix((list(cx) + [0], list(cy) + [0], list(cz) + [0], [0, 0, 0, 1])).transposed() @ S

# ---------------------------------------------------------------- layout (metres), read off the Tripo side view
WB = 1.45
FA, RA = V((WB / 2, 0, 0.32)), V((-WB / 2, 0, 0.33))      # axles: 120/70 front, 180/55 rear tyre on 17-inch rims
WRF, WRR = 0.32, 0.33
CRANK = V((0.10, 0, 0.47))
TILT = radians(15)
CD = V((sin(TILT), 0, cos(TILT)))                          # cylinder axis
CF = V((cos(TILT), 0, -sin(TILT)))                         # forward, square to the cylinder axis
STROKE, ROD = 0.070, 0.130
R = STROKE / 2
CYL_Y = [-0.046, 0.046]                                    # right, left cylinder
PIN_ANG = [0.0, pi / 2]                                    # at rest: right piston at TDC, left pin 90 degrees before TDC (270-degree crank)
DECK = CRANK + CD * (R + ROD + 0.030 + 0.002)
PRIMARY_C = 0.1125                                         # crank -> mainshaft, module 2.5 x (32 + 58) / 2
GEAR_C = 0.11125                                           # mainshaft -> countershaft
MAIN = CRANK + V((-0.894, 0, 0.447)) * PRIMARY_C
COUNTER = MAIN + V((-0.894, 0, -0.447)) * GEAR_C
CHAIN_Y = 0.105
CLUTCH_Y = -0.155
PIVOT = V((-0.18, 0, 0.45))                                # swingarm pivot
RAKE = radians(21)
STEER = V((-sin(RAKE), 0, cos(RAKE)))                      # steering axis, pointing up
HEAD = FA + V((cos(RAKE), 0, sin(RAKE))) * -0.03 + STEER * 0.80          # top of the steering head

common.MATS.update({   # base colour (linear), metallic, roughness
    'alu':    ((0.62, 0.63, 0.65), 1.0, 0.38),
    'cast':   ((0.10, 0.10, 0.11), 0.7, 0.50),
    'steel':  ((0.50, 0.51, 0.53), 1.0, 0.30),
    'chrome': ((0.80, 0.80, 0.82), 1.0, 0.12),
    'black':  ((0.015, 0.015, 0.017), 0.0, 0.55),
    'dark':   ((0.04, 0.04, 0.045), 0.5, 0.45),
    'rubber': ((0.02, 0.02, 0.02), 0.0, 0.85),
    'gold':   ((0.70, 0.50, 0.12), 1.0, 0.35),
    'red':    ((0.55, 0.04, 0.03), 0.2, 0.35),
    'brass':  ((0.60, 0.42, 0.15), 1.0, 0.35),
    'core':   ((0.08, 0.08, 0.085), 0.6, 0.6),
})

# ---------------------------------------------------------------- engine
def pin_pos(i):
    a = PIN_ANG[i]
    return CRANK + V((0, CYL_Y[i], 0)) + (CD * cos(a) + CF * -sin(a)) * R   # matches the CAD throws: 270 degrees on = 90 degrees back

def wrist_pos(i):
    p = pin_pos(i) - V((0, CYL_Y[i], 0)) - CRANK
    s = p.dot(CD) + sqrt(ROD ** 2 - p.dot(CF) ** 2)
    return CRANK + V((0, CYL_Y[i], 0)) + CD * s

def engine():
    m = part('crankcase', explode=(0, 0, -0.45))
    m.stl('crankcase', 'alu', at(CRANK, Matrix.Rotation(0, 4, 'Z') @ S))
    part('cylinder_block', explode=(0, 0, 0)).stl('block', 'alu', frame_m(DECK, CF, Y, CD))
    h = part('cylinder_head', explode=CD * 0.30)
    rbox(h, DECK + CD * 0.045, (0.125, 0.215, 0.09), 0.012, 'alu', Matrix.Rotation(TILT, 3, 'Y'))
    for y in CYL_Y:                                                                       # exhaust ports and intake stubs
        h.tube(DECK + CD * 0.04 + CF * 0.05 + V((0, y, 0)), DECK + CD * 0.035 + CF * 0.085 + V((0, y, 0)), 0.019, 'alu', 14)
        h.tube(DECK + CD * 0.05 - CF * 0.05 + V((0, y, 0)), DECK + CD * 0.08 - CF * 0.11 + V((0, y, 0)), 0.022, 'black', 14)
    c = part('cam_cover', explode=CD * 0.5)
    rbox(c, DECK + CD * 0.115, (0.12, 0.205, 0.05), 0.018, 'black', Matrix.Rotation(TILT, 3, 'Y'))
    for k, (pid, d) in enumerate((('camshaft_exhaust', 0.028), ('camshaft_intake', -0.028))):
        cp = DECK + CD * 0.08 + CF * d
        part(pid, pivot=cp, axis=Y, explode=CD * 0.4 + CF * d * 6).stl('cam_ex' if k == 0 else 'cam_in', 'steel', at(cp, PY))
    cr = part('crankshaft', pivot=CRANK, axis=Y, explode=(0, 0, -0.65))
    cr.stl('crankshaft', 'steel', at(CRANK, PY, -pi / 2 + TILT))                         # throw 0 (right cylinder) along CD
    for i, (y, side) in enumerate(zip(CYL_Y, 'rl')):
        P, W = pin_pos(i), wrist_pos(i)
        u = (W - P).normalized()
        part(f'conrod_{side}', pivot=P, axis=Y, explode=CD * 0.45 + V((0, y * 3, 0))).stl('conrod', 'steel', frame_m(P, u.cross(Y), u, Y))
        part(f'piston_{side}', pivot=W, explode=CD * 0.70 + V((0, y * 3, 0))).stl('piston', 'alu', frame_m(W, Y, CD.cross(Y), CD))
    ch = part('cam_chain', explode=(0, -0.25, 0.1))
    a, b = CRANK + V((0, -0.118, 0)), DECK + CD * 0.08 + V((0, -0.118, 0))
    for s in (-1, 1): ch.tube(a + CF * s * 0.025, b + CF * s * 0.034, 0.004, 'dark', 6)
    pg = part('primary_gear', pivot=CRANK + V((0, CLUTCH_Y + 0.024, 0)), parent='crankshaft', axis=Y, explode=(0, -0.3, 0))
    pg.stl('primary_gear', 'steel', at(CRANK + V((0, CLUTCH_Y + 0.024, 0)), NY))
    cl = part('clutch', pivot=MAIN + V((0, CLUTCH_Y, 0)), axis=Y, explode=(0, -0.45, 0))
    cl.stl('clutch', 'alu', at(MAIN + V((0, CLUTCH_Y, 0)), NY))
    cc = part('clutch_cover', explode=(0, -0.7, 0))
    cc.disc(MAIN + V((0, CLUTCH_Y - 0.046, 0)), Y, 0.078, 0.012, 'black', 40)
    cc.torus(MAIN + V((0, CLUTCH_Y - 0.036, 0)), Y, 0.078, 0.008, 'black', 40, 8)
    rad = part('radiator', explode=(0.4, 0, 0.1))
    rc = V((0.335, 0, 0.60)); rr = Matrix.Rotation(TILT, 3, 'Y')
    rad.box(rc, (0.035, 0.30, 0.24), 'core', rr)
    for k in range(12): rad.box(rc + rr @ V((0.019, -0.14 + k * 0.0255, 0)), (0.004, 0.003, 0.24), 'dark', rr)
    for s in (-1, 1): rad.box(rc + rr @ V((0, s * 0.16, 0)), (0.04, 0.02, 0.25), 'black', rr)
    rad.tube(rc + rr @ V((-0.02, 0.10, 0.10)), DECK + CD * 0.03 + V((0, 0.08, 0)), 0.012, 'black', 10)    # hoses
    rad.tube(rc + rr @ V((-0.02, -0.10, -0.10)), CRANK + V((0.09, -0.08, 0.02)), 0.012, 'black', 10)
    ex = part('exhaust_headers', explode=(0.35, 0, -0.25))
    for y in CYL_Y:
        p0 = DECK + CD * 0.035 + CF * 0.085 + V((0, y, 0))
        bend = [p0, p0 + CF * 0.04 - CD * 0.01, p0 + CF * 0.065 - CD * 0.06]
        low = CRANK.z - 0.16
        run = [V((0.27, y * 0.9, CRANK.z - 0.06)), V((0.25, y * 0.8, low + 0.03)), V((0.19, y * 0.6, low)), V((0.08, y * 0.3 - 0.02, low - 0.01)),
               V((-0.05, -0.04, low - 0.01)), V((-0.17, -0.05, low + 0.01))]
        ex.sweep(smooth(bend + run, 8), 0.021, 'chrome', 16)

# ---------------------------------------------------------------- gearbox and chain
def gearbox():
    ms = part('mainshaft', pivot=MAIN, axis=Y, explode=(-0.05, 0, 0.45))
    ms.disc(MAIN + V((0, -0.035, 0)), Y, 0.011, 0.25, 'steel', 14)
    cs = part('countershaft', pivot=COUNTER, axis=Y, explode=(-0.1, 0, -0.45))
    cs.disc(COUNTER + V((0, 0.0, 0)), Y, 0.012, 0.23, 'steel', 14)
    for k in range(6):                                                                    # cad.GEARS
        y = -0.088 + 0.0165 * k
        ms.stl(f'gear_main_{k + 1}', 'steel', at(MAIN + V((0, y, 0)), PY))
        cs.stl(f'gear_counter_{k + 1}', 'steel', at(COUNTER + V((0, y, 0)), PY))
    fs = part('sprocket_front', pivot=COUNTER + V((0, CHAIN_Y, 0)), parent='countershaft', axis=Y, explode=(0, 0.3, 0))
    fs.stl('sprocket_front', 'steel', at(COUNTER + V((0, CHAIN_Y, 0)), PY))

def pitch_r(n, p=0.015875): return p / (2 * sin(pi / n))

def chain():
    c1, r1, c2, r2 = COUNTER, pitch_r(15), RA, pitch_r(43)
    d = V((c2.x - c1.x, c2.z - c1.z)); L = d.length; th = atan2(d.y, d.x); be = acos((r1 - r2) / L)
    def pt(c, r, a): return V((c.x + r * cos(a), CHAIN_Y, c.z + r * sin(a)))
    path = [pt(c1, r1, th + be)]
    path += [pt(c2, r2, th + be - 2 * be * i / 24) for i in range(25)]                   # around the rear sprocket
    path += [pt(c1, r1, th - be - (2 * pi - 2 * be) * i / 10) for i in range(11)]        # around the front one
    pts = []
    for a, b in zip(path, path[1:]):
        n = max(1, round((b - a).length / 0.015875)); pts += [a.lerp(b, i / n) for i in range(n)]
    ch = part('chain', explode=(0, 0.45, 0))
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]; t = q - p
        if t.length < 1e-6: continue
        rot = Matrix.Rotation(-atan2(t.z, t.x), 3, 'Y')
        ch.disc(p, Y, 0.0051, 0.0095, 'dark', 6)                                          # roller
        w, mat = (0.0078, 'gold') if i % 2 == 0 else (0.0058, 'dark')                     # outer / inner plates
        for sy in (-1, 1): ch.box(p.lerp(q, 0.5) + V((0, sy * w, 0)), (0.022, 0.0015, 0.012), mat, rot)

# ---------------------------------------------------------------- wheels and brakes
def tyre(m, c, wr, r, squash):
    m.torus(c, Y, wr - r, r, 'rubber', 64, 12, squash=squash)

def wheels():
    f = part('wheel_front', pivot=FA, parent='fork', axis=Y, explode=(0.35, 0, 0))
    f.stl('rim_front', 'cast', at(FA, PY)); tyre(f, FA, WRF, 0.055, 1.1)
    for s in (1, -1):
        dpos = FA + V((0, s * 0.072, 0))
        part(f'disc_front_{"l" if s > 0 else "r"}', pivot=FA, parent='wheel_front', axis=Y, explode=(0, s * 0.25, 0)).stl('disc_front', 'steel', at(dpos, PY))
    cal = part('calipers_front', parent='fork', explode=(0.1, 0, 0.2))
    for s in (1, -1):
        cp = FA + V((-0.115, s * 0.072, 0.11))
        cal.box(cp, (0.10, 0.045, 0.05), 'gold', Matrix.Rotation(radians(-50), 3, 'Y'))
    r = part('wheel_rear', pivot=RA, parent='swingarm', axis=Y, explode=(-0.35, 0, 0))
    r.stl('rim_rear', 'cast', at(RA, PY)); tyre(r, RA, WRR, 0.062, 1.45)
    part('sprocket_rear', pivot=RA, parent='wheel_rear', axis=Y, explode=(0, 0.3, 0)).stl('sprocket_rear', 'alu', at(RA + V((0, CHAIN_Y, 0)), PY))
    part('disc_rear', pivot=RA, parent='wheel_rear', axis=Y, explode=(0, -0.3, 0)).stl('disc_rear', 'steel', at(RA + V((0, -0.088, 0)), PY))
    rc = part('caliper_rear', parent='swingarm', explode=(0, -0.25, 0.15))
    rc.box(RA + V((0.06, -0.088, 0.10)), (0.08, 0.04, 0.045), 'black', Matrix.Rotation(radians(-60), 3, 'Y'))

def build():
    engine(); gearbox(); chain(); tripo_body(); wheels()

# ---------------------------------------------------------------- Tripo bodywork
TRIPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tripo', 'body.glb')

def on_fork(c):   # fork legs, triple clamps and front fender: near the steering axis, wider low down by the wheel
    d = c - HEAD; along = d.dot(STEER); off = (d - STEER * along).length
    return -0.85 < along < 0.03 and off < (0.17 if along < -0.35 else 0.10)

def near_swingarm(c):
    a, b = V((PIVOT.x, PIVOT.z)), V((RA.x, RA.z)); p = V((c.x, c.z))
    t = max(0, min(1, (p - a).dot(b - a) / (b - a).length_squared))
    return (p - a.lerp(b, t)).length < 0.055 and abs(c.y) < 0.15 and c.x < PIVOT.x - 0.02

def classify(c, n):
    x, y, z = c
    if x > 0.47 and 0.84 < z < 1.16 and abs(y) < 0.13: return 'headlight_cowl'
    if z > 1.03 and x > 0.22 and (abs(y) > 0.13 or x > 0.37): return 'handlebar'
    if on_fork(c): return 'fork'
    if near_swingarm(c): return 'swingarm'
    if -0.21 < x < 0.37 and z > 0.87 and abs(y) < 0.18: return 'tank'
    if x < -0.78 and z > 0.80: return 'tail'
    if -0.80 < x < -0.17 and z > 0.90 and abs(y) < 0.16 and n.z > 0.2: return 'seat'
    if -0.58 < x < -0.15 and 0.58 < z < 0.90 and abs(y) > 0.05 and abs(n.y) > 0.5: return 'side_cover_l' if y > 0 else 'side_cover_r'
    return 'frame'

def tripo_body():
    def cut(ps):   # Tripo's wheels, tyres, discs and rear sprocket
        def inside(p):
            for a, wr, hw in ((FA, WRF, 0.075), (RA, WRR, 0.105)):
                if ((p.x - a.x) ** 2 + (p.z - a.z) ** 2) ** 0.5 < wr + 0.01 and abs(p.y) < hw: return True
            return False
        return all(inside(p) for p in ps)
    nodes = {'frame': (None, None, (0, 0, 0.9), None), 'fork': (HEAD, STEER, (0.55, 0, 0.2), None),
             'swingarm': (PIVOT, Y, (-0.5, 0, -0.1), None), 'tank': (None, None, (0, 0, 0.55), None),
             'seat': (None, None, (-0.1, 0, 0.5), None), 'side_cover_l': (None, None, (0, 0.35, 0), None),
             'side_cover_r': (None, None, (0, -0.35, 0), None), 'headlight_cowl': (HEAD, None, (0.4, 0, 0.25), 'fork'),
             'handlebar': (HEAD, None, (0.1, 0, 0.45), 'fork'), 'tail': (None, None, (-0.45, 0, 0.3), None)}
    if not tripo_shell(TRIPO, (FA.x, RA.x), cut, 16000, classify, nodes):
        part('fork', pivot=HEAD, axis=STEER); part('swingarm', pivot=PIVOT, axis=Y)            # keep the wheel parents

VIEWS = {'left': ((0.1, 3.2, 0.6), (0.0, 0, 0.5), 35), 'left_34': ((1.9, 2.2, 1.2), (0.0, 0, 0.45), 35),
         'right_34': ((-1.2, -2.4, 1.1), (0.0, 0, 0.45), 35), 'engine': ((0.75, 0.9, 0.75), (0.05, 0, 0.5), 40),
         'front': ((2.6, 0.3, 0.8), (0.3, 0, 0.5), 40)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['left_34'])
