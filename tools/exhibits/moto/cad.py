# Mechanical parts of the motorcycle exhibit as real CAD (build123d), exported as STL (mm) for build.py to place.
#   C:\AI\cad-venv\Scripts\python.exe tools/exhibits/moto/cad.py      -> tools/exhibits/moto/cad/out/<name>.stl (gitignored)
# Generic 700 cc liquid-cooled parallel twin (bore 80, stroke 70, rod 130, bore pitch 92, 270-degree crank), wet multi-plate
# clutch on the gearbox mainshaft, 6-speed constant-mesh gearbox, 520 chain, 17-inch cast wheels with floating discs.
# Every rotating part is modelled about +z with its rotation centre at the origin (same conventions as car/cad.py, whose
# piston, con-rod and gear helpers are reused here).
import os, sys
from math import sin, cos, pi
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline, Circle, Locations, PolarLocations, make_face,
                       extrude, revolve, Mode, Cylinder, Box, Plane, Axis, Pos, Rot, export_stl)
import car.cad as car
import bike.cad as bike

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cad', 'out')
TAU = 2 * pi
STROKE, ROD, PITCH_CYL = 70, 130, 92
CYL_Z = [-PITCH_CYL / 2, PITCH_CYL / 2]
THROW = [0, 1.5 * pi]                                      # 270-degree crank
car.STROKE, car.ROD = STROKE, ROD                          # car helpers read these at call time
bike.PITCH, bike.ROLLER = 15.875, 10.16                    # 520 chain

PRIMARY = (32, 58)                                         # crank gear : clutch basket, module 2.5 -> 112.5 mm centres
GEARS = [(24, 65), (30, 59), (35, 54), (39, 50), (42, 47), (45, 44)]   # mainshaft : countershaft, module 2.5 -> 111.25 mm
SPROCKETS = (15, 43)

def crankshaft():
    with BuildPart() as p:
        for z in (-92, 0, 92):
            with Locations(Pos(0, 0, z)): Cylinder(22, 24)          # main journals
        for z, a in zip(CYL_Z, THROW):
            with Locations(Pos(STROKE / 2 * cos(a), STROKE / 2 * sin(a), z)): Cylinder(20, 24)   # crankpins
            for s in (-1, 1):
                with BuildSketch(Plane.XY.offset(z + s * 19)):
                    with BuildLine(): Polyline(*car.web(a), close=True)
                    make_face()
                extrude(amount=7, both=True)
        with Locations(Pos(0, 0, 130)): Cylinder(16, 60)            # left end: alternator rotor
        with Locations(Pos(0, 0, 150)): Cylinder(55, 30)
        with Locations(Pos(0, 0, -125)): Cylinder(16, 50)           # right end carries the primary gear
    return p.part

def camshaft(phase):
    """Two lobes per cylinder; the second cylinder follows 270 crank degrees later (135 cam degrees)."""
    with BuildPart() as p:
        Cylinder(11, 2 * PITCH_CYL + 40)
        for z, a in zip(CYL_Z, (phase, phase - 0.75 * pi)):
            for dz in (-17, 17):
                with BuildSketch(Plane.XY.offset(z + dz)):
                    with BuildLine(): Polyline(*car.lobe_pts(a), close=True)
                    make_face()
                extrude(amount=6, both=True)
        for z in (-92, 0, 92):
            with Locations(Pos(0, 0, z)): Cylinder(14, 12)
        with Locations(Pos(0, 0, -PITCH_CYL - 25)): Cylinder(34, 6)   # cam chain sprocket
    return p.part

def block():
    """Two-bore cylinder block, bores on +z, crank axis along y, front +x, deck at z = 0; closed like a real one (lessons ghost it to show inside)."""
    with BuildPart() as p:
        with Locations(Pos(0, 0, -60)): Box(112, 205, 120)
        for y in CYL_Z:
            with Locations(Pos(0, y, -60)): Cylinder(40, 130, mode=Mode.SUBTRACT)
        with Locations(Pos(0, -112, -60)): Box(30, 20, 100, mode=Mode.SUBTRACT)        # cam chain tunnel (right)
    return p.part

def crankcase():
    """Side outline in xz around the crank (origin), gearbox behind; walls 6 mm, sealed: the crank and gears run in oil inside."""
    out = [(105, 30), (110, -40), (70, -120), (-60, -130), (-200, -80), (-262, -10), (-250, 60), (-170, 105), (-60, 100), (50, 75)]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline(*out, close=True)
            make_face()
        extrude(amount=110, both=True)
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline(*[(x * 0.95 - 5, z * 0.92 - 3) for x, z in out], close=True)
            make_face()
        extrude(amount=104, both=True, mode=Mode.SUBTRACT)
        for y in CYL_Z:
            with Locations(Pos(0, y, 60)): Cylinder(41, 80, mode=Mode.SUBTRACT)          # bores up into the block
        for x, z in ((-100, 50), (-200, 0)):
            with Locations(Pos(x, -105, z)): Cylinder(16, 20, rotation=(90, 0, 0), mode=Mode.SUBTRACT)   # shaft bearings, right wall
    return p.part

def clutch():
    """Wet clutch: basket with primary driven gear behind (z < 0), friction/steel plate stack, pressure plate, springs."""
    with BuildPart() as p:
        with BuildSketch(Plane.XY.offset(-30)):
            with BuildLine(): Polyline(*car.gear_outline(PRIMARY[1], 2.5), close=True)
            make_face()
            Circle(20, mode=Mode.SUBTRACT)
        extrude(amount=12)
        with Locations(Pos(0, 0, 0)):
            Cylinder(66, 44); Cylinder(61, 46, mode=Mode.SUBTRACT)                       # basket drum
            with PolarLocations(63, 8): Box(14, 8, 46, mode=Mode.SUBTRACT)               # fingers
        for k in range(7):                                                                 # plate stack
            with Locations(Pos(0, 0, -16 + 4.5 * k)):
                Cylinder(58 if k % 2 else 60, 2.4); Cylinder(30, 3, mode=Mode.SUBTRACT)
        with Locations(Pos(0, 0, 18)): Cylinder(52, 5)                                   # pressure plate
        with Locations(Pos(0, 0, 24)):
            with PolarLocations(34, 5): Cylinder(6, 14)                                  # springs
        with Locations(Pos(0, 0, 0)): Cylinder(20, 60, mode=Mode.SUBTRACT)
        with Locations(Pos(0, 0, 25)): Cylinder(14, 18)                                  # nut
    return p.part

def rim(width):
    """17-inch cast rim, bead seat radius 216, five split spokes; axis z, centred on z = 0."""
    R, h = 216, width / 2
    prof = [(R - 4, -h), (R + 10, -h - 2), (R + 10, -h + 6), (R, -h + 12), (R - 12, -h + 22), (R - 12, h - 22), (R, h - 12), (R + 10, h - 6),
            (R + 10, h + 2), (R - 4, h), (R - 2, h - 10), (R - 18, h - 24), (R - 18, -h + 24), (R - 2, -h + 10)]
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline(*prof, close=True)
            make_face()
        revolve(axis=Axis.Z)
        Cylinder(48, width * 0.55)                                                          # hub
        with PolarLocations(0, 5):
            for da in (-8, 8):
                with Locations(Rot(0, 0, da)):
                    with Locations(Pos(130, 0, 0)): Box(165, 16, 22)
        Cylinder(13, width, mode=Mode.SUBTRACT)
    return p.part

def disc(r):
    """Floating brake disc: 5 mm drilled ring on a carrier with six floating buttons, braking face at z = 0."""
    with BuildPart() as p:
        Cylinder(r, 5); Cylinder(r - 34, 6, mode=Mode.SUBTRACT)
        for k in range(3):
            with PolarLocations(r - 10 - 9 * k, 18, start_angle=7 * k): Cylinder(2.5, 6, mode=Mode.SUBTRACT)
        Cylinder(r - 50, 4); Cylinder(46, 5, mode=Mode.SUBTRACT)
        with PolarLocations(r - 40, 6):
            Cylinder(7, 6)
        with PolarLocations((r - 50 + 46) / 2 + 6, 6, start_angle=30): Cylinder(18, 6, mode=Mode.SUBTRACT)
        with PolarLocations(56, 6): Cylinder(4, 6, mode=Mode.SUBTRACT)
    return p.part

def sprocket_rear():
    s = bike.sprocket(SPROCKETS[1], 8, bike.pitch_r(SPROCKETS[1]) - 22)
    with BuildPart() as c:
        Cylinder(bike.pitch_r(SPROCKETS[1]) - 20, 6); Cylinder(52, 7, mode=Mode.SUBTRACT)
        with PolarLocations(78, 5): Cylinder(16, 7, mode=Mode.SUBTRACT)
        with PolarLocations(60, 5, start_angle=36): Cylinder(5, 7, mode=Mode.SUBTRACT)
    return s + c.part

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    jobs = [('crankshaft', crankshaft, 0.1), ('piston', car.piston, 0.1), ('conrod', car.conrod, 0.1),
            ('cam_in', lambda: camshaft(0), 0.1), ('cam_ex', lambda: camshaft(-pi / 2), 0.1), ('block', block, 0.15),
            ('crankcase', crankcase, 0.2), ('clutch', clutch, 0.12),
            ('primary_gear', lambda: car.gear(PRIMARY[0], 2.5, 14, 16, hub=24), 0.08),
            ('rim_front', lambda: rim(89), 0.2), ('rim_rear', lambda: rim(140), 0.2),
            ('disc_front', lambda: disc(160), 0.12), ('disc_rear', lambda: disc(120), 0.12),
            ('sprocket_front', lambda: bike.sprocket(SPROCKETS[0], 9, 14), 0.06), ('sprocket_rear', sprocket_rear, 0.1)]
    for i, (a, b) in enumerate(GEARS, 1):
        jobs += [(f'gear_main_{i}', lambda a=a: car.gear(a, 2.5, 12, 12, hub=18), 0.08), (f'gear_counter_{i}', lambda b=b: car.gear(b, 2.5, 12, 14, hub=20), 0.08)]
    for name, make, tol in jobs:
        part = make()
        assert part.is_valid, name
        export_stl(part, os.path.join(OUT, name + '.stl'), tolerance=tol, angular_tolerance=0.3)
        print(name, 'ok')
