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
    'can':    ((0.16, 0.16, 0.17), 0.85, 0.32),   # silencer: brushed dark steel, the Tripo can's grey
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
    m.stl('crankcase', 'cast', at(CRANK, Matrix.Rotation(0, 4, 'Z') @ S))
    part('cylinder_block', explode=(0, 0, 0)).stl('block', 'cast', frame_m(DECK, CF, Y, CD))
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
    # right engine cover, sealed like a real one: clutch, primary drive and cam chain run in oil behind it
    cc = part('clutch_cover', explode=(0, -0.7, 0))
    yc, t = (-0.108 + CLUTCH_Y - 0.052) / 2, -0.108 - (CLUTCH_Y - 0.052)
    cc.disc(MAIN + V((0, yc, 0)), Y, 0.082, t, 'cast', 48)
    cc.disc(CRANK + V((0, yc, 0)), Y, 0.062, t, 'cast', 40)
    d = MAIN - CRANK
    cc.box((MAIN + CRANK) / 2 + V((0, yc, 0)), (d.length, t, 0.12), 'cast', Matrix.Rotation(-atan2(d.z, d.x), 3, 'Y'))
    cc.torus(MAIN + V((0, CLUTCH_Y - 0.052, 0)), Y, 0.06, 0.006, 'alu', 40, 8)          # polished clutch lid ring
    a, b = CRANK + V((0, -0.118, 0)), DECK + CD * 0.08 + V((0, -0.118, 0))
    rbox(cc, (a + b) / 2, (0.085, 0.04, (b - a).length + 0.05), 0.012, 'cast', Matrix.Rotation(TILT, 3, 'Y'))   # cam chain tunnel
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
    for s in (1, -1): caliper(cal, FA, radians(136), 0.143, s * 0.072, s, 'gold', 4, FA)
    r = part('wheel_rear', pivot=RA, parent='swingarm', axis=Y, explode=(-0.35, 0, 0))
    r.stl('rim_rear', 'cast', at(RA, PY)); tyre(r, RA, WRR, 0.062, 1.45)
    part('sprocket_rear', pivot=RA, parent='wheel_rear', axis=Y, explode=(0, 0.3, 0)).stl('sprocket_rear', 'alu', at(RA + V((0, CHAIN_Y, 0)), PY))
    part('disc_rear', pivot=RA, parent='wheel_rear', axis=Y, explode=(0, -0.3, 0)).stl('disc_rear', 'steel', at(RA + V((0, -0.088, 0)), PY))
    rc = part('caliper_rear', parent='swingarm', explode=(0, -0.25, 0.15))
    caliper(rc, RA, radians(60), 0.103, -0.088, -1, 'black', 1)
    a = radians(60); u = V((cos(a), 0, sin(a)))                                            # bracket: axle to caliper, torque stay
    rc.sweep([RA + V((0, -0.118, 0)), RA + u * 0.07 + V((0, -0.118, 0))], 0.012, 'black', 12)
    rc.disc(RA + V((0, -0.123, 0)), Y, 0.016, 0.008, 'steel', 6)                           # axle nut
    rc.sweep(smooth([RA + u * 0.125 + V((0, -0.11, 0.0)), RA + V((0.2, -0.12, 0.10)), V((PIVOT.x - 0.06, -0.125, PIVOT.z - 0.01))], 6), 0.004, 'black', 8)   # hose

def caliper(m, c, ang, rad, yd, s, mat, pistons, leg=None):
    """Brake caliper straddling a disc (axle c, braking face y = yd, rim band at radius rad) at angle ang in the xz plane, s = +1
    when the outboard side is +y: two body halves with rounded edges joined by a bridge over the disc edge, piston bores on
    the outboard face, pad pin, bleed nipple, banjo bolt, two mounting lugs and, given the fork axle `leg`, brackets from them to the fork leg."""
    u = V((cos(ang), 0, sin(ang))); w = V((-sin(ang), 0, cos(ang)))          # radial out, tangential
    rot = Matrix((w, Y, u)).transposed()                                      # local x = tangential, y = Y, z = radial
    L = 0.10 if pistons > 2 else 0.07
    for k in (-1, 1):                                                         # halves: outboard (k = s) carries the bores
        rbox(m, c + u * (rad + 0.004) + Y * (yd + k * 0.019), (L, 0.024, 0.05), 0.008, mat, rot)
    rbox(m, c + u * (rad + 0.031) + Y * yd, (L * 0.86, 0.06, 0.014), 0.006, mat, rot)
    n = pistons // 2 or 1
    for i in range(n):
        tx = (i - (n - 1) / 2) * 0.042
        m.disc(c + u * rad + w * tx + Y * (yd + s * 0.032), Y, 0.017, 0.004, mat, 24)
        m.disc(c + u * rad + w * tx + Y * (yd + s * 0.0345), Y, 0.012, 0.002, 'dark', 20)
    m.tube(c + u * (rad + 0.012) + Y * (yd - 0.035), c + u * (rad + 0.012) + Y * (yd + 0.035), 0.0025, 'steel', 8)   # pad pin
    m.tube(c + u * (rad + 0.02) + w * (L / 2 - 0.012) + Y * (yd + s * 0.02), c + u * (rad + 0.034) + w * (L / 2 - 0.006) + Y * (yd + s * 0.02), 0.003, 'steel', 6)
    m.disc(c + u * (rad + 0.01) - w * (L / 2 - 0.01) + Y * (yd + s * 0.033), Y, 0.007, 0.006, 'steel', 6)   # banjo bolt
    for k in (-1, 1):                                                         # mounting lugs, bolts and, on a fork, the leg's lugs
        lp = c + u * (rad - 0.032) + w * k * (L / 2 - 0.012) + Y * (yd + s * 0.019)
        rbox(m, lp, (0.024, 0.02, 0.024), 0.006, mat, rot)
        m.disc(lp - u * 0.012, u, 0.0072, 0.007, 'steel', 6)
        if leg is not None:
            q = leg + STEER * (lp - leg).dot(STEER); q.y = lp.y + s * 0.02
            m.sweep([lp - u * 0.016, q], 0.009, 'dark', 12)

def build():
    engine(); gearbox(); chain(); tripo_body(); wheels(); strip_tripo(); controls(); silencer()
    if 'handlebar' in PARTS:   # Tripo lost the right mirror's stalk in decimation: a stalk like the left one's, bar clamp to mirror head
        PARTS['handlebar']['m'].tube(V((0.333, -0.245, 1.215)), V((0.330, -0.285, 1.375)), 0.0065, 'black', 10)

# ---------------------------------------------------------------- foot controls and silencer (the Tripo ones were shapeless lumps)
PEG = V((-0.265, 0, 0.325))                                  # rider footpeg pivot (x, z); cad.py hanger_rider bosses are relative to it
PILLION = V((-0.52, 0, 0.485))
HANGER_Y = {1: 0.218, -1: -0.192}                            # hanger mid-planes: just outboard of the swingarm pivot plates
PILLION_Y = {1: 0.205, -1: -0.188}

def bar(m, pts, w, t, mat):
    """Forged lever: a flat bar along points in an xz plane (width w in that plane, t thick across it), rounded joints."""
    for a, b in zip(pts, pts[1:]):
        d = b - a
        rbox(m, (a + b) / 2, (d.length, t, w), min(w, t) * 0.4, mat, Matrix.Rotation(-atan2(d.z, d.x), 3, 'Y'))
    for p in pts[1:-1]: m.disc(p, Y, w * 0.5, t, mat, 16)

def peg(m, root, s, length, fold=0.0):
    """Footpeg folding about an axis along x at root: steel peg with a ribbed rubber sleeve, clevis, pivot pin and, on the rider's pegs, a peg feeler (the wear tip that touches down first in a deep lean)."""
    ax = V((0, s, 0))
    rbox(m, root + ax * 0.010, (0.036, 0.022, 0.026), 0.005, 'alu')          # clevis
    m.tube(root + V((-0.024, 0, 0)), root + V((0.024, 0, 0)), 0.004, 'steel', 8)   # pivot pin
    a, b = root + ax * 0.018, root + ax * length
    m.tube(a, b, 0.0105, 'steel', 16)
    m.tube(a + ax * 0.008, b - ax * 0.008, 0.0135, 'rubber', 16)
    k = 0.012
    while k < length - 0.02:
        m.disc(a + ax * k, ax, 0.0158, 0.006, 'rubber', 16); k += 0.011
    m.disc(b, ax, 0.0125, 0.004, 'steel', 16)
    if fold: m.tube(b - ax * 0.012 - V((0, 0, 0.01)), b - ax * 0.012 - V((0, 0, 0.034)), 0.0032, 'steel', 8)   # peg feeler

def controls():
    """Rider and pillion footpegs on cast hangers, the gear lever with its linkage to the shift shaft (left) and the rear
    brake pedal with its master cylinder and reservoir (right). Bolted to the frame, so they are part of it."""
    m = PARTS['frame']['m']
    for s in (1, -1):
        hy = HANGER_Y[s]; c = V((PEG.x, hy, PEG.z))
        m.stl('hanger_rider', 'alu', frame_m(c, V((1, 0, 0)), V((0, 0, 1)), V((0, -1, 0))))
        for bx, bz in ((0.030, 0.105), (-0.105, 0.145)):                                  # frame bolts
            m.disc(c + V((bx, s * 0.006, bz)), Y, 0.0075, 0.006, 'steel', 6)
        peg(m, c + V((0, s * 0.004, 0)), s, 0.11, fold=1)
        p = V((PILLION.x, PILLION_Y[s], PILLION.z))
        m.stl('hanger_pillion', 'alu', frame_m(p, V((1, 0, 0)), V((0, 0, 1)), V((0, -1, 0))))
        for bx, bz in ((0.060, 0.040), (-0.040, 0.040)):
            m.disc(p + V((bx, s * 0.006, bz)), Y, 0.0065, 0.006, 'steel', 6)
        peg(m, p + V((0, s * 0.004, 0)), s, 0.085)
        d = c + V((0.030, s * 0.012, 0.030))                                              # lever pivot on the hanger
        m.disc(d + V((0, s * 0.004, 0)), Y, 0.0085, 0.008, 'steel', 6)
        if s > 0:   # gear lever: toe arm forward to a rubber toe peg, short upper arm to the linkage rod
            t = V((-0.088, d.y, 0.338)); e = d + V((0.008, 0, 0.040))
            bar(m, [d, V((-0.16, d.y, 0.342)), t], 0.014, 0.007, 'alu')
            bar(m, [d, e], 0.013, 0.007, 'alu')
            m.tube(t, t + Y * 0.055, 0.0095, 'rubber', 14); m.disc(t + Y * 0.056, Y, 0.0085, 0.003, 'steel', 14)
            sh = V((-0.036, 0.10, 0.432)); f = V((-0.032, d.y, 0.392))                   # shift shaft out past the frame, its clamp arm
            m.tube(sh, V((sh.x, d.y + 0.004, sh.z)), 0.0075, 'steel', 12)
            bar(m, [V((sh.x, d.y, sh.z)), f], 0.014, 0.008, 'alu')
            m.disc(V((sh.x, d.y + 0.006, sh.z)), Y, 0.0045, 0.006, 'steel', 6)
            a, b = f + Y * 0.008, e + Y * 0.008                                           # linkage rod with rod ends
            m.tube(a, b, 0.0042, 'steel', 8)
            for q in (a, b): m.disc(q, Y, 0.0085, 0.009, 'steel', 12)
            for q in (a.lerp(b, 0.15), a.lerp(b, 0.85)): m.disc(q, b - a, 0.0055, 0.008, 'steel', 6)   # lock nuts
        else:       # brake pedal forward to a pad, rear arm pushing the master cylinder's rod
            pad = V((-0.095, d.y, 0.330)); g = d + V((-0.040, 0, 0.008))
            bar(m, [d, V((-0.17, d.y, 0.322)), pad], 0.016, 0.008, 'alu')
            bar(m, [d, g], 0.013, 0.008, 'alu')
            rbox(m, pad + V((0.004, -0.026, 0.006)), (0.048, 0.05, 0.014), 0.004, 'alu', Matrix.Rotation(radians(-8), 3, 'Y'))
            for k in range(4): m.box(pad + V((-0.015 + k * 0.01, -0.026, 0.014)), (0.003, 0.046, 0.003), 'steel')
            mc0, mc1 = V((-0.300, -0.172, 0.392)), V((-0.300, -0.172, 0.468))             # master cylinder on the hanger's inner face
            m.disc((mc0 + mc1) / 2, V((0, 0, 1)), 0.0125, (mc1 - mc0).length, 'alu', 18)
            m.disc(mc1 + V((0, 0, 0.004)), V((0, 0, 1)), 0.008, 0.012, 'steel', 6)       # banjo
            rbox(m, (mc0 + mc1) / 2 + V((0.018, -0.006, 0)), (0.022, 0.01, 0.06), 0.004, 'alu')   # mounting flange
            m.tube(mc0, g + V((0, 0.004, 0)), 0.003, 'steel', 6)                         # push rod
            m.disc(mc0 - V((0, 0, 0.004)), V((0, 0, 1)), 0.009, 0.008, 'rubber', 12)     # dust boot
            rv = V((-0.36, -0.158, 0.565))
            m.disc(rv, V((0, 0, 1)), 0.016, 0.042, 'core', 18); m.disc(rv + V((0, 0, 0.024)), V((0, 0, 1)), 0.017, 0.008, 'black', 18)
            m.sweep(smooth([rv - V((0, 0, 0.021)), V((-0.345, -0.17, 0.52)), mc1 + V((0, 0, 0.012))], 6), 0.0045, 'black', 8)
            m.sweep(smooth([mc1 + V((0.004, 0.0, 0.010)), V((-0.27, -0.14, 0.47)), V((PIVOT.x - 0.06, -0.125, PIVOT.z - 0.01))], 6), 0.004, 'black', 8)

def silencer():
    """Link pipe from the headers' collector to a round silencer under the pillion peg, held by a clamp band and a strap."""
    m = PARTS['exhaust_headers']['m']
    i0, o0 = V((-0.385, -0.175, 0.335)), V((-0.745, -0.175, 0.48)); ax = (o0 - i0).normalized()
    m.sweep(smooth([V((-0.17, -0.05, CRANK.z - 0.15)), V((-0.24, -0.08, 0.296)), V((-0.32, -0.14, 0.302)), i0 + ax * 0.01], 6), 0.025, 'chrome', 16)
    L = (o0 - i0).length; prof = [(0, 0.026), (0.02, 0.03), (0.07, 0.056), (0.09, 0.058), (L - 0.03, 0.056), (L - 0.012, 0.05), (L, 0.044)]
    m.sweep([i0 + ax * d for d, _ in prof[:3]], [r for _, r in prof[:3]], 'chrome', 32)     # inlet cone
    m.sweep([i0 + ax * d for d, _ in prof[2:5]], [r for _, r in prof[2:5]], 'can', 32)      # body
    m.sweep([i0 + ax * d for d, _ in prof[4:]], [r for _, r in prof[4:]], 'alu', 32)        # end cap
    m.tube(o0 - ax * 0.01, o0 + ax * 0.028, 0.021, 'chrome', 20); m.disc(o0 + ax * 0.026, ax, 0.016, 0.006, 'black', 16)
    band = i0 + ax * 0.24
    m.torus(band, ax, 0.0585, 0.0035, 'alu', 40, 6)
    top = V((PILLION.x - 0.01, -0.186, PILLION.z - 0.01))
    bar(m, [band + V((0, 0, 0.057)), top], 0.022, 0.006, 'alu')                         # strap to the pillion hanger

def strip_tripo():
    """Delete the Tripo faces the parts above replace: footpeg hangers, pegs and levers, the silencer and link pipe, and the
    brake disc remnants left in the front wheel."""
    def poly(x, z, pts):
        c = False
        for (x1, z1), (x2, z2) in zip(pts, pts[1:] + pts[:1]):
            if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1): c = not c
        return c
    HL = [(-0.245, 0.456), (-0.38, 0.489), (-0.38, 0.45), (-0.32, 0.378), (-0.32, 0.28), (-0.205, 0.28), (-0.212, 0.366), (-0.239, 0.378)]
    HR = [(-0.383, 0.492), (-0.242, 0.456), (-0.218, 0.378), (-0.212, 0.33), (-0.188, 0.294), (-0.35, 0.294), (-0.35, 0.348), (-0.302, 0.39)]
    def seg(x, z, a, b):
        t = max(0, min(1, ((x - a[0]) * (b[0] - a[0]) + (z - a[1]) * (b[1] - a[1])) / ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)))
        return sqrt((x - a[0] - t * (b[0] - a[0])) ** 2 + (z - a[1] - t * (b[1] - a[1])) ** 2)
    def gone(pid, p):
        x, y, z = p
        if pid in ('fork', 'frame') and sqrt((x - FA.x) ** 2 + (z - FA.z) ** 2) < 0.21 and 0.05 < abs(y) < 0.16:
            d = FA - p; d.y = 0
            leg = sqrt((d.x * STEER.z - d.z * STEER.x) ** 2 + (abs(y) - 0.115) ** 2)   # fork leg: 0.115 off centre, ~0.04 radius
            if leg > 0.042 or z < FA.z - 0.035: return True
        if pid != 'frame': return False
        return ((y > 0.10 and poly(x, z, HL)) or (y < -0.10 and poly(x, z, HR))
                or (y < -0.06 and x < -0.24 and seg(x, z, (-0.26, 0.25), (-0.76, 0.48)) < 0.08)
                or (z < 0.295 and -0.42 < x < -0.02 and abs(y) < 0.2))
    for pid in ('fork', 'frame'):
        if pid not in PARTS: continue
        bm = PARTS[pid]['m'].bm
        dead = [f for f in bm.faces if gone(pid, f.calc_center_median())]
        cut = {v for f in dead for v in f.verts}
        bmesh.ops.delete(bm, geom=dead, context='FACES')
        seen, shards = set(), []                     # slivers the cut left: small pieces that were attached to deleted faces
        for f in bm.faces:
            if f in seen: continue
            island, todo = [], [f]; seen.add(f)
            while todo:
                g = todo.pop(); island.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h not in seen: seen.add(h); todo.append(h)
            if len(island) < 24 and any(v in cut for g in island for v in g.verts): shards += island
        bmesh.ops.delete(bm, geom=shards, context='FACES')
        print('strip', pid, len(dead), 'faces,', len(shards), 'in slivers')

# ---------------------------------------------------------------- Tripo bodywork
TRIPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tripo', 'body.glb')
SHELL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shell.glb')

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
    if not tripo_shell(TRIPO, (FA.x, RA.x), cut, 16000, classify, nodes) and not shell_glb(SHELL, nodes):
        part('fork', pivot=HEAD, axis=STEER); part('swingarm', pivot=PIVOT, axis=Y)            # keep the wheel parents

def shell_glb(path, nodes):
    """Without the Tripo source (it is not in git): shell.glb holds the already cut, aligned, decimated and split shell parts,
    as one node per part (exported from a build), so any machine can rebuild the exhibit."""
    if not os.path.exists(path): return False
    bpy.ops.import_scene.gltf(filepath=path)
    for ob in [o for o in bpy.context.selected_objects if o.type == 'MESH']:
        pid = ob.name.split('.')[0]; piv, ax, ex, parent = nodes[pid]
        me = ob.data; me.transform(ob.matrix_world)
        m = part(pid, pivot=piv, axis=ax, explode=ex, parent=parent); m.mats = [me.materials[0].name]
        m.bm.from_mesh(me)
        for f in m.bm.faces: f.material_index = 0; f.smooth = True
    for o in list(bpy.context.selected_objects): bpy.data.objects.remove(o)
    common.SHELLS.add('body_paint')
    return True

VIEWS = {'left': ((0.1, 3.2, 0.6), (0.0, 0, 0.5), 35), 'left_34': ((1.9, 2.2, 1.2), (0.0, 0, 0.45), 35),
         'right_34': ((-1.2, -2.4, 1.1), (0.0, 0, 0.45), 35), 'engine': ((0.75, 0.9, 0.75), (0.05, 0, 0.5), 40),
         'front': ((2.6, 0.3, 0.8), (0.3, 0, 0.5), 40),
         'pegs_l': ((-0.05, 0.85, 0.55), (-0.18, 0.1, 0.36), 45), 'pegs_r': ((-0.05, -0.85, 0.55), (-0.2, -0.1, 0.36), 45),
         'pegs_l_low': ((0.25, 0.75, 0.22), (-0.2, 0.12, 0.33), 45), 'rear_r': ((-0.9, -0.9, 0.7), (-0.55, 0, 0.45), 45),
         'caliper_f': ((1.2, -0.8, 0.6), (0.65, 0, 0.42), 45), 'side_r': ((0.0, -3.0, 0.6), (0.0, 0, 0.55), 35),
         'caliper_f2': ((0.3, -0.75, 0.62), (0.62, -0.08, 0.42), 45), 'under': ((0.3, 1.0, 0.1), (-0.1, 0, 0.3), 30)}

if __name__ == '__main__':
    run(__file__, build, VIEWS, VIEWS['left_34'])
