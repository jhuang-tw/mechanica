# Case and movement parts of the dive-watch exhibit as real CAD (build123d), exported as STL (mm) for build.py.
#   C:\AI\cad-venv\Scripts\python.exe tools/exhibits/watch/cad.py      -> tools/exhibits/watch/cad/out/<name>.stl (gitignored)
# Generic 42 mm automatic dive watch (no brand). Frame: dial faces +z, 12 o'clock = +y, 3 o'clock = +x, z = 0 on the dial face.
# Wheels are modelled at their own centre (build.py places them); case, case back and bezel are revolves about z.
import os, sys
from math import sin, cos, pi, radians
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline, make_face, make_hull, extrude, revolve, Mode, Circle, Rectangle,
                       Cylinder, Box, Locations, PolarLocations, Plane, Axis, Pos, export_stl)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from heli.cad import gear_outline
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout import *

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cad', 'out')
TAU = 2 * pi


def wheel(n, m, t, arms=4, bore=0.15, z=0.0):
    """Train wheel of n teeth, thickness t, with `arms` crossings cut out between rim and hub."""
    ra = m * n / 2
    with BuildPart() as p:
        with BuildSketch(Plane.XY.offset(z)):
            with BuildLine(): Polyline(*gear_outline(n, m, 1), close=True)
            make_face()
            if arms:
                Circle(ra * 0.78, mode=Mode.SUBTRACT)
                Circle(ra * 0.22)
                with PolarLocations(0, arms): Rectangle(ra * 1.6, ra * 0.1)
            Circle(bore, mode=Mode.SUBTRACT)
        extrude(amount=t)
    return p.part

def pinion(n, m, z0, z1):
    with BuildPart() as p:
        with BuildSketch(Plane.XY.offset(z0)):
            with BuildLine(): Polyline(*gear_outline(n, m, 1), close=True)
            make_face()
        extrude(amount=z1 - z0)
    return p.part

def arbor(z0, z1, r=0.12): return Pos(0, 0, (z0 + z1) / 2) * Cylinder(r, z1 - z0)

def lathe(prof):
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline(*prof, close=True)
            make_face()
        revolve(axis=Axis.Z)
    return p.part

def barrel():
    """Mainspring barrel: toothed drum, lid cut open over a quarter so the spring shows (spring is drawn in build.py)."""
    with BuildPart() as p:
        with Locations(Pos(0, 0, -3.4)): Cylinder(M_B * 42 - 0.35, 1.2)
        with Locations(Pos(0, 0, -3.3)): Cylinder(M_B * 42 - 0.75, 1.2, mode=Mode.SUBTRACT)
        with Locations(Pos(2.6, 2.6, -3.95)): Box(5.2, 5.2, 0.4, mode=Mode.SUBTRACT)
        with Locations(Pos(0, 0, -3.4)): Cylinder(0.9, 1.2)                                        # arbor hub
    return p.part + wheel(84, M_B, 0.3, 0, 0.9, z=-3.1)

def escape_wheel():
    """20 club teeth, raked forward."""
    ro, ri = 2.35, 1.85; pts = []
    for k in range(20):
        a = TAU * k / 20; da = TAU / 20
        for t, r in ((a, ri), (a + 0.55 * da, ro), (a + 0.75 * da, ro - 0.08), (a + 0.8 * da, ri)): pts.append((r * cos(t), r * sin(t)))
    with BuildPart() as p:
        with BuildSketch(Plane.XY.offset(-3.7)):
            with BuildLine(): Polyline(*pts, close=True)
            make_face()
            Circle(1.5, mode=Mode.SUBTRACT); Circle(0.45)
            with PolarLocations(0, 4): Rectangle(3.2, 0.25)
        extrude(amount=0.15)
    return p.part + pinion(7, M_E, -5.25, -4.9) + arbor(-5.3, -2.7, 0.1)

def pallet_fork():
    """Lever from the pivot to the balance roller, plus the anchor whose two arms reach over the escape wheel (stones in build.py)."""
    e = (ESCAPE[0] - PALLET[0], ESCAPE[1] - PALLET[1]); b = (BALANCE[0] - PALLET[0], BALANCE[1] - PALLET[1])
    n = dist(b); ux, uy = b[0] / n, b[1] / n
    with BuildPart() as p:
        for ends in (((ux * 2.8, uy * 2.8, 0.28),),
                     ((e[0] * 0.55 + e[1] * 0.42, e[1] * 0.55 - e[0] * 0.42, 0.3), (e[0] * 0.55 - e[1] * 0.42, e[1] * 0.55 + e[0] * 0.42, 0.3))):
            with BuildSketch(Plane.XY.offset(-3.7)):
                Circle(0.5)
                for x, y, r in ends:
                    with Locations((x, y)): Circle(r)
                make_hull()
            extrude(amount=0.2)
    return p.part + arbor(-5.2, -2.7, 0.08)

def balance():
    with BuildPart() as p:
        with Locations(Pos(0, 0, -3.9)):
            Cylinder(4.4, 0.3); Cylinder(3.9, 0.35, mode=Mode.SUBTRACT)
            with PolarLocations(4.42, 8): Cylinder(0.22, 0.3)                                         # timing screws on the rim
        with BuildSketch(Plane.XY.offset(-4.0)):
            with PolarLocations(0, 3): Rectangle(7.9, 0.45)
            Circle(0.5)
        extrude(amount=0.2)
        with Locations(Pos(0, 0, -3.6)): Cylinder(0.7, 0.2)                                           # roller with the impulse jewel
    return p.part + arbor(-5.5, -2.7, 0.08)

def bridge(circles, z0=-6.4, z1=-5.25, holes=()):
    with BuildPart() as p:
        with BuildSketch(Plane.XY.offset(z0)):
            for (x, y, r) in circles:
                with Locations((x, y)): Circle(r)
            make_hull()
            for (x, y, r) in holes:
                with Locations((x, y)): Circle(r, mode=Mode.SUBTRACT)
        extrude(amount=z1 - z0)
    return p.part

def mainplate():
    with BuildPart() as p:
        with Locations(Pos(0, 0, -1.8)): Cylinder(13.0, 1.6)
        with Locations(Pos(0, 0, -1.8)): Cylinder(15.1, 1.6); Cylinder(13.0, 1.7, mode=Mode.SUBTRACT)    # movement ring
    return p.part

def rotor():
    """Half-moon oscillating weight: thin centre, heavy rim; on a ball bearing at the centre."""
    with BuildPart() as p:
        with BuildSketch(Plane.XY.offset(-7.0)):
            Circle(12.4)
            with Locations((0, -7)): Rectangle(26, 14, mode=Mode.SUBTRACT)
        extrude(amount=0.35)
        with BuildSketch(Plane.XY.offset(-7.25)):
            Circle(12.4); Circle(9.6, mode=Mode.SUBTRACT)
            with Locations((0, -7)): Rectangle(26, 14, mode=Mode.SUBTRACT)
        extrude(amount=0.6)
        with Locations(Pos(0, 0, -6.65)): Cylinder(2.0, 0.5)
    return p.part

def case():
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline((15.2, -7.3), (19.6, -7.3), (20.6, -6.4), (20.9, -2.0), (20.7, 1.6), (20.0, 2.5), (16.3, 2.5),
                                       (16.3, 1.2), (15.2, 1.0), close=True)
            make_face()
        revolve(axis=Axis.Z)
        for sx in (-1, 1):
            for sy in (-1, 1):
                with BuildSketch(Plane.YZ.offset(sx * 12.4)):
                    with BuildLine(): Polyline((sy * 17, -5.6), (sy * 24.5, -4.6), (sy * 25.4, -3.0), (sy * 24.8, 0.4), (sy * 18, 1.8), close=True)
                    make_face()
                extrude(amount=1.4, both=True)
        with Locations(Pos(21.6, 4.6, -1.9), Pos(21.6, -4.6, -1.9)): Box(3.4, 2.2, 5.2)               # crown guards
        with Locations(Pos(20, 0, -1.9)): Cylinder(1.3, 6, rotation=(0, 90, 0), mode=Mode.SUBTRACT)  # stem tube bore
    return p.part

def case_back():
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline((12.8, -9.0), (17.8, -9.0), (19.4, -8.4), (19.6, -7.3), (15.15, -7.3), (15.15, -6.7), (14.6, -6.7),
                                       (14.6, -7.3), (12.8, -7.3), close=True)
            make_face()
        revolve(axis=Axis.Z)
        with Locations(Pos(0, 0, -8.9)):
            with PolarLocations(18.3, 6): Box(2.4, 1.6, 0.6, mode=Mode.SUBTRACT)                      # wrench notches
    return p.part

def bezel():
    with BuildPart() as p:
        with BuildSketch(Plane.XZ):
            with BuildLine(): Polyline((16.4, 2.5), (20.9, 2.5), (20.9, 3.6), (20.2, 4.5), (16.6, 4.5), close=True)
            make_face()
        revolve(axis=Axis.Z)
        with Locations(Pos(0, 0, 3.0)):
            with PolarLocations(20.95, 120): Box(0.45, 0.45, 1.2, mode=Mode.SUBTRACT)                 # coin edge for grip
    return p.part

def crown():
    with BuildPart() as p:
        with BuildSketch(Plane.YZ.offset(22.2)):
            with BuildLine(): Polyline(*gear_outline(24, 0.28, 1), close=True)
            make_face()
        extrude(amount=3.4)
        with Locations(Pos(16, 0, 0)): Cylinder(0.5, 14, rotation=(0, 90, 0))                        # winding stem
    return p.part.moved(Pos(0, 0, -1.9))

JOBS = {
    'case': case, 'case_back': case_back, 'bezel': bezel, 'crown': crown,
    'dial': lambda: Pos(0, 0, -0.2) * Cylinder(15.1, 0.4),
    'mainplate': mainplate, 'rotor': rotor, 'barrel': barrel,
    'center_wheel': lambda: wheel(75, M_3, 0.25, 4, z=-4.35) + pinion(12, M_B, -3.1, -2.8) + arbor(-5.0, -0.5, 0.25),
    'ratchet': lambda: wheel(60, 0.12, 0.2, 0, 0.6, z=-6.6),
    'cannon_pinion': lambda: pinion(12, M_MW, -1.0, -0.6) + arbor(-0.6, 0.95, 0.3),
    'third_wheel': lambda: wheel(80, M_4, 0.25, 4, z=-4.85) + pinion(10, M_3, -4.4, -4.05) + arbor(-5.2, -2.7, 0.1),
    'fourth_wheel': lambda: wheel(84, M_E, 0.25, 5, z=-5.2) + pinion(10, M_4, -4.95, -4.55) + arbor(-5.2, 1.35, 0.1),
    'escape_wheel': escape_wheel, 'pallet_fork': pallet_fork, 'balance': balance,
    'minute_wheel': lambda: wheel(36, M_MW, 0.2, 0, 0.1, z=-1.0) + pinion(10, M_HW, -0.8, -0.5) + arbor(-1.0, -0.4, 0.1),
    'hour_wheel': lambda: wheel(40, M_HW, 0.2, 0, 0.42, z=-0.75) + Pos(0, 0, -0.1) * Cylinder(0.55, 1.3) - Pos(0, 0, 0) * Cylinder(0.42, 3),
    'barrel_bridge': lambda: bridge([(BARREL[0], BARREL[1], 5.4), (-6.0, 9.2, 1.5), (6.8, 8.6, 1.5)]),
    'train_bridge': lambda: bridge([(0, 0, 1.2), (THIRD[0], THIRD[1], 1.5), (ESCAPE[0], ESCAPE[1], 1.2), (PALLET[0], PALLET[1], 0.9), (8.0, -7.5, 1.5)]),
    'balance_cock': lambda: bridge([(BALANCE[0], BALANCE[1], 1.6), (-8.8, -6.9, 2.0), (-6.2, -8.9, 1.4)], -6.6, -5.6),
}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, make in JOBS.items():
        part = make()
        assert part.is_valid, name
        export_stl(part, os.path.join(OUT, name + '.stl'), tolerance=0.01, angular_tolerance=0.2)
        print(name, 'ok')
