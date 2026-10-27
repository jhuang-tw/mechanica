# Drivetrain parts of the bike exhibit as real CAD (build123d), exported as STL for build.py to place.
#   C:\AI\cad-venv\Scripts\python.exe tools/exhibits/bike/cad.py      -> tools/exhibits/bike/cad/out/<name>.stl (mm, gitignored)
# Every part is modelled about the z axis with its rotation centre at the origin; build.py turns z into the bike's axle
# direction and moves it into place. Sizes follow real 11-speed road parts (12.7 mm chain pitch, 110 mm BCD spider).
import os
from math import sin, cos, pi, asin
from build123d import (BuildPart, BuildSketch, BuildLine, Polyline, Circle, Rectangle, Locations, PolarLocations, make_face,
                       extrude, Mode, Cylinder, Plane, Axis, revolve, export_stl, Part)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cad', 'out')
PITCH, ROLLER = 12.7, 7.75
TAU = 2 * pi

def pitch_r(n): return PITCH / (2 * sin(pi / n))

def tooth_outline(n, seg=5):
    """Sprocket outline: a roller seat (arc) in every gap, straight flanks up to a narrowed tip."""
    rp, rs = pitch_r(n), ROLLER / 2 * 1.02
    tip = rp + 0.38 * PITCH if n > 20 else rp + 0.33 * PITCH
    half = asin(min(0.95, rs / rp))       # half-angle the seat takes on the pitch circle
    pts = []
    for k in range(n):
        g = TAU * k / n                   # gap (roller) centre
        cx, cy = rp * cos(g), rp * sin(g)
        for i in range(seg + 1):          # seat arc: the half of the roller circle facing the centre
            a = g + 1.5 * pi - pi * i / seg   # trailing side -> inward -> leading side
            pts.append((cx + rs * cos(a), cy + rs * sin(a)))
        t = g + pi / n                    # tooth centre
        w = 0.18 * TAU / n
        pts += [(tip * cos(t - w), tip * sin(t - w)), (tip * cos(t + w), tip * sin(t + w))]
    return pts

def sprocket(n, t, r_in):
    with BuildPart() as p:
        with BuildSketch():
            with BuildLine(): Polyline(*tooth_outline(n), close=True)
            make_face()
            Circle(r_in, mode=Mode.SUBTRACT)
        extrude(amount=t / 2, both=True)
    return p.part

def chainring():
    ring = sprocket(50, 4.0, pitch_r(50) - 13)
    with BuildPart() as tabs:              # four bolt tabs reaching in to the 110 BCD spider
        with BuildSketch():
            with PolarLocations(55, 4, start_angle=45): Circle(9)
        extrude(amount=2, both=True)
        with BuildSketch():
            with PolarLocations(70, 4, start_angle=45): Rectangle(36, 16, rotation=0)
        extrude(amount=2, both=True)
        with BuildSketch():
            with PolarLocations(55, 4, start_angle=45): Circle(5)
        extrude(amount=2, both=True, mode=Mode.SUBTRACT)
    return ring + tabs.part

def cassette():
    """11-28 eleven-speed: 11T at z = 0, each bigger cog 3.9 mm further along -z (towards the spokes)."""
    cogs = [11, 12, 13, 14, 15, 17, 19, 21, 23, 25, 28]
    part = None
    for i, n in enumerate(cogs):
        c = sprocket(n, 1.8, 16).moved(Plane.XY.offset(-i * 3.9).location)
        part = c if part is None else part + c
    with BuildPart() as carrier:           # spacers and the freehub body the cogs slide onto
        Cylinder(18, 11 * 3.9, align=None)
        Cylinder(16, 11 * 3.9 + 4, align=None, mode=Mode.SUBTRACT)
    return part + carrier.part.moved(Plane.XY.offset(-5 * 3.9).location)

def crank_arm(spider=True):
    """Crank arm: spindle boss at the origin, pedal eye 172.5 mm along -y, arm face at z = -6..6. The right arm carries
    the four-arm 110 BCD spider in the chainring plane, 18-22 mm inboard (-z), where the 50T ring bolts on."""
    L = 172.5
    with BuildPart() as p:
        with BuildSketch():
            with BuildLine(): Polyline((-13, 0), (-8.5, -L), (8.5, -L), (13, 0), close=True)
            make_face()
            Circle(19)
            with Locations((0, -L)): Circle(11)
        extrude(amount=6, both=True)
        if spider:
            with BuildSketch(Plane.XY.offset(-22)):
                for a in (45, 135, 225, 315):
                    with Locations((27.5 * cos(a * pi / 180), 27.5 * sin(a * pi / 180))): Rectangle(55, 11, rotation=a)
                with PolarLocations(55, 4, start_angle=45): Circle(8)
                Circle(19)
            extrude(amount=4)
            with BuildSketch(Plane.XY.offset(-22)):
                Circle(19)
            extrude(amount=28)
        with BuildSketch(Plane.XY.offset(-30)):
            Circle(12)                          # 24 mm spindle bore
            with Locations((0, -L)): Circle(4.5)
            with PolarLocations(55, 4, start_angle=45): Circle(4.5)
        extrude(amount=40, mode=Mode.SUBTRACT)
    return p.part

def hub(width, flange_r, flange_x, holes=12):
    """Hub shell with two drilled flanges; axle along z."""
    with BuildPart() as p:
        Cylinder(15, width, align=None)
        for z in flange_x:
            with BuildSketch(Plane.XY.offset(z)):
                Circle(flange_r)
                with PolarLocations(flange_r - 4, holes): Circle(1.3, mode=Mode.SUBTRACT)
            extrude(amount=1.5, both=True)
        Cylinder(5, width + 30, align=None)      # axle / quick release
    return p.part

def jockey():
    with BuildPart() as p:
        with BuildSketch():
            with BuildLine(): Polyline(*tooth_outline(11, 3), close=True)
            make_face()
        extrude(amount=1.5, both=True)
        Cylinder(9, 5, align=None)
        Cylinder(3, 8, align=None, mode=Mode.SUBTRACT)
    return p.part

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, make, tol in (('chainring', chainring, 0.08), ('cassette', cassette, 0.08), ('crank_right', crank_arm, 0.1), ('crank_left', lambda: crank_arm(False), 0.1),
                            ('hub_front', lambda: hub(70, 22, (-27, 27)), 0.1), ('hub_rear', lambda: hub(110, 24, (-27, 20)), 0.1),
                            ('jockey', jockey, 0.05)):
        part = make()
        assert part.is_valid, name
        export_stl(part, os.path.join(OUT, name + '.stl'), tolerance=tol, angular_tolerance=0.3)
        print(name, 'ok')
