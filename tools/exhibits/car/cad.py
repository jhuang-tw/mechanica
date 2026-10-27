# Mechanical parts of the car exhibit as real CAD (build123d), exported as STL (mm) for build.py to place.
#   C:\AI\cad-venv\Scripts\python.exe tools/exhibits/car/cad.py      -> tools/exhibits/car/cad/out/<name>.stl (gitignored)
# Generic transverse 1.8 L inline-four (bore 80, stroke 88, rod 140, bore pitch 88), 5-speed constant-mesh gearbox,
# open differential, 16-inch five-spoke wheels with vented discs. No brand shapes.
# Every rotating part is modelled about +z with its rotation centre at the origin; the piston has its cylinder axis on +z
# and the wrist pin on x; the con-rod lies in the xy plane, big end at the origin, small end at +y.
import os
from math import sin, cos, pi, atan2
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline, Circle, Rectangle, Locations, PolarLocations, make_face,
                       extrude, revolve, Mode, Cylinder, Box, Plane, Axis, Pos, Rot, export_stl)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cad', 'out')
TAU = 2 * pi
BORE, STROKE, ROD, PITCH_CYL = 80, 88, 140, 88
CYL_Z = [(i - 1.5) * PITCH_CYL for i in range(4)]          # cylinder centres along the crank
THROW = [0, pi, pi, 0]                                     # crankpin angles (cyl 1..4), firing order 1-3-4-2

def poly_face(pts):
    with BuildSketch() as s:
        with BuildLine(): Polyline(*pts, close=True)
        make_face()
    return s.sketch

def gear_outline(n, m, seg=3):
    """Spur gear outline: trapezoid teeth on pitch radius m*n/2 (addendum m, dedendum 1.25 m)."""
    rp = m * n / 2; ra, rf = rp + m, rp - 1.25 * m; pts = []
    for k in range(n):
        a = TAU * k / n; da = TAU / n
        for i in range(seg + 1): t = a - 0.25 * da + 0.25 * da * i / seg; pts.append((rf * cos(t), rf * sin(t)))   # root land
        for t, r in ((a + 0.05 * da, rp - 0.2 * m), (a + 0.17 * da, ra), (a + 0.33 * da, ra), (a + 0.45 * da, rp - 0.2 * m)): pts.append((r * cos(t), r * sin(t)))
        t = a + 0.5 * da; pts.append((rf * cos(t), rf * sin(t)))
    return pts

def gear(n, m, width, bore, hub=0):
    with BuildPart() as p:
        with BuildSketch():
            with BuildLine(): Polyline(*gear_outline(n, m), close=True)
            make_face()
            Circle(bore, mode=Mode.SUBTRACT)
        extrude(amount=width / 2, both=True)
        if hub:
            Cylinder(hub, width + 10, align=None)
            Cylinder(bore, width + 12, align=None, mode=Mode.SUBTRACT)
    return p.part

def web(angle):
    """Crank web: capsule from the main journal to the crankpin plus a counterweight opposite, in the xy plane."""
    pts = []
    for i in range(13):   # counterweight arc, 150 deg wide, opposite the pin
        t = angle + pi - 0.42 * pi + 0.84 * pi * i / 12; pts.append((60 * cos(t), 60 * sin(t)))
    for i in range(9):    # round end around the crankpin
        t = angle - pi / 2 + pi * i / 8; pts.append((STROKE / 2 * cos(angle) + 26 * cos(t), STROKE / 2 * sin(angle) + 26 * sin(t)))
    return pts

def crankshaft():
    with BuildPart() as p:
        for k in range(5):                                         # main journals
            with Locations(Pos(0, 0, (k - 2) * PITCH_CYL)): Cylinder(25, 26)
        for z, a in zip(CYL_Z, THROW):
            px, py = STROKE / 2 * cos(a), STROKE / 2 * sin(a)
            with Locations(Pos(px, py, z)): Cylinder(22, 26)       # crankpin
            for s in (-1, 1):
                with BuildSketch(Plane.XY.offset(z + s * 20)):
                    with BuildLine(): Polyline(*web(a), close=True)
                    make_face()
                extrude(amount=7, both=True)
        with Locations(Pos(0, 0, -2 * PITCH_CYL - 40)): Cylinder(19, 60)   # nose (timing pulley end)
        with Locations(Pos(0, 0, 2 * PITCH_CYL + 22)): Cylinder(30, 20)    # flange for the flywheel
    return p.part

def piston():
    """Cylinder axis z, crown at z = +30 (compression height), wrist pin on x through the origin."""
    with BuildPart() as p:
        with Locations(Pos(0, 0, 30 - 27.5)): Cylinder(BORE / 2 - 0.5, 55)
        with Locations(Pos(0, 0, 30 - 27.5 - 6)): Cylinder(BORE / 2 - 5, 50, mode=Mode.SUBTRACT)   # hollow skirt
        for zz in (24, 19, 14):                                   # ring grooves
            with Locations(Pos(0, 0, zz)):
                Cylinder(BORE / 2 + 1, 1.6, mode=Mode.SUBTRACT)
        for zz in (24, 19, 14):
            with Locations(Pos(0, 0, zz)): Cylinder(BORE / 2 - 3, 1.6)
        with Locations(Pos(0, 0, 0)): Cylinder(14, BORE - 14, rotation=(0, 90, 0))                 # pin bosses
        with Locations(Pos(0, 0, 0)): Cylinder(10, BORE, rotation=(0, 90, 0))                      # wrist pin
    return p.part

def conrod():
    """Big end at the origin (crankpin r 22), small end at (0, ROD) (wrist pin r 10), I-section shank, thickness along z."""
    shank = [(-14, 30), (-8, ROD - 12), (8, ROD - 12), (14, 30)]
    with BuildPart() as p:
        with BuildSketch():
            Circle(34);
            with Locations((0, ROD)): Circle(15)
            with BuildLine(): Polyline(*shank, close=True)
            make_face()
        extrude(amount=10, both=True)
        with BuildSketch(Plane.XY.offset(-11)):                    # I-beam recesses both faces
            with BuildLine(): Polyline((-7, 40), (-4, ROD - 22), (4, ROD - 22), (7, 40), close=True)
            make_face()
        extrude(amount=4, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(7)):
            with BuildLine(): Polyline((-7, 40), (-4, ROD - 22), (4, ROD - 22), (7, 40), close=True)
            make_face()
        extrude(amount=4, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(-12)):
            Circle(22)
            with Locations((0, ROD)): Circle(10)
        extrude(amount=24, mode=Mode.SUBTRACT)
        for x in (-28, 28):                                        # cap bolts
            with Locations(Pos(x, 0, 0)): Cylinder(5, 22, rotation=(90, 0, 0))
    return p.part

def lobe_pts(angle):
    pts = []
    for i in range(24):
        t = TAU * i / 24; r = 18 + 8 * max(0.0, cos(t - angle)) ** 3
        pts.append((r * cos(t), r * sin(t)))
    return pts

def camshaft(phase):
    """Two lobes per cylinder (4 valves), lobes timed for 1-3-4-2 at half crank speed; shaft on z, ends like the crank."""
    with BuildPart() as p:
        Cylinder(12, 4 * PITCH_CYL + 30)
        order = {0: 0, 2: 1, 3: 2, 1: 3}                           # cylinder index -> firing slot
        for i, z in enumerate(CYL_Z):
            a = phase - order[i] * pi / 2
            for dz in (-18, 18):
                with BuildSketch(Plane.XY.offset(z + dz)):
                    with BuildLine(): Polyline(*lobe_pts(a), close=True)
                    make_face()
                extrude(amount=6, both=True)
        for k in range(5):
            with Locations(Pos(0, 0, (k - 2) * PITCH_CYL)): Cylinder(15, 14)          # bearing journals
    return p.part

def flywheel():
    with BuildPart() as p:
        with BuildSketch():
            with BuildLine(): Polyline(*gear_outline(120, 2.5, 1), close=True)
            make_face()
        extrude(amount=8, both=True)
        Cylinder(140, 22)
        Cylinder(32, 30, mode=Mode.SUBTRACT)
        with Locations(Pos(0, 0, 11)):
            with PolarLocations(70, 6): Cylinder(14, 4, mode=Mode.SUBTRACT)
    return p.part

def pulley(n, width=26):
    """Toothed timing-belt pulley with flanges."""
    with BuildPart() as p:
        with BuildSketch():
            with BuildLine(): Polyline(*gear_outline(n, 3.0, 1), close=True)
            make_face()
            Circle(10, mode=Mode.SUBTRACT)
        extrude(amount=width / 2, both=True)
        r = 1.5 * n + 5
        for s in (-1, 1):
            with Locations(Pos(0, 0, s * (width / 2 + 1))): Cylinder(r, 2)
    return p.part

def disc():
    """Vented brake disc 280 x 24 with a hat; braking face at z = -12..12, hat towards +z (outboard)."""
    with BuildPart() as p:
        for z in (-8.5, 8.5):
            with Locations(Pos(0, 0, z)): Cylinder(140, 7)
        with PolarLocations(0, 36):
            with Locations(Pos(115, 0, 0)): Box(48, 4, 10)
        Cylinder(92, 30, mode=Mode.SUBTRACT)
        with Locations(Pos(0, 0, 20)):
            Cylinder(94, 40)
            Cylinder(86, 40, mode=Mode.SUBTRACT)
        with Locations(Pos(0, 0, 38)):
            Cylinder(94, 4)
            Cylinder(30, 6, mode=Mode.SUBTRACT)
            with PolarLocations(57, 5): Cylinder(7, 6, mode=Mode.SUBTRACT)
    return p.part

def rim():
    """16 x 6.5 inch rim, five spokes; axis z, mounting face at z = +40 (outboard), bead seat radius 203."""
    R = 203
    prof = [(R - 6, -82), (R + 12, -84), (R + 12, -76), (R, -70), (R - 14, -55), (R - 14, 50), (R, 66), (R + 12, 74), (R + 12, 82), (R - 6, 80), (R - 4, 70),
            (R - 20, 52), (R - 20, -52), (R - 4, -72)]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline(*prof, close=True)
            make_face()
        revolve(axis=Axis.Z)
        with Locations(Pos(0, 0, 44)): Cylinder(72, 26)                        # centre hub
        with PolarLocations(0, 5):                                              # Y-split spokes
            for da in (-7, 7):
                with Locations(Rot(0, 0, da)):
                    with Locations(Pos(125, 0, 52)): Box(130, 20, 20, rotation=(0, -8, 0))
        with Locations(Pos(0, 0, 44)):
            Cylinder(33, 40, mode=Mode.SUBTRACT)
            with PolarLocations(57, 5): Cylinder(8, 40, mode=Mode.SUBTRACT)
    return p.part

def diff_ring():
    """Final-drive ring gear on the differential carrier, with the cross pin, two spider and two side gears."""
    ring = gear(59, 3.0, 22, 60)
    with BuildPart() as c:
        Cylinder(62, 70)                                            # carrier
        Cylinder(48, 72, mode=Mode.SUBTRACT)
        Cylinder(36, 110)                                           # side bearing bosses
        Cylinder(16, 112, mode=Mode.SUBTRACT)
    sp = gear(10, 4.0, 14, 6).rotate(Axis.X, 90)
    side = gear(16, 4.0, 14, 16)
    parts = ring + c.part
    for s in (-1, 1):
        parts += sp.moved(Pos(0, s * 30, 0))
        parts += side.moved(Pos(0, 0, s * 26))
    parts += Cylinder(7, 92, rotation=(90, 0, 0))                   # cross pin
    return parts

def engine_case():
    """Block, head, valve cover and oil pan in engine axes (mm): x forward, y along the crank (cylinder 1 at +y), z up,
    origin on the crank centre. Bores are open so the pistons show when the head is lifted off."""
    DECK, HEAD, COVER = STROKE / 2 + ROD + 32, 130, 52
    ys = [-z for z in CYL_Z]
    with BuildPart() as b:
        with Locations(Pos(0, 0, (DECK - 70) / 2)): Box(230, 410, DECK + 70)
        for y in ys:
            with Locations(Pos(0, y, DECK / 2 + 20)): Cylinder(BORE / 2, DECK, mode=Mode.SUBTRACT)
            with Locations(Pos(0, y, 30)): Box(140, 60, 120, mode=Mode.SUBTRACT)            # throw clearance
        with Locations(Pos(0, 0, -40)): Box(160, 420, 80, mode=Mode.SUBTRACT)               # crankcase opening
        for y in [(k - 2) * PITCH_CYL for k in range(5)]:
            with Locations(Pos(0, y, 0)): Cylinder(40, 22, rotation=(90, 0, 0))             # main bearing saddles
            with Locations(Pos(0, y, 0)): Cylinder(26, 24, rotation=(90, 0, 0), mode=Mode.SUBTRACT)
    with BuildPart() as h:
        with Locations(Pos(0, 0, DECK + HEAD / 2)): Box(230, 410, HEAD)
        for x in (-35, 35):                                                                 # cam tunnels
            with Locations(Pos(x, 0, DECK + 95)): Cylinder(20, 420, rotation=(90, 0, 0), mode=Mode.SUBTRACT)
        for y in ys:
            with Locations(Pos(0, y, DECK)): Cylinder(BORE / 2 - 2, 20, mode=Mode.SUBTRACT)  # combustion chambers
            with Locations(Pos(0, y, DECK + 60)): Cylinder(9, 140, rotation=(0, 0, 0))      # spark plug tube
    with BuildPart() as v:
        with Locations(Pos(0, 0, DECK + HEAD + COVER / 2 - 4)): Box(210, 400, COVER)
        with Locations(Pos(0, 0, DECK + HEAD - 4)): Box(196, 386, 20, mode=Mode.SUBTRACT)
        for y in ys:
            with Locations(Pos(0, y, DECK + HEAD + COVER)): Cylinder(14, 30, mode=Mode.SUBTRACT)   # plug wells
    with BuildPart() as o:
        with BuildSketch(Plane.XZ.offset(-200)):
            with BuildLine(): Polyline((-110, -80), (110, -80), (110, -150), (40, -210), (-110, -210), close=True)
            make_face()
        extrude(amount=-400)
        with BuildSketch(Plane.XZ.offset(-192)):
            with BuildLine(): Polyline((-102, -78), (102, -78), (102, -146), (36, -202), (-102, -202), close=True)
            make_face()
        extrude(amount=-384, mode=Mode.SUBTRACT)
    return {'block': b.part, 'head': h.part, 'valve_cover': v.part, 'oil_pan': o.part}

def cv_shaft(length):
    """Drive shaft along z, inner tripod housing at z = 0, outer CV ball joint at z = length."""
    with BuildPart() as p:
        with Locations(Pos(0, 0, length / 2)): Cylinder(13, length - 80)
        Cylinder(42, 70)                                            # inner joint
        with Locations(Pos(0, 0, length)): Cylinder(45, 70)        # outer joint (bell)
        for z, r0, r1 in ((60, 40, 15), (length - 70, 15, 42)):      # boots
            with BuildSketch(Plane.XZ):
                pts = [(0, z - 25), (r0, z - 25)] + [(r0 + (r1 - r0) * i / 6 + (5 if i % 2 else 0), z - 25 + 50 * i / 6) for i in range(1, 7)] + [(0, z + 25)]
                with BuildLine(): Polyline(*pts, close=True)
                make_face()
            revolve(axis=Axis.Z)
    return p.part

# 5-speed constant mesh: input/output 122 mm apart, module 2.5 -> tooth sums of 98
GEARS = [(24, 74), (33, 65), (41, 57), (47, 51), (53, 45)]   # (input, output) teeth: 3.08, 1.97, 1.39, 1.09, 0.85
FINAL = (20, 59)                                              # output pinion : ring gear, module 3 -> 2.95

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    jobs = [('crankshaft', crankshaft, 0.1), ('piston', piston, 0.1), ('conrod', conrod, 0.1), ('cam_in', lambda: camshaft(0), 0.1),
            ('cam_ex', lambda: camshaft(-pi / 2), 0.1), ('flywheel', flywheel, 0.15), ('pulley_crank', lambda: pulley(20), 0.1),
            ('pulley_cam', lambda: pulley(40), 0.1), ('disc', disc, 0.15), ('rim', rim, 0.2), ('diff', diff_ring, 0.12),
            ('pinion', lambda: gear(FINAL[0], 3.0, 24, 12, hub=22), 0.08), ('cv_shaft', lambda: cv_shaft(300), 0.2)]
    for k, part in engine_case().items(): jobs.append((k, lambda part=part: part, 0.2))
    for i, (a, b) in enumerate(GEARS, 1):
        jobs += [(f'gear_in_{i}', lambda a=a: gear(a, 2.5, 16, 12, hub=20), 0.08), (f'gear_out_{i}', lambda b=b: gear(b, 2.5, 16, 12, hub=22), 0.08)]
    for name, make, tol in jobs:
        part = make()
        assert part.is_valid, name
        export_stl(part, os.path.join(OUT, name + '.stl'), tolerance=tol, angular_tolerance=0.3)
        print(name, 'ok')
