# Mechanical parts of the steam locomotive exhibit as real CAD (build123d), exported as STL (mm) for build.py.
#   C:\AI\cad-venv\Scripts\python.exe tools/exhibits/steam/cad.py      -> tools/exhibits/steam/cad/out/<name>.stl (gitignored)
# Generic 0-6-0 tank engine: 1200 mm driving wheels, two outside cylinders 400 x 600 mm with piston valves above them.
# Wheels: axis z, outer face (crankpin side) towards +z, crankpin at +x. Cylinder: bore axis x, piston at the origin side.
import os
from math import sin, cos, pi
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline, Polygon, Circle, Locations, PolarLocations, make_face,
                       extrude, revolve, Mode, Cylinder, Box, Plane, Axis, Pos, Rot, export_stl)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cad', 'out')
R_TREAD, CRANK = 600, 300
TAU = 2 * pi

def wheel(counterweight=True):
    # tyre and rim (flange on the inner, -z side) and the hub: two separate rings, joined only by the spokes
    rim = [(500, 40), (520, 40), (520, 70), (R_TREAD, 70), (R_TREAD + 4, -40), (R_TREAD + 30, -50), (R_TREAD + 30, -70), (520, -70), (520, -40), (500, -40)]
    hub = [(80, 90), (175, 90), (175, -90), (80, -90)]
    with BuildPart() as p:
        for prof in (rim, hub):
            with BuildSketch(Plane.XZ):
                with BuildLine(): Polyline(*prof, close=True)
                make_face()
            revolve(axis=Axis.Z)
        with BuildSketch(Plane.XY.offset(-22)):                            # spokes taper from hub to rim, like cast ones
            with PolarLocations(0, 14, start_angle=360 / 28):
                Polygon((160, -27), (525, -16), (525, 16), (160, 27), align=None)
        extrude(amount=44)
        if counterweight:                                                   # crescent opposite the crankpin
            pts = [(r * cos(a), r * sin(a)) for r, a in [(520, pi + d) for d in [-0.75 + 1.5 * i / 12 for i in range(13)]]]
            pts += [(220 * cos(pi + d), 220 * sin(pi + d)) for d in [0.75 - 1.5 * i / 12 for i in range(13)]]
            with BuildSketch(Plane.XY.offset(-28)):
                with BuildLine(): Polyline(*pts, close=True)
                make_face()
            extrude(amount=56)
        with Locations(Pos(CRANK, 0, 20)): Cylinder(95, 80)                # crank boss
        Cylinder(80, 200, mode=Mode.SUBTRACT)                               # axle seat
    return p.part

def cylinder(side=1):
    """Cylinder block, bore axis x from x = 0 (back cover) to 750, piston valve chest above at z = 340, slide bars to -1050.
    The outer upper quarter is cut away so the piston and the valve show."""
    with BuildPart() as p:
        with Locations(Pos(375, 0, 0)): Cylinder(260, 750, rotation=(0, 90, 0))
        with Locations(Pos(375, 0, 340)): Cylinder(150, 780, rotation=(0, 90, 0))      # valve chest
        with Locations(Pos(375, 0, 170)): Box(700, 200, 300)                            # saddle between them
        with Locations(Pos(375, 0, 0)): Cylinder(205, 740, rotation=(0, 90, 0), mode=Mode.SUBTRACT)   # bore
        with Locations(Pos(375, 0, 340)): Cylinder(110, 770, rotation=(0, 90, 0), mode=Mode.SUBTRACT)
        for x in (220, 530):                                                             # steam ports
            with Locations(Pos(x, 0, 170)): Box(50, 120, 280, mode=Mode.SUBTRACT)
        with Locations(Pos(375, side * 160, 270)): Box(800, 320, 640, mode=Mode.SUBTRACT)   # cutaway on the outer side (side = +1: +y)
        for z in (-120, 120):                                                            # slide bars
            with Locations(Pos(-520, 0, z)): Box(1040, 60, 40)
        with Locations(Pos(-10, 0, 0)): Cylinder(270, 30, rotation=(0, 90, 0))         # back cover with gland
        with Locations(Pos(-10, 0, 0)): Cylinder(45, 40, rotation=(0, 90, 0), mode=Mode.SUBTRACT)
    return p.part

def piston():
    """Piston head at the origin (x = 0 face centre), rod along -x to the crosshead at x = -850."""
    with BuildPart() as p:
        Cylinder(200, 90, rotation=(0, 90, 0))
        for x in (-25, 0, 25):
            with Locations(Pos(x, 0, 0)): Cylinder(203, 8, rotation=(0, 90, 0), mode=Mode.SUBTRACT)
            with Locations(Pos(x, 0, 0)): Cylinder(198, 8, rotation=(0, 90, 0))
        with Locations(Pos(-425, 0, 0)): Cylinder(40, 850, rotation=(0, 90, 0))
    return p.part

def valve():
    """Piston valve: two heads 300 apart on a spindle along x, origin at the centre; spindle runs back 700."""
    with BuildPart() as p:
        for x in (-150, 150):
            with Locations(Pos(x, 0, 0)): Cylinder(108, 70, rotation=(0, 90, 0))
        with Locations(Pos(-250, 0, 0)): Cylinder(22, 1000, rotation=(0, 90, 0))
    return p.part

def crosshead():
    """Crosshead block between the slide bars, gudgeon pin on y through the origin."""
    with BuildPart() as p:
        Box(260, 120, 200)
        with Locations(Pos(0, 0, 0)): Box(200, 140, 120, mode=Mode.SUBTRACT)
        Cylinder(40, 150, rotation=(90, 0, 0))
        for z in (-120, 120):
            with Locations(Pos(0, 0, z)): Box(300, 90, 40)                    # slippers on the bars
    return p.part

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, make, tol in (('wheel', wheel, 0.4), ('cylinder_l', cylinder, 0.5), ('cylinder_r', lambda: cylinder(-1), 0.5), ('piston', piston, 0.3), ('valve', valve, 0.3), ('crosshead', crosshead, 0.3)):
        part = make()
        assert part.is_valid, name
        export_stl(part, os.path.join(OUT, name + '.stl'), tolerance=tol, angular_tolerance=0.3)
        print(name, 'ok')
